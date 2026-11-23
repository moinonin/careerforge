"""Tests proving CareerForge-S1 works end-to-end with NO TYPESAFE_API_KEY."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from backend.jev import JevAnalysis, JevChoiceAnswer
from backend.s1 import (
    DEFAULT_WEIGHTS_PATH,
    FallbackDecisionClient,
    get_decision_client,
)


@pytest.mark.asyncio
async def test_s1_works_without_typesafe_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("DECISION_ENGINE", "auto")

    assert DEFAULT_WEIGHTS_PATH.exists(), "weights.json must be trained and present"
    client = get_decision_client()
    assert isinstance(client, FallbackDecisionClient)

    async with client:
        analysis = await client.analyze_job(
            "Senior Python FastAPI Backend Engineer. 5+ years building async APIs, PostgreSQL, Redis. "
            "100% remote distributed team. Salary $140,000 - $155,000. Clear roadmap and healthy culture."
        )
        assert analysis.skill_category is not None
        assert analysis.skill_category.choice == "backend"
        assert analysis.tech_stack is not None
        assert analysis.tech_stack.choice == "python_fastapi"
        assert analysis.remote_ok is not None and analysis.remote_ok.value > 0.5
        assert analysis.has_red_flags is not None and analysis.has_red_flags.value < 0.5
        ctx = analysis.to_context_dict()
        assert ctx["primary_skill_category"] == "backend"
        assert ctx["primary_tech_stack"] == "python_fastapi"


@pytest.mark.asyncio
async def test_s1_analyze_cv_without_typesafe_api_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("DECISION_ENGINE", "careerforge-s1")

    sample_cv = (
        "Nicolus Rotich, PhD\n"
        "+358 40 501 4334 | linkedin.com/in/rotichtheengineer\n"
        "Professional Summary: Computational engineer (2013-2026).\n"
        "Skills: Python, PyTorch, C++, Rust, Docker, Kubernetes, ANSYS CFD.\n"
        "Experience: Senior Quant Researcher 2019-2026.\n"
        "Education: PhD Chemical Engineering, LUT University.\n"
        "Publications: Chemical Engineering Journal doi:10.1016/j.cej.2017.05.136.\n"
        "Languages: English (Fluent), Finnish.\n"
    )
    async with get_decision_client() as client:
        profile_analysis = await client.analyze_cv(sample_cv)
        assert profile_analysis.has_phone is not None and profile_analysis.has_phone.value > 0.5
        assert profile_analysis.has_linkedin is not None and profile_analysis.has_linkedin.value > 0.5
        assert profile_analysis.has_publications is not None and profile_analysis.has_publications.value > 0.5
        assert profile_analysis.seniority_level is not None and profile_analysis.seniority_level.score >= 4.0


@pytest.mark.asyncio
async def test_fallback_to_jev_when_s1_weights_missing(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    client = FallbackDecisionClient(weights_path=Path("/nonexistent/weights.json"))
    mock_jev = AsyncMock()
    mock_jev.analyze_job.return_value = JevAnalysis(
        skill_category=JevChoiceAnswer(choice="devops", confidence=0.92),
        raw_answers={"engine": "jev-fallback"},
    )
    client._jev = mock_jev

    async with client:
        result = await client.analyze_job("Kubernetes Terraform SRE")
        assert result.skill_category is not None
        assert result.skill_category.choice == "devops"
        mock_jev.analyze_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_to_jev_on_low_confidence_escalation(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    client = FallbackDecisionClient(min_confidence=0.60)
    mock_s1 = AsyncMock()
    mock_s1.analyze_job.return_value = JevAnalysis(
        skill_category=JevChoiceAnswer(choice="backend", confidence=0.40),
        raw_answers={"engine": "careerforge-s1"},
    )
    mock_jev = AsyncMock()
    mock_jev.analyze_job.return_value = JevAnalysis(
        skill_category=JevChoiceAnswer(choice="data", confidence=0.95),
        raw_answers={"engine": "jev-escalated"},
    )
    client._s1 = mock_s1
    client._jev = mock_jev

    async with client:
        result = await client.analyze_job("Ambiguous general generalist role with unclear scope")
        assert result.raw_answers.get("engine") == "jev-escalated"
        mock_s1.analyze_job.assert_awaited_once()
        mock_jev.analyze_job.assert_awaited_once()
