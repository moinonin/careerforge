#!/usr/bin/env python3
"""Train, calibrate against live Jev (optional), and benchmark CareerForge-S1.

Usage:
    # Distill & calibrate directly against live Jev (uses TYPESAFE_API_KEY from .env):
    .venv/bin/python scripts/train_careerforge_s1.py --use-jev

    # Offline / cached mode (reuses cached Jev teacher labels if present):
    .venv/bin/python scripts/train_careerforge_s1.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from backend.jev import JevClient
from backend.s1.model import (
    DEFAULT_WEIGHTS_PATH,
    JOB_BINARY_HEADS,
    JOB_CHOICE_HEADS,
    JOB_SCORE_HEADS,
    CareerForgeS1Model,
)

CACHE_PATH = ROOT / "artifacts" / "s1_jev_teacher_cache.jsonl"


def _build_seed_jds() -> list[dict[str, Any]]:
    """Build a diverse, realistic 120-JD benchmark corpus spanning all Jev heads."""
    templates: list[tuple[str, str, str, list[str]]] = [
        (
            "backend",
            "python_fastapi",
            "Build high-throughput REST and GraphQL APIs in Python using FastAPI, SQLAlchemy, PostgreSQL, and Redis.",
            ["microservices", "async I/O", "Celery workers", "Pytest", "OAuth2 authentication", "Django REST APIs"],
        ),
        (
            "backend",
            "node_js",
            "Develop scalable server-side services in Node.js, TypeScript, Express, and PostgreSQL with event-driven queues.",
            ["NestJS", "RESTful APIs", "WebSockets", "MongoDB", "Kafka consumers", "GraphQL gateway"],
        ),
        (
            "backend",
            "java",
            "Architect enterprise backend microservices using Java 21, Spring Boot, Hibernate, Kafka, and relational databases.",
            ["Kotlin services", "gRPC", "JVM tuning", "Oracle/Postgres", "distributed transactions", "Maven/Gradle"],
        ),
        (
            "backend",
            "go",
            "Design low-latency backend systems in Go and Rust with gRPC, Protobuf, concurrency primitives, and Linux tuning.",
            ["C++ core engine", "distributed consensus", "high-frequency APIs", "Prometheus metrics", "zero-allocation parsers", "NATS"],
        ),
        (
            "backend",
            "ruby",
            "Maintain and scale core backend platform built on Ruby on Rails, Sidekiq, PostgreSQL, and RSpec.",
            ["ActiveRecord optimization", "Rails API", "background jobs", "Stripe billing", "GraphQL Ruby", "Redis caching"],
        ),
        (
            "backend",
            "dotnet",
            "Engineer mission-critical backend APIs using C#, .NET 8, ASP.NET Core, Entity Framework, and SQL Server.",
            ["Azure Service Bus", "WCF migration", "xUnit", "distributed caching", "REST APIs", "Microservices on .NET"],
        ),
        (
            "frontend",
            "node_js",
            "Craft responsive web applications using React, Next.js, TypeScript, Tailwind CSS, and modern browser APIs.",
            ["design systems", "WCAG accessibility", "state management", "Core Web Vitals", "Jest/Playwright", "Vue/Nuxt UI"],
        ),
        (
            "fullstack",
            "python_fastapi",
            "Own end-to-end features across a React/Next.js frontend and Python FastAPI/Django backend with PostgreSQL.",
            ["TypeScript UI", "REST API design", "database migrations", "full-stack SaaS", "CI/CD", "Stripe integration"],
        ),
        (
            "fullstack",
            "node_js",
            "Build full-stack web products with TypeScript, React, Next.js frontend and Node.js Express backend services.",
            ["Prisma ORM", "tRPC", "PostgreSQL", "Tailwind CSS", "end-to-end ownership", "GraphQL"],
        ),
        (
            "devops",
            "go",
            "Automate cloud infrastructure, Kubernetes clusters, Terraform IaC, CI/CD pipelines, and observability stacks.",
            ["AWS/GCP", "Docker containers", "Helm charts", "Prometheus/Grafana", "GitHub Actions", "SRE on-call reliability"],
        ),
        (
            "data",
            "python_fastapi",
            "Build ETL/ELT data pipelines, analytics warehouses, and ML feature stores using Python, SQL, Spark, and dbt.",
            ["Airflow orchestration", "Snowflake/BigQuery", "PyTorch modeling", "data quality monitoring", "Pandas/Polars", "streaming Kafka"],
        ),
        (
            "mobile",
            "java",
            "Develop native and cross-platform mobile applications for iOS and Android using Kotlin, Swift, and React Native.",
            ["Jetpack Compose", "SwiftUI", "offline sync", "App Store/Play Store releases", "mobile performance", "push notifications"],
        ),
    ]

    seniority_specs: list[tuple[int, str, str, str]] = [
        (1, "entry", "under_80k", "Graduate / Entry-Level (0-1 years experience). Salary $62,000 - $75,000."),
        (2, "junior", "80k_120k", "Junior Engineer (1-2 years experience). Compensation $85,000 - $105,000."),
        (3, "mid", "80k_120k", "Mid-Level Engineer (3-5 years experience). Base salary $105,000 - $120,000."),
        (4, "senior", "120k_160k", "Senior Engineer (5-8 years experience). Salary range $135,000 - $158,000."),
        (5, "staff", "160k_200k", "Staff Engineer (8+ years leading architecture). Total comp $170,000 - $195,000."),
        (6, "principal", "200k_plus", "Principal Engineer (10+ years, org-wide technical strategy). Comp $220,000 - $270,000 + equity."),
    ]

    remote_phrases = [
        (1.0, "100% remote / work from anywhere with async distributed team collaboration."),
        (1.0, "Fully remote position across EU/US timezones with home-office stipend."),
        (0.0, "Strictly onsite 5 days/week at our headquarters office. No remote work."),
        (0.0, "In-person office presence required daily in our downtown facility."),
    ]

    red_flag_phrases = [
        (0.0, "Clear roadmap, transparent compensation, structured interview process, healthy work-life balance."),
        (0.0, "Well-scoped responsibilities, collaborative code reviews, dedicated learning budget."),
        (
            1.0,
            "Looking for a 10x rockstar ninja willing to wear every hat, work 70-hour weeks, "
            "unpaid overtime, fast-paced family culture, salary competitive TBD after trial.",
        ),
        (
            1.0,
            "Must have 10 years experience in 2-year-old frameworks, mandatory unpaid weekend on-call, "
            "no clear job scope, equity-only until Series A.",
        ),
    ]

    rng = random.Random(42)
    rows: list[dict[str, Any]] = []
    idx = 0
    for cat, stack, base_desc, extras in templates:
        for sen_num, sen_label, sal_bracket, sen_desc in seniority_specs:
            # Generate 2 distinct variations per (template, seniority) = 144 JDs
            for rep in range(2):
                picked_extras = rng.sample(extras, k=3)
                rem_val, rem_txt = remote_phrases[(idx + rep) % len(remote_phrases)]
                red_val, red_txt = red_flag_phrases[(idx + rep * 2) % len(red_flag_phrases)]
                title = f"{sen_label.title()} {cat.title()} Engineer"
                jd = (
                    f"Title: {title}\n"
                    f"{sen_desc}\n"
                    f"{base_desc} Key technologies: {', '.join(picked_extras)}.\n"
                    f"Work arrangement: {rem_txt}\n"
                    f"Culture & expectations: {red_txt}"
                )
                rows.append(
                    {
                        "id": f"jd_{idx:03d}",
                        "jd": jd,
                        "gold": {
                            "skill_category": cat,
                            "tech_stack": stack,
                            "seniority_level": sen_label,
                            "salary_bracket": sal_bracket,
                            "has_red_flags": red_val,
                            "remote_ok": rem_val,
                        },
                    }
                )
                idx += 1
    return rows


async def _fetch_jev_teacher_labels(
    dataset: list[dict[str, Any]],
    *,
    max_live: int = 80,
) -> dict[str, dict[str, Any]]:
    """Query live JevClient to collect calibrated teacher soft labels (cached to disk)."""
    cached: dict[str, dict[str, Any]] = {}
    if CACHE_PATH.exists():
        for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                cached[rec["id"]] = rec["jev"]

    to_fetch = [row for row in dataset[:max_live] if row["id"] not in cached]
    if not to_fetch:
        return cached

    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        print("TYPESAFE_API_KEY not set — skipping live Jev fetch.")
        return cached

    print(f"Fetching live Jev teacher labels for {len(to_fetch)} JDs (cached={len(cached)})...")
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)

    async with JevClient(api_key=api_key) as client:
        async def _one(row: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
            async with sem:
                try:
                    ans = await client.analyze_job(row["jd"])
                    return row["id"], {
                        "skill_category": ans.skill_category.probabilities if ans.skill_category else {},
                        "tech_stack": ans.tech_stack.probabilities if ans.tech_stack else {},
                        "seniority_level": ans.seniority_level.probabilities if ans.seniority_level else {},
                        "seniority_legend": ans.seniority_level.legend if ans.seniority_level else {},
                        "salary_bracket": ans.salary_bracket.probabilities if ans.salary_bracket else {},
                        "has_red_flags": ans.has_red_flags.value if ans.has_red_flags else 0.5,
                        "remote_ok": ans.remote_ok.value if ans.remote_ok else 0.5,
                    }
                except Exception as exc:
                    print(f"  Jev failed on {row['id']}: {exc}")
                    return row["id"], None

        results = await asyncio.gather(*(_one(r) for r in to_fetch))

    with CACHE_PATH.open("a", encoding="utf-8") as handle:
        for row_id, jev_data in results:
            if jev_data is not None:
                cached[row_id] = jev_data
                handle.write(json.dumps({"id": row_id, "jev": jev_data}) + "\n")
    print(f"Total Jev teacher labels available: {len(cached)}")
    return cached


def _probs_from_jev_or_gold(
    row: dict[str, Any],
    jev_map: dict[str, dict[str, Any]],
    head_name: str,
    labels: list[str],
) -> list[float]:
    jev = jev_map.get(row["id"])
    if jev and jev.get(head_name):
        raw = jev[head_name]
        if head_name == "seniority_level":
            # Jev returns {"1": p1, "2": p2, ...} or label-keyed probs
            vec = [float(raw.get(str(i + 1), raw.get(lbl, 0.0))) for i, lbl in enumerate(labels)]
        else:
            vec = [float(raw.get(lbl, 0.0)) for lbl in labels]
        total = sum(vec)
        if total > 0.0:
            return [v / total for v in vec]
    gold_label = row["gold"][head_name]
    return [1.0 if lbl == gold_label else 0.0 for lbl in labels]


def _binary_from_jev_or_gold(row: dict[str, Any], jev_map: dict[str, dict[str, Any]], head_name: str) -> float:
    jev = jev_map.get(row["id"])
    if jev and head_name in jev:
        return float(jev[head_name])
    return float(row["gold"][head_name])


def _macro_f1_and_confusion(y_true: list[str], y_pred: list[str], labels: list[str]) -> tuple[float, float, list[list[int]]]:
    idx = {lbl: i for i, lbl in enumerate(labels)}
    n = len(labels)
    cm = [[0] * n for _ in range(n)]
    correct = 0
    for t, p in zip(y_true, y_pred):
        cm[idx[t]][idx[p]] += 1
        if t == p:
            correct += 1
    f1s: list[float] = []
    for i in range(n):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(n)) - tp
        fn = sum(cm[i][c] for c in range(n)) - tp
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append((2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0)
    acc = correct / max(1, len(y_true))
    macro_f1 = sum(f1s) / max(1, len(f1s))
    return acc, macro_f1, cm


def _roc_auc(y_true: list[int], y_score: list[float]) -> float:
    pos = [s for y, s in zip(y_true, y_score) if y == 1]
    neg = [s for y, s in zip(y_true, y_score) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for sp in pos:
        for sn in neg:
            if sp > sn:
                wins += 1.0
            elif sp == sn:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def _ece_binary(y_true: list[int], y_prob: list[float], bins: int = 10) -> float:
    n = len(y_true)
    if n == 0:
        return 0.0
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        members = [(y, p) for y, p in zip(y_true, y_prob) if (lo <= p < hi) or (b == bins - 1 and p == hi)]
        if not members:
            continue
        avg_p = sum(p for _, p in members) / len(members)
        avg_y = sum(y for y, _ in members) / len(members)
        ece += (len(members) / n) * abs(avg_p - avg_y)
    return ece


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-jev", action="store_true", help="Query live Jev teacher for soft labels")
    parser.add_argument("--max-live", type=int, default=96, help="Max live Jev API calls")
    parser.add_argument("--epochs", type=int, default=140)
    args = parser.parse_args()

    dataset = _build_seed_jds()
    rng = random.Random(42)
    rng.shuffle(dataset)

    jev_map: dict[str, dict[str, Any]] = {}
    if args.use_jev:
        jev_map = asyncio.run(_fetch_jev_teacher_labels(dataset, max_live=args.max_live))
    elif CACHE_PATH.exists():
        for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                jev_map[rec["id"]] = rec["jev"]

    # If Jev teacher labels exist, use Jev-labeled subset as primary calibrated corpus
    eval_pool = [r for r in dataset if r["id"] in jev_map] if len(jev_map) >= 40 else dataset
    split = int(len(eval_pool) * 0.75)
    train_rows = eval_pool[:split]
    test_rows = eval_pool[split:]

    all_mc_heads = {**JOB_CHOICE_HEADS, **JOB_SCORE_HEADS}
    train_mc = {
        h: [_probs_from_jev_or_gold(r, jev_map, h, labels) for r in train_rows]
        for h, labels in all_mc_heads.items()
    }
    train_bin = {
        h: [_binary_from_jev_or_gold(r, jev_map, h) for r in train_rows]
        for h in JOB_BINARY_HEADS
    }

    t0 = time.perf_counter()
    model = CareerForgeS1Model.fit_distilled(
        [r["jd"] for r in train_rows],
        train_mc,
        train_bin,
        epochs=args.epochs,
        lr=1.5,
        l2=1e-4,
    )
    train_sec = time.perf_counter() - t0
    model.metadata = {
        "trained_on_rows": len(train_rows),
        "tested_on_rows": len(test_rows),
        "jev_teacher_rows": sum(1 for r in train_rows if r["id"] in jev_map),
        "train_seconds": round(train_sec, 3),
    }
    model.save(DEFAULT_WEIGHTS_PATH)

    # ── Benchmark Inference Latency & Held-Out Metrics ──
    t_inf0 = time.perf_counter()
    test_preds = [model.predict_job(r["jd"]) for r in test_rows]
    avg_ms = ((time.perf_counter() - t_inf0) / max(1, len(test_rows))) * 1000.0

    teacher_tag = "Jev Teacher" if sum(1 for r in test_rows if r["id"] in jev_map) > 0 else "Gold Labels"
    print(f"\n=== CareerForge-S1 Evaluation (vs {teacher_tag}) ===")
    print(f"Train: {len(train_rows)} | Held-out Test: {len(test_rows)} | Jev-distilled: {model.metadata['jev_teacher_rows']} | Train time: {train_sec:.2f}s | Inference: {avg_ms:.3f} ms/JD")
    print(f"Weights saved -> {DEFAULT_WEIGHTS_PATH} ({DEFAULT_WEIGHTS_PATH.stat().st_size / 1024:.1f} KB)\n")

    for h, labels in all_mc_heads.items():
        y_true: list[str] = []
        y_pred: list[str] = []
        kls: list[float] = []
        for r, pred in zip(test_rows, test_preds):
            t_probs = _probs_from_jev_or_gold(r, jev_map, h, labels)
            y_true.append(labels[max(range(len(labels)), key=lambda i: t_probs[i])])
            if h == "seniority_level":
                p_map = pred.seniority_level.probabilities if pred.seniority_level else {}
                p_probs = [float(p_map.get(str(i + 1), 1e-9)) for i in range(len(labels))]
                y_pred.append(labels[max(range(len(labels)), key=lambda i: p_probs[i])])
            else:
                ans = getattr(pred, h)
                y_pred.append(ans.choice)
                p_probs = [float(ans.probabilities.get(lbl, 1e-9)) for lbl in labels]
            kl = sum(tp * math.log(max(1e-9, tp) / max(1e-9, pp)) for tp, pp in zip(t_probs, p_probs) if tp > 1e-9)
            kls.append(kl)

        acc, mf1, cm = _macro_f1_and_confusion(y_true, y_pred, labels)
        temp = model.multiclass_heads[h]["temperature"]
        print(f"[{h}] Acc={acc:.3f} | Macro-F1={mf1:.3f} | Mean-KL={sum(kls)/len(kls):.4f} | Temp={temp:.2f}")
        print(f"  Labels: {labels}")
        print(f"  Confusion Matrix: {cm}")

    print()
    for h in JOB_BINARY_HEADS:
        y_true_f = [_binary_from_jev_or_gold(r, jev_map, h) for r in test_rows]
        y_true_b = [1 if v >= 0.5 else 0 for v in y_true_f]
        y_prob = [getattr(pred, h).value for pred in test_preds]
        y_pred_b = [1 if p >= 0.5 else 0 for p in y_prob]
        tp = sum(1 for t, p in zip(y_true_b, y_pred_b) if t == 1 and p == 1)
        fp = sum(1 for t, p in zip(y_true_b, y_pred_b) if t == 0 and p == 1)
        fn = sum(1 for t, p in zip(y_true_b, y_pred_b) if t == 1 and p == 0)
        tn = sum(1 for t, p in zip(y_true_b, y_pred_b) if t == 0 and p == 0)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        auc = _roc_auc(y_true_b, y_prob)
        brier = sum((p - t) ** 2 for p, t in zip(y_prob, y_true_f)) / len(y_prob)
        ece = _ece_binary(y_true_b, y_prob)
        temp = model.binary_heads[h]["temperature"]
        print(
            f"[{h}] F1={f1:.3f} | ROC-AUC={auc:.3f} | Brier={brier:.4f} | ECE={ece:.4f} | Temp={temp:.2f} | CM(TN={tn},FP={fp},FN={fn},TP={tp})"
        )


if __name__ == "__main__":
    main()
