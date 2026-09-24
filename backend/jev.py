"""Jev (TypeSafe System One) decision model client.

Jev returns typed decisions with calibrated probabilities instead of
free-form text.  It is ~0.7s latency and $0.042/M input tokens —
ideal for fast classification tasks (skill extraction, seniority
scoring, red-flag detection) whose output is then used as structured
context for the text-generation LLM (Ollama specgen, OpenAI, etc.).

Key differences from an LLM:
  - No text generation — only typed choices, scores, and booleans
  - Cannot hallucinate — output shape is guaranteed by construction
  - Extremely fast and cheap
  - Input is text only (no images/audio)

Usage:
    from backend.jev import JevClient, JevAnalysis

    client = JevClient()
    analysis = await client.analyze_job(job_description, company_name)
    # analysis.skill_category, analysis.tech_stack, analysis.seniority, etc.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

API_BASE = "https://api.typesafe.ai/v1/systemone"


@dataclass
class JevSkillCategory:
    category: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass
class JevNoulAnswer:
    value: float  # 0.0 – 1.0


@dataclass
class JevScoreAnswer:
    score: float
    confidence: float
    legend: dict[str, str] = field(default_factory=dict)
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass
class JevChoiceAnswer:
    choice: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass
class JevAnalysis:
    """Structured result from Jev's job analysis."""

    skill_category: JevChoiceAnswer | None = None
    tech_stack: JevChoiceAnswer | None = None
    seniority_level: JevScoreAnswer | None = None
    salary_bracket: JevChoiceAnswer | None = None
    has_red_flags: JevNoulAnswer | None = None
    remote_ok: JevNoulAnswer | None = None
    # Raw answers for extensibility
    raw_answers: dict[str, Any] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def has_red_flags_bool(self) -> bool:
        """Convenience: True if red-flag probability exceeds 0.5."""
        if self.has_red_flags:
            return self.has_red_flags.value > 0.5
        return False

    @property
    def remote_ok_bool(self) -> bool:
        """Convenience: True if remote probability exceeds 0.5."""
        if self.remote_ok:
            return self.remote_ok.value > 0.5
        return False

    def to_context_dict(self) -> dict[str, Any]:
        """Convert analysis to a dict suitable for LLM prompt context."""
        result: dict[str, Any] = {}
        if self.skill_category:
            result["primary_skill_category"] = self.skill_category.choice
        if self.tech_stack:
            result["primary_tech_stack"] = self.tech_stack.choice
        if self.seniority_level:
            result["seniority_level"] = self.seniority_level.score
            result["seniority_label"] = self.seniority_level.legend.get(
                str(int(self.seniority_level.score)), "unknown"
            )
        if self.salary_bracket:
            result["salary_bracket"] = self.salary_bracket.choice
        if self.has_red_flags:
            result["has_red_flags"] = self.has_red_flags.value
        if self.remote_ok:
            result["remote_ok"] = self.remote_ok.value
        return result


class JevClient:
    """Client for the TypeSafe System One (Jev) API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY", "")
        self.model = "jev-latest"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def analyze_job(
        self,
        job_description: str,
        company_name: str | None = None,
    ) -> JevAnalysis:
        """Analyze a job description and return structured data.

        Sends the job description as `state` and a set of typed questions
        to Jev.  Returns a ``JevAnalysis`` with calibrated probabilities.

        Args:
            job_description: The full job posting text.
            company_name: Optional company name for additional context.

        Returns:
            Structured analysis with skill category, tech stack, seniority,
            salary bracket, red flags, and remote availability.

        Raises:
            RuntimeError: If the API call fails or returns an error.
        """
        state: dict[str, Any] = {"job_description": job_description}
        if company_name:
            state["company_name"] = company_name

        questions: dict[str, Any] = {
            "skill_category": {
                "type": "choice",
                "options": ["backend", "frontend", "fullstack", "devops", "data", "mobile"],
                "instructions": "What is the primary skill category for this role?",
                "criteria": {
                    "backend": "Server-side logic, APIs, databases",
                    "frontend": "UI/UX, browser-side code",
                    "fullstack": "Both frontend and backend",
                    "devops": "Infrastructure, CI/CD, deployment",
                    "data": "Data engineering, analytics",
                    "mobile": "Mobile app development",
                },
            },
            "tech_stack": {
                "type": "choice",
                "options": ["python_fastapi", "node_js", "java", "go", "ruby", "dotnet"],
                "instructions": "What is the primary backend technology?",
                "criteria": {
                    "python_fastapi": "Python, FastAPI, Django, Flask",
                    "node_js": "JavaScript, Node.js, Express",
                    "java": "Java, Spring, Kotlin",
                    "go": "Go, Rust, C++",
                    "ruby": "Ruby, Rails",
                    "dotnet": "C#, .NET",
                },
            },
            "seniority_level": {
                "type": "score",
                "instructions": "What seniority level is this role?",
                "criteria": ["entry", "junior", "mid", "senior", "staff", "principal"],
            },
            "salary_bracket": {
                "type": "choice",
                "options": ["under_80k", "80k_120k", "120k_160k", "160k_200k", "200k_plus"],
                "instructions": "What salary bracket does this role fall into?",
                "criteria": {
                    "under_80k": "Entry-level or contract positions",
                    "80k_120k": "Mid-level roles",
                    "120k_160k": "Senior roles at startups or mid-size companies",
                    "160k_200k": "Staff/principal at large companies",
                    "200k_plus": "Executive or specialized roles",
                },
            },
            "has_red_flags": {
                "type": "noul",
                "instructions": "Does this job description contain red flags like vague requirements or unrealistic expectations?",
            },
            "remote_ok": {
                "type": "noul",
                "instructions": "Does this role support remote or distributed work?",
            },
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "state": state,
            "questions": questions,
        }

        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._client.post(
                API_BASE, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Jev API call failed: {exc}") from exc

        if "detail" in data:
            raise RuntimeError(f"Jev API error: {json.dumps(data['detail'])}")

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> JevAnalysis:
        """Parse the raw Jev response into a JevAnalysis dataclass."""
        answers = data.get("answers", {})
        usage = data.get("usage", {})

        skill_category_data = answers.get("skill_category", {})
        skill_category = JevChoiceAnswer(
            choice=skill_category_data.get("choice", ""),
            confidence=skill_category_data.get("confidence", 0.0),
            probabilities=skill_category_data.get("probabilities", {}),
        ) if skill_category_data.get("choice") else None

        tech_stack_data = answers.get("tech_stack", {})
        tech_stack = JevChoiceAnswer(
            choice=tech_stack_data.get("choice", ""),
            confidence=tech_stack_data.get("confidence", 0.0),
            probabilities=tech_stack_data.get("probabilities", {}),
        ) if tech_stack_data.get("choice") else None

        seniority_data = answers.get("seniority_level", {})
        seniority_level = JevScoreAnswer(
            score=seniority_data.get("score", 0.0),
            confidence=seniority_data.get("confidence", 0.0),
            legend=seniority_data.get("legend", {}),
            probabilities=seniority_data.get("probabilities", {}),
        ) if seniority_data.get("score") else None

        salary_data = answers.get("salary_bracket", {})
        salary_bracket = JevChoiceAnswer(
            choice=salary_data.get("choice", ""),
            confidence=salary_data.get("confidence", 0.0),
            probabilities=salary_data.get("probabilities", {}),
        ) if salary_data.get("choice") else None

        noul_skill = answers.get("has_red_flags", {})
        has_red_flags = JevNoulAnswer(value=noul_skill.get("noul", 0.0))

        noul_remote = answers.get("remote_ok", {})
        remote_ok = JevNoulAnswer(value=noul_remote.get("noul", 0.0))

        return JevAnalysis(
            skill_category=skill_category,
            tech_stack=tech_stack,
            seniority_level=seniority_level,
            salary_bracket=salary_bracket,
            has_red_flags=has_red_flags,
            remote_ok=remote_ok,
            raw_answers=answers,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> JevClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
