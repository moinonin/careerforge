"""Jev-enhanced job analyzer — uses TypeSafe System One for fast structured
classification, then feeds the result into the LLM for detailed analysis."""

from __future__ import annotations

import json
from typing import Any

from backend.database import get_session
from backend.jev import JevClient, JevAnalysis
from backend.llm.adapter import GenerationError
from backend.llm.router import build_adapter
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["analyzer"])


class JevAnalyzerRequest(BaseModel):
    """Request body for ``POST /api/v1/analyzer/jev``."""

    job_description: str
    company_name: str | None = None
    use_llm_fallback: bool = True
    """If True, fall back to the standard LLM analyzer if Jev fails."""


class JevAnalyzerResponse(BaseModel):
    """Response body for Jev-enhanced analysis."""

    required_skills: list[str]
    implied_skills: list[str]
    red_flags: list[str]
    jev_analysis: dict[str, Any]
    llm_enrichment: dict[str, Any] | None = None
    salary_estimate: dict[str, Any] | None = None
    keyword_coverage: dict[str, Any] | None = None


@router.post("/jev", response_model=JevAnalyzerResponse, status_code=status.HTTP_200_OK)
async def analyze_job_post_jev(
    request: JevAnalyzerRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Analyze a job description using Jev + LLM hybrid pipeline.

    **Step 1 (Jev, ~0.7s):** Classify the job description into structured
    categories — skill category, tech stack, seniority, salary bracket,
    red flags, remote availability. Jev returns calibrated probabilities
    with zero hallucination.

    **Step 2 (LLM, ~12s):** Use Jev's structured output as prompt context
    to generate detailed skill lists, implied skills, and salary estimates.
    The LLM sees Jev's analysis as part of the prompt, so it generates
    more targeted and accurate results.

    Body::
        {"job_description": "Senior Python Engineer..."}

    Returns::
        {
            "required_skills": [...],
            "implied_skills": [...],
            "red_flags": [...],
            "jev_analysis": {
                "skill_category": {"choice": "backend", "confidence": 1.0, ...},
                "tech_stack": {"choice": "python_fastapi", "confidence": 1.0, ...},
                "seniority_level": {"score": 3.0, "confidence": 1.0, ...},
                "salary_bracket": {"choice": "120k_160k", "confidence": 1.0, ...},
                "has_red_flags": {"noul": 0.23},
                "remote_ok": {"noul": 0.56}
            },
            "llm_enrichment": { ... },
            "salary_estimate": { ... },
            "keyword_coverage": null
        }

    No account required.  Jev handles classification (~0.7s, $0.042/M tokens),
    the LLM handles detailed generation (~12s, model-dependent).
    """
    job_description = request.job_description.strip()
    company_name = request.company_name or None

    if not job_description or len(job_description) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_description must be at least 10 characters",
        )

    try:
        result = await _run_jev_analyzer(job_description, company_name, request.use_llm_fallback)
    except GenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM analysis failed: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Jev analysis failed: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Analyzer failed: {exc}",
        ) from exc

    return result


async def _run_jev_analyzer(
    job_description: str,
    company_name: str | None,
    use_llm_fallback: bool,
) -> dict[str, Any]:
    """Run Jev classification followed by LLM enrichment."""

    # ── Step 1: Jev classification (~0.7s) ──────────────────────────
    jev_analysis: JevAnalysis | None = None
    jev_raw: dict[str, Any] = {}

    try:
        async with JevClient() as client:
            jev_analysis = await client.analyze_job(job_description, company_name)
            jev_raw = jev_analysis.to_context_dict()
    except RuntimeError as exc:
        if not use_llm_fallback:
            raise
        # Jev failed but fallback is allowed — proceed with empty context
        jev_raw = {}

    # ── Step 2: LLM enrichment with Jev context ─────────────────────
    adapter = build_adapter()

    prompt = _build_jev_enrichment_prompt(job_description, company_name, jev_raw)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "required_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "implied_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "red_flags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "salary_estimate": {
                "type": "object",
                "properties": {
                    "range": {"type": "string"},
                    "currency": {"type": "string"},
                    "location": {"type": "string"},
                },
            },
        },
        "required": ["required_skills", "implied_skills", "red_flags"],
    }

    llm_response = await adapter.generate(prompt, schema)
    llm_enrichment: dict[str, Any] = {
        "required_skills": _normalize_skill_list(llm_response.get("required_skills", [])),
        "implied_skills": _normalize_skill_list(llm_response.get("implied_skills", [])),
        "red_flags": _normalize_skill_list(llm_response.get("red_flags", [])),
        "salary_estimate": llm_response.get("salary_estimate"),
    }

    return {
        "required_skills": llm_enrichment["required_skills"],
        "implied_skills": llm_enrichment["implied_skills"],
        "red_flags": llm_enrichment["red_flags"],
        "jev_analysis": jev_raw if jev_raw else jev_analysis.__dict__ if jev_analysis else {},
        "llm_enrichment": llm_enrichment,
        "salary_estimate": llm_enrichment["salary_estimate"],
        "keyword_coverage": None,
    }


def _build_jev_enrichment_prompt(
    job_description: str,
    company_name: str | None,
    jev_context: dict[str, Any],
) -> str:
    """Build the prompt with Jev's structured analysis as context."""

    jev_section = ""
    if jev_context:
        parts = []
        if jev_context.get("primary_skill_category"):
            parts.append(f"- Primary skill category: {jev_context['primary_skill_category']}")
        if jev_context.get("primary_tech_stack"):
            parts.append(f"- Primary tech stack: {jev_context['primary_tech_stack']}")
        if jev_context.get("seniority_level"):
            parts.append(f"- Seniority level: {jev_context['seniority_level']} ({jev_context.get('seniority_label', '')})")
        if jev_context.get("salary_bracket"):
            parts.append(f"- Salary bracket: {jev_context['salary_bracket']}")
        if jev_context.get("has_red_flags"):
            parts.append(f"- Has red flags: {'yes' if jev_context['has_red_flags'] > 0.5 else 'no'} ({jev_context['has_red_flags']:.2f})")
        if jev_context.get("remote_ok"):
            parts.append(f"- Remote work: {'yes' if jev_context['remote_ok'] > 0.5 else 'no'} ({jev_context['remote_ok']:.2f})")
        jev_section = "\n".join(parts)

    company_section = (
        f"Company name: {company_name}\n" if company_name else "No company name provided.\n"
    )

    return (
        "ACT AS AN EXPERT TECHNICAL RECRUITER AND JOB MARKET ANALYST. "
        "You are analyzing a job posting. The job has already been classified by a "
        "fast decision model (Jev). Use that structured classification as context "
        "and provide detailed enrichment.\n\n"
        f"Company:\n{company_section}\n"
        "Job Description:\n"
        f"{job_description}\n\n"
        "Jev Classification Results (use these as context, not as final answers):\n"
        f"{jev_section if jev_section else 'No Jev classification available.'}\n\n"
        "Based on the Jev classification AND the job description, provide a detailed "
        "analysis. Focus on:\n\n"
        "1. **required_skills**: All hard skills, tools, platforms, languages, and "
        "frameworks explicitly required. Cross-reference with Jev's tech_stack "
        "classification.\n\n"
        "2. **implied_skills**: Skills NOT explicitly stated but strongly implied by "
        "the role context. Cross-reference with Jev's skill_category.\n\n"
        "3. **red_flags**: Specific red flags (vague requirements, unrealistic "
        "expectations). Use Jev's has_red_flags probability as a starting point.\n\n"
        "4. **salary_estimate**: An estimated salary range based on Jev's salary_bracket, "
        "seniority_level, and the job description.\n\n"
        "Return ONLY a valid JSON object. No markdown, no commentary, no preamble."
    )


def _normalize_skill_list(data: Any) -> list[str]:
    """Normalize skill data to a list of strings.

    Handles LLM returning ``{"Skill Name": True}`` dicts or plain lists.
    """
    if isinstance(data, list):
        return [str(s) for s in data if isinstance(s, str)]
    if isinstance(data, dict):
        return [str(k) for k in data.keys() if k]
    return []
