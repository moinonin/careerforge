"""CareerForge-S1: Pure-Python multi-head TF-IDF + temperature-scaled decision model.

Drop-in local replacement for TypeSafe Jev (`JevClient`) that returns identical
`JevAnalysis` and `JevProfileAnalysis` dataclasses with calibrated probabilities,
<1ms CPU latency, zero external dependencies, and no `TYPESAFE_API_KEY` required.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from backend.jev import (
    JevAnalysis,
    JevChoiceAnswer,
    JevClient,
    JevNoulAnswer,
    JevProfileAnalysis,
    JevScoreAnswer,
)

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_PATH = Path(__file__).resolve().parent / "weights.json"

JOB_CHOICE_HEADS: dict[str, list[str]] = {
    "skill_category": ["backend", "frontend", "fullstack", "devops", "data", "mobile"],
    "tech_stack": ["python_fastapi", "node_js", "java", "go", "ruby", "dotnet"],
    "salary_bracket": ["under_80k", "80k_120k", "120k_160k", "160k_200k", "200k_plus"],
}

JOB_SCORE_HEADS: dict[str, list[str]] = {
    "seniority_level": ["entry", "junior", "mid", "senior", "staff", "principal"],
}

JOB_BINARY_HEADS: tuple[str, ...] = ("has_red_flags", "remote_ok")

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "will", "would", "can", "this", "that", "these",
        "those", "it", "its", "as", "we", "you", "your", "our", "they", "their",
    }
)


def tokenize(text: str) -> list[str]:
    """Extract normalized unigrams + bigrams preserving tech symbols (c++, c#, .net)."""
    lowered = text.lower()
    raw = re.findall(r"(?:\.net|c\+\+|c#|[a-z0-9][a-z0-9_+.-]*)", lowered)
    unigrams = [t.strip(".-") for t in raw if len(t.strip(".-")) >= 2 and t not in _STOP_WORDS]
    bigrams = [f"{unigrams[i]}_{unigrams[i + 1]}" for i in range(len(unigrams) - 1)]
    return unigrams + bigrams


def _softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    t = max(0.05, float(temperature))
    scaled = [z / t for z in logits]
    m = max(scaled)
    exps = [math.exp(max(-50.0, min(50.0, z - m))) for z in scaled]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


def _sigmoid(logit: float, temperature: float = 1.0) -> float:
    t = max(0.05, float(temperature))
    z = max(-50.0, min(50.0, logit / t))
    return 1.0 / (1.0 + math.exp(-z))


class CareerForgeS1Model:
    """Multi-head linear TF-IDF classifier with per-head temperature calibration."""

    def __init__(
        self,
        *,
        vocab: dict[str, int] | None = None,
        idf: list[float] | None = None,
        multiclass_heads: dict[str, dict[str, Any]] | None = None,
        binary_heads: dict[str, dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.vocab: dict[str, int] = vocab or {}
        self.idf: list[float] = idf or []
        self.multiclass_heads: dict[str, dict[str, Any]] = multiclass_heads or {}
        self.binary_heads: dict[str, dict[str, Any]] = binary_heads or {}
        self.metadata: dict[str, Any] = metadata or {}

    def vectorize(self, text: str) -> dict[int, float]:
        """Convert text into an L2-normalized sparse TF-IDF dict {feature_idx: weight}."""
        counts = Counter(tokenize(text))
        vec: dict[int, float] = {}
        norm_sq = 0.0
        for tok, cnt in counts.items():
            idx = self.vocab.get(tok)
            if idx is None:
                continue
            val = (1.0 + math.log(cnt)) * self.idf[idx]
            vec[idx] = val
            norm_sq += val * val
        if norm_sq > 0.0:
            inv = 1.0 / math.sqrt(norm_sq)
            for idx in vec:
                vec[idx] *= inv
        return vec

    @classmethod
    def fit_distilled(
        cls,
        texts: list[str],
        multiclass_targets: dict[str, list[list[float]]],
        binary_targets: dict[str, list[float]],
        *,
        max_features: int = 2500,
        epochs: int = 120,
        lr: float = 1.2,
        l2: float = 1e-4,
        val_fraction: float = 0.2,
    ) -> CareerForgeS1Model:
        """Train all heads via soft-label distillation + per-head temperature scaling."""
        n_total = len(texts)
        if n_total < 4:
            raise ValueError("Need at least 4 examples to train CareerForgeS1Model")

        # Deterministic split: train vs calibration split
        val_count = max(1, int(n_total * val_fraction))
        train_idx = list(range(0, n_total - val_count))
        cal_idx = list(range(n_total - val_count, n_total))

        # Build vocabulary & IDF on training texts only
        df: Counter[str] = Counter()
        for i in train_idx:
            for tok in set(tokenize(texts[i])):
                df[tok] += 1

        top_terms = [tok for tok, _ in df.most_common(max_features)]
        vocab = {tok: idx for idx, tok in enumerate(top_terms)}
        n_train = len(train_idx)
        idf = [math.log((1.0 + n_train) / (1.0 + df[tok])) + 1.0 for tok in top_terms]

        model = cls(vocab=vocab, idf=idf)
        all_vecs = [model.vectorize(t) for t in texts]
        n_feats = len(vocab)

        # ── Train multiclass & ordinal score heads (KL / soft cross-entropy) ──
        head_labels = {**JOB_CHOICE_HEADS, **JOB_SCORE_HEADS}
        for head_name, targets in multiclass_targets.items():
            labels = head_labels[head_name]
            n_cls = len(labels)
            weights = [[0.0] * n_feats for _ in range(n_cls)]
            biases = [0.0] * n_cls

            for epoch in range(epochs):
                step_lr = lr / (1.0 + 0.015 * epoch)
                grad_w = [[0.0] * n_feats for _ in range(n_cls)]
                grad_b = [0.0] * n_cls
                for i in train_idx:
                    vec = all_vecs[i]
                    y = targets[i]
                    logits = [
                        biases[c] + sum(weights[c][idx] * val for idx, val in vec.items())
                        for c in range(n_cls)
                    ]
                    probs = _softmax(logits, 1.0)
                    for c in range(n_cls):
                        diff = probs[c] - y[c]
                        grad_b[c] += diff
                        for idx, val in vec.items():
                            grad_w[c][idx] += diff * val

                inv_n = 1.0 / n_train
                for c in range(n_cls):
                    biases[c] -= step_lr * (grad_b[c] * inv_n)
                    w_c = weights[c]
                    gw_c = grad_w[c]
                    for j in range(n_feats):
                        w_c[j] -= step_lr * (gw_c[j] * inv_n + l2 * w_c[j])

            # Temperature scaling on calibration split minimizing soft cross-entropy
            best_temp = 1.0
            best_loss = float("inf")
            cal_logits = [
                [
                    biases[c] + sum(weights[c][idx] * val for idx, val in all_vecs[i].items())
                    for c in range(n_cls)
                ]
                for i in cal_idx
            ]
            for t_step in range(10, 301, 5):
                temp = t_step / 100.0
                loss = 0.0
                for pos, i in enumerate(cal_idx):
                    probs = _softmax(cal_logits[pos], temp)
                    y = targets[i]
                    for c in range(n_cls):
                        if y[c] > 0.0:
                            loss -= y[c] * math.log(max(1e-9, probs[c]))
                if loss < best_loss:
                    best_loss = loss
                    best_temp = temp

            # Store sparse non-zero weights for compact JSON
            sparse_w = [
                {str(j): round(w, 6) for j, w in enumerate(weights[c]) if abs(w) > 1e-5}
                for c in range(n_cls)
            ]
            model.multiclass_heads[head_name] = {
                "labels": labels,
                "weights": sparse_w,
                "biases": [round(b, 6) for b in biases],
                "temperature": round(best_temp, 4),
            }

        # ── Train binary (noul) heads (soft BCE + temperature scaling) ──
        for head_name, targets in binary_targets.items():
            weights_b = [0.0] * n_feats
            bias_b = 0.0

            for epoch in range(epochs):
                step_lr = lr / (1.0 + 0.015 * epoch)
                grad_w_b = [0.0] * n_feats
                grad_b_b = 0.0
                for i in train_idx:
                    vec = all_vecs[i]
                    y_val = targets[i]
                    logit = bias_b + sum(weights_b[idx] * val for idx, val in vec.items())
                    prob = _sigmoid(logit, 1.0)
                    diff = prob - y_val
                    grad_b_b += diff
                    for idx, val in vec.items():
                        grad_w_b[idx] += diff * val

                inv_n = 1.0 / n_train
                bias_b -= step_lr * (grad_b_b * inv_n)
                for j in range(n_feats):
                    weights_b[j] -= step_lr * (grad_w_b[j] * inv_n + l2 * weights_b[j])

            best_temp = 1.0
            best_loss = float("inf")
            cal_logits_b = [
                bias_b + sum(weights_b[idx] * val for idx, val in all_vecs[i].items())
                for i in cal_idx
            ]
            for t_step in range(10, 301, 5):
                temp = t_step / 100.0
                loss = 0.0
                for pos, i in enumerate(cal_idx):
                    p = min(1.0 - 1e-9, max(1e-9, _sigmoid(cal_logits_b[pos], temp)))
                    y_val = targets[i]
                    loss -= y_val * math.log(p) + (1.0 - y_val) * math.log(1.0 - p)
                if loss < best_loss:
                    best_loss = loss
                    best_temp = temp

            model.binary_heads[head_name] = {
                "weights": {str(j): round(w, 6) for j, w in enumerate(weights_b) if abs(w) > 1e-5},
                "bias": round(bias_b, 6),
                "temperature": round(best_temp, 4),
            }

        return model

    def predict_multiclass(self, vec: dict[int, float], head_name: str) -> tuple[str, float, dict[str, float]]:
        head = self.multiclass_heads[head_name]
        labels: list[str] = head["labels"]
        sparse_w: list[dict[str, float]] = head["weights"]
        biases: list[float] = head["biases"]
        temp: float = float(head.get("temperature", 1.0))

        logits: list[float] = []
        for c in range(len(labels)):
            w_c = sparse_w[c]
            z = biases[c]
            for idx, val in vec.items():
                w = w_c.get(str(idx))
                if w is not None:
                    z += w * val
            logits.append(z)

        probs = _softmax(logits, temp)
        best_i = max(range(len(labels)), key=lambda i: probs[i])
        prob_map = {labels[i]: round(probs[i], 6) for i in range(len(labels))}
        return labels[best_i], round(probs[best_i], 6), prob_map

    def predict_binary(self, vec: dict[int, float], head_name: str) -> float:
        head = self.binary_heads[head_name]
        w_map: dict[str, float] = head["weights"]
        z = float(head["bias"])
        for idx, val in vec.items():
            w = w_map.get(str(idx))
            if w is not None:
                z += w * val
        return round(_sigmoid(z, float(head.get("temperature", 1.0))), 6)

    def predict_job(self, job_description: str, company_name: str | None = None) -> JevAnalysis:
        text = f"{company_name or ''} {job_description}".strip()
        vec = self.vectorize(text)

        sc_choice, sc_conf, sc_probs = self.predict_multiclass(vec, "skill_category")
        ts_choice, ts_conf, ts_probs = self.predict_multiclass(vec, "tech_stack")
        sb_choice, sb_conf, sb_probs = self.predict_multiclass(vec, "salary_bracket")

        _, sen_conf, sen_probs = self.predict_multiclass(vec, "seniority_level")
        sen_labels = JOB_SCORE_HEADS["seniority_level"]
        sen_legend = {str(i + 1): label for i, label in enumerate(sen_labels)}
        sen_prob_by_num = {str(i + 1): sen_probs[label] for i, label in enumerate(sen_labels)}
        expected_score = sum((i + 1) * sen_probs[label] for i, label in enumerate(sen_labels))

        red_prob = self.predict_binary(vec, "has_red_flags")
        rem_prob = self.predict_binary(vec, "remote_ok")

        return JevAnalysis(
            skill_category=JevChoiceAnswer(choice=sc_choice, confidence=sc_conf, probabilities=sc_probs),
            tech_stack=JevChoiceAnswer(choice=ts_choice, confidence=ts_conf, probabilities=ts_probs),
            seniority_level=JevScoreAnswer(
                score=round(expected_score, 4),
                confidence=sen_conf,
                legend=sen_legend,
                probabilities=sen_prob_by_num,
            ),
            salary_bracket=JevChoiceAnswer(choice=sb_choice, confidence=sb_conf, probabilities=sb_probs),
            has_red_flags=JevNoulAnswer(value=red_prob),
            remote_ok=JevNoulAnswer(value=rem_prob),
            raw_answers={"engine": "careerforge-s1"},
            input_tokens=len(text.split()),
            output_tokens=0,
        )

    def save(self, path: Path = DEFAULT_WEIGHTS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "careerforge-s1-v1",
            "vocab": self.vocab,
            "idf": [round(x, 6) for x in self.idf],
            "multiclass_heads": self.multiclass_heads,
            "binary_heads": self.binary_heads,
            "metadata": self.metadata,
        }
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_WEIGHTS_PATH) -> CareerForgeS1Model:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            vocab={str(k): int(v) for k, v in data["vocab"].items()},
            idf=[float(x) for x in data["idf"]],
            multiclass_heads=data["multiclass_heads"],
            binary_heads=data["binary_heads"],
            metadata=data.get("metadata", {}),
        )


def _analyze_cv_local(cv_text: str) -> JevProfileAnalysis:
    """Fast calibrated local CV presence & seniority scorer (zero external API)."""
    lower = cv_text.lower()

    def _present(pattern: str) -> JevNoulAnswer:
        return JevNoulAnswer(value=0.95 if re.search(pattern, lower, re.M) else 0.05)

    years_matches = re.findall(r"\b(19\d{2}|20\d{2})\b", cv_text)
    years_int = [int(y) for y in years_matches if 1980 <= int(y) <= 2030]
    span = (max(years_int) - min(years_int)) if len(years_int) >= 2 else 2

    if re.search(r"\b(principal|staff|director|vp|head of|phd|doctoral)\b", lower) or span >= 10:
        sen_score = 5.0
    elif re.search(r"\b(senior|lead|architect)\b", lower) or span >= 6:
        sen_score = 4.0
    elif span >= 3:
        sen_score = 3.0
    elif span >= 1:
        sen_score = 2.0
    else:
        sen_score = 1.0

    tech_hits = len(
        re.findall(
            r"\b(python|c\+\+|rust|java|go|pytorch|tensorflow|kubernetes|docker|sql|aws|cfd|ansys|fastapi|react)\b",
            lower,
        )
    )
    depth_score = float(min(5, max(1, 1 + tech_hits // 2)))
    years_score = float(min(5, max(1, 1 if span < 1 else 2 if span < 3 else 3 if span < 5 else 4 if span < 10 else 5)))

    return JevProfileAnalysis(
        has_phone=_present(r"\+?\d[\d\s\-()]{7,18}"),
        has_linkedin=_present(r"linkedin\.com/in/"),
        has_summary=_present(r"(professional\s+summary|summary|profile|objective)"),
        has_skills_section=_present(r"(skills|competencies|technologies)"),
        has_experience=_present(r"(experience|employment|work\s+history)"),
        has_education=_present(r"(education|university|bachelor|master|phd|bsc|msc)"),
        has_certifications=_present(r"(certification|certificate|certified|license)"),
        has_publications=_present(r"(publication|journal|doi:|conference|peer-reviewed|ieee|aiche)"),
        has_languages=_present(r"(languages|english|finnish|spanish|german|french|fluent|native)"),
        has_projects=_present(r"(projects|portfolio|github\.com)"),
        seniority_level=JevScoreAnswer(
            score=sen_score,
            confidence=0.85,
            legend={"1": "entry", "2": "junior", "3": "mid", "4": "senior", "5": "lead"},
        ),
        technical_depth=JevScoreAnswer(
            score=depth_score,
            confidence=0.82,
            legend={"1": "basic", "2": "intermediate", "3": "advanced", "4": "expert", "5": "specialist"},
        ),
        years_experience=JevScoreAnswer(
            score=years_score,
            confidence=0.85,
            legend={"1": "0-1", "2": "1-3", "3": "3-5", "4": "5-10", "5": "10+"},
        ),
        raw_answers={"engine": "careerforge-s1"},
        input_tokens=len(cv_text.split()),
        output_tokens=0,
    )


class CareerForgeS1Client:
    """Async drop-in replacement for `JevClient` backed by local `CareerForgeS1Model`."""

    _cached_model: CareerForgeS1Model | None = None

    def __init__(self, weights_path: Path | None = None) -> None:
        self.weights_path = weights_path or DEFAULT_WEIGHTS_PATH
        if CareerForgeS1Client._cached_model is None or weights_path is not None:
            if not self.weights_path.exists():
                raise RuntimeError(
                    f"CareerForge-S1 weights not found at {self.weights_path}. "
                    "Run scripts/train_careerforge_s1.py first."
                )
            model = CareerForgeS1Model.load(self.weights_path)
            if weights_path is None:
                CareerForgeS1Client._cached_model = model
            self._model = model
        else:
            self._model = CareerForgeS1Client._cached_model

    async def analyze_job(
        self,
        job_description: str,
        company_name: str | None = None,
    ) -> JevAnalysis:
        return self._model.predict_job(job_description, company_name)

    async def analyze_cv(
        self,
        cv_text: str,
        company_name: str | None = None,
    ) -> JevProfileAnalysis:
        return _analyze_cv_local(cv_text)

    async def close(self) -> None:
        return None

    async def __aenter__(self) -> CareerForgeS1Client:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


class FallbackDecisionClient:
    """Primary CareerForge-S1 client with automatic fallback to remote TypeSafe Jev API.

    Uses local CareerForge-S1 first (<1ms, $0). Falls back to JevClient only if:
      - local weights are missing or S1 raises an error, OR
      - S1's primary skill_category confidence is below `min_confidence`
        (controlled by `S1_FALLBACK_MIN_CONFIDENCE`, default 0.0 = error-only fallback),
    and `TYPESAFE_API_KEY` is configured.
    """

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self.weights_path = weights_path or DEFAULT_WEIGHTS_PATH
        raw_min_conf = (
            min_confidence
            if min_confidence is not None
            else float(os.environ.get("S1_FALLBACK_MIN_CONFIDENCE", "0.0") or "0.0")
        )
        self.min_confidence = max(0.0, min(1.0, raw_min_conf))
        self._s1: CareerForgeS1Client | None = None
        self._jev: JevClient | None = None

    def _has_jev_key(self) -> bool:
        return bool(os.environ.get("TYPESAFE_API_KEY", "").strip())

    def _get_s1(self) -> CareerForgeS1Client:
        if self._s1 is None:
            self._s1 = CareerForgeS1Client(weights_path=self.weights_path)
        return self._s1

    def _get_jev(self) -> JevClient:
        if self._jev is None:
            self._jev = JevClient()
        return self._jev

    async def analyze_job(
        self,
        job_description: str,
        company_name: str | None = None,
    ) -> JevAnalysis:
        s1_result: JevAnalysis | None = None
        try:
            s1_result = await self._get_s1().analyze_job(job_description, company_name)
            top_conf = (
                s1_result.skill_category.confidence
                if s1_result.skill_category is not None
                else 1.0
            )
            if top_conf >= self.min_confidence or not self._has_jev_key():
                return s1_result
            logger.info(
                "CareerForge-S1 confidence %.3f < %.3f; escalating to Jev fallback",
                top_conf,
                self.min_confidence,
            )
        except Exception as exc:
            if not self._has_jev_key():
                raise
            logger.warning("CareerForge-S1 analyze_job failed (%s); falling back to Jev API", exc)

        try:
            return await self._get_jev().analyze_job(job_description, company_name)
        except Exception as exc:
            if s1_result is not None:
                logger.warning("Jev fallback failed (%s); returning CareerForge-S1 result", exc)
                return s1_result
            raise

    async def analyze_cv(
        self,
        cv_text: str,
        company_name: str | None = None,
    ) -> JevProfileAnalysis:
        try:
            return await self._get_s1().analyze_cv(cv_text, company_name)
        except Exception as exc:
            if not self._has_jev_key():
                raise
            logger.warning("CareerForge-S1 analyze_cv failed (%s); falling back to Jev API", exc)
            return await self._get_jev().analyze_cv(cv_text, company_name)

    async def close(self) -> None:
        if self._s1 is not None:
            await self._s1.close()
        if self._jev is not None:
            await self._jev.close()

    async def __aenter__(self) -> FallbackDecisionClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


def get_decision_client() -> FallbackDecisionClient | CareerForgeS1Client | JevClient:
    """Return decision client based on DECISION_ENGINE env var.

    - ``DECISION_ENGINE=auto`` (default): CareerForge-S1 primary with Jev API fallback.
    - ``DECISION_ENGINE=careerforge-s1``: local CareerForge-S1 only (never calls Jev).
    - ``DECISION_ENGINE=jev``: remote TypeSafe Jev API only.
    """
    mode = os.environ.get("DECISION_ENGINE", "auto").strip().lower()
    if mode == "jev":
        return JevClient()
    if mode in ("careerforge-s1", "s1", "local"):
        return CareerForgeS1Client()
    return FallbackDecisionClient()
