"""Generation Service — job lifecycle, LLM orchestration, artifact assembly.

Sprint 3 core: wires the prompt assembler, LLM adapter, and generation job
tracking together.  Adapter selection is env-driven (no llm_configs table yet —
that arrives in Sprint 6).

Model contract (from models.py):
  GenerationJob: id, user_id, profile_id, job_title, company_name,
                 job_description, status (pending|processing|completed|failed),
                 cv_docx_url, cv_pdf_url, cl_docx_url, cl_pdf_url,
                 at_score, tokens_used, execution_time_ms, error_message,
                 created_at, completed_at
  StoredArtifact: (Sprint 4 — not used in Sprint 3)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from backend.llm.prompts import COVER_LETTER_SCHEMA, CV_SCHEMA, assemble_prompt
from backend.llm.router import build_adapter
from backend.models import GenerationJob, MasterProfile, StoredArtifact
from backend.profiles.service import _load_profile_data
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Status values match the model: pending | processing | completed | failed
PENDING = "pending"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ── Job creation ───────────────────────────────────────────────────────────────


async def create_generation_job(
    session: AsyncSession,
    user_id: str,
    profile_id: str,
    job_description: str,
    *,
    job_title: str | None = None,
    company_name: str | None = None,
    output_language: str = "en",
    provider: str | None = None,
    model: str | None = None,
) -> GenerationJob:
    """Insert a new ``GenerationJob`` in ``pending`` state and return it."""
    job = GenerationJob(
        user_id=user_id,
        profile_id=profile_id,
        job_title=job_title or "CV & Cover Letter",
        company_name=company_name,
        job_description=job_description,
        output_language=output_language,
        status=PENDING,
        provider=provider,
        model_name=model,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


# ── LLM generation (the core async operation) ────────────────────────────────


async def run_generation(
    session: AsyncSession,
    job: GenerationJob,
    *,
    provider: str | None = None,
    model: str | None = None,
    jev_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the LLM generation for *job*.

    Returns ``(cv_dict, cover_letter_dict)`` on success.

    Raises:
        GenerationError: all LLM retry attempts exhausted.
        ValueError: profile not found or profile_data is not valid.
    """
    # 1. Load the master profile
    stmt = select(MasterProfile).where(MasterProfile.id == job.profile_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"Profile {job.profile_id} not found")

    profile_data_raw: Any = row.profile_data
    profile_data: dict[str, Any] = _load_profile_data(profile_data_raw)
    if not isinstance(profile_data, dict) or not profile_data:
        raise ValueError(f"Profile {job.profile_id} has no profile_data")

    # 2. Build the prompt
    from backend.profiles.schemas import MasterProfileData

    profile = MasterProfileData(**profile_data)
    prompt = assemble_prompt(
        profile=profile,
        job_description=job.job_description,
        output_language=job.output_language,
        jev_context=jev_context,
    )

    # 3. Pick and run the adapter (DB-driven for Sprint 6; env-driven fallback)
    from backend.llm.router import build_adapter_from_config

    adapter, effective_provider, effective_model = await build_adapter_from_config(
        session,
        job.user_id,
        provider_slug=provider,
        model=model,
    )

    # 4. Generate — the adapter handles JSON parse + full validation (top-level
    #    AND sub-objects) + retries. After it returns, the data is fully valid.
    combined_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "cv": CV_SCHEMA,
            "cover_letter": COVER_LETTER_SCHEMA,
        },
        "required": ["cv", "cover_letter"],
    }

    result_data = await adapter.generate(
        prompt=prompt,
        schema=combined_schema,
        model=effective_model or None,
        max_retries=3,
    )

    cv = result_data.get("cv", {})
    cover_letter = result_data.get("cover_letter", {})

    return cv, cover_letter


# ── Artifact text rendering ────────────────────────────────────────────────────


def render_cv_markdown(cv: dict[str, Any]) -> str:
    """Render a CV dict (from LLM output) into a markdown string for storage."""

    lines: list[str] = []
    lines.append("# CV")
    lines.append("")

    contact = cv.get("contact", {})
    if contact.get("full_name"):
        lines.append(f"## {contact['full_name']}")
        lines.append("")
    if contact.get("location"):
        lines.append(f"{contact['location']}")
        lines.append("")

    summary = cv.get("summary", "")
    if summary:
        lines.append(summary)
        lines.append("")

    skills = cv.get("skills", {})
    if skills:
        lines.append("## Skills")
        lines.append("")
        for group, label in [
            ("technical", "Technical Skills"),
            ("domain", "Domain Knowledge"),
            ("tools", "Tools"),
            ("soft", "Soft Skills"),
        ]:
            items = skills.get(group, [])
            if items:
                lines.append(f"**{label}:** {', '.join(items)}")
        lines.append("")

    for exp in cv.get("experience", []):
        loc = f", {exp['location']}" if exp.get("location") else ""
        dates = ""
        if exp.get("start_date"):
            end = exp.get("end_date", "")
            if end and end.lower() not in ("", "present", "now"):
                dates = f" ({exp['start_date']} – {end})"
            else:
                dates = f" ({exp['start_date']} – Present)"
        lines.append(f"### {exp['role']} at {exp['company']}{loc}{dates}")
        if exp.get("relevance_note"):
            lines.append(f"*Relevance to target role: {exp['relevance_note']}*")
        for b in exp.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")

    for edu in cv.get("education", []):
        loc = f", {edu['location']}" if edu.get("location") else ""
        dates = ""
        if edu.get("start_date"):
            end = edu.get("end_date", "")
            if end:
                dates = f" ({edu['start_date']} – {end})"
            else:
                dates = f" ({edu['start_date']} – Present)"
        lines.append(f"- {edu['degree']} at {edu['institution']}{loc}{dates}")
        if edu.get("thesis"):
            lines.append(f"  Thesis: {edu['thesis']}")
        lines.append("")

    for p in cv.get("projects", []):
        lines.append(f"### {p['name']}")
        if p.get("description"):
            lines.append(p["description"])
        if p.get("tech_stack"):
            lines.append(f"**Tech:** {', '.join(p['tech_stack'])}")
        if p.get("link"):
            lines.append(f"[Link]({p['link']})")
        lines.append("")

    for pub in cv.get("publications", []):
        year = f" ({pub['year']})" if pub.get("year") else ""
        lines.append(f"- {pub['citation']}{year}")
        if pub.get("doi"):
            lines.append(f"  DOI: {pub['doi']}")
        if pub.get("link"):
            lines.append(f"  [Link]({pub['link']})")
    if cv.get("publications"):
        lines.append("")

    for cert in cv.get("certifications", []):
        year = f" ({cert['year']})" if cert.get("year") else ""
        issuer = f" — {cert['issuer']}" if cert.get("issuer") else ""
        lines.append(f"- {cert['name']}{issuer}{year}")
    if cv.get("certifications"):
        lines.append("")

    for lang in cv.get("languages", []):
        lines.append(f"- {lang['language']}: {lang['proficiency']}")
    if cv.get("languages"):
        lines.append("")

    addl = cv.get("additional_info", "")
    if addl:
        lines.append("## Additional Information")
        lines.append("")
        lines.append(addl)
        lines.append("")

    return "\n".join(lines)


def render_cover_letter_markdown(cl: dict[str, Any]) -> str:
    """Render a cover letter dict (from LLM output) into a markdown string."""

    lines: list[str] = []
    if cl.get("header"):
        lines.append(cl["header"])
        lines.append("")
    if cl.get("salutation"):
        lines.append(cl["salutation"])
        lines.append("")
    if cl.get("opening"):
        lines.append(cl["opening"])
        lines.append("")
    for para in cl.get("body_paragraphs", []):
        lines.append(para)
        lines.append("")
    if cl.get("call_to_action"):
        lines.append(cl["call_to_action"])
        lines.append("")
    if cl.get("closing"):
        lines.append(cl["closing"])
        lines.append("")
    if cl.get("signature"):
        lines.append(cl["signature"])
        lines.append("")
    return "\n".join(lines)


# ── Job status updates ────────────────────────────────────────────────────────


async def mark_job_processing(session: AsyncSession, job_id: str) -> GenerationJob | None:
    """Set a job's status to ``processing``.  Returns the updated job or None."""
    return await _set_status(session, job_id, PROCESSING)


async def mark_job_completed(
    session: AsyncSession,
    job_id: str,
    cv_json: dict[str, Any],
    cover_letter_json: dict[str, Any],
    *,
    at_score: int | None = None,
    missing_keywords: list[str] | None = None,
    tokens_used: int | None = None,
    execution_time_ms: int | None = None,
    cv_docx_path: str | None = None,
    cl_docx_path: str | None = None,
    cv_pdf_path: str | None = None,
    cl_pdf_path: str | None = None,
    user_id: str | None = None,
) -> GenerationJob | None:
    """Set a job to ``completed``, persist result JSON, fill artifact URLs.

    Also creates StoredArtifact rows for all provided artifact paths.
    """
    job = await _set_status(session, job_id, COMPLETED)
    if job is None:
        return None

    if cv_docx_path is not None:
        job.cv_docx_url = cv_docx_path
    if cl_docx_path is not None:
        job.cl_docx_url = cl_docx_path
    if cv_pdf_path is not None:
        job.cv_pdf_url = cv_pdf_path
    if cl_pdf_path is not None:
        job.cl_pdf_url = cl_pdf_path

    if at_score is not None:
        job.at_score = at_score
    if missing_keywords is not None:
        job.missing_keywords = missing_keywords
    if tokens_used is not None:
        job.tokens_used = tokens_used
    if execution_time_ms is not None:
        job.execution_time_ms = execution_time_ms
    job.completed_at = _utc_now()

    # Create StoredArtifact rows for all generated artifacts
    if user_id:
        artifact_rows = []
        for artifact_type, file_path in [
            ("cv_docx", cv_docx_path),
            ("cv_pdf", cv_pdf_path),
            ("cl_docx", cl_docx_path),
            ("cl_pdf", cl_pdf_path),
        ]:
            if file_path:
                size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                artifact_rows.append(
                    StoredArtifact(
                        user_id=user_id,
                        generation_job_id=job.id,
                        artifact_type=artifact_type,
                        file_key=file_path,
                        file_size_bytes=size,
                        file_url=file_path,
                        title=artifact_type.replace("_", " ").title(),
                        job_title=job.job_title,
                        company_name=job.company_name,
                        at_score=at_score,
                    )
                )
        if artifact_rows:
            session.add_all(artifact_rows)

    await session.commit()
    await session.refresh(job)
    return job


async def mark_job_failed(session: AsyncSession, job_id: str, error_message: str) -> GenerationJob | None:
    """Set a job to ``failed`` with an error message.  Returns the updated job or None."""
    return await _set_status(session, job_id, FAILED, error_message=error_message)


async def _set_status(
    session: AsyncSession,
    job_id: str,
    status: str,
    *,
    error_message: str | None = None,
) -> GenerationJob | None:
    """Internal helper: set status (and optional error_message) on a job."""
    stmt = select(GenerationJob).where(GenerationJob.id == job_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None
    job.status = status
    if error_message is not None:
        job.error_message = error_message
    await session.commit()
    await session.refresh(job)
    return job


# ── Job read ───────────────────────────────────────────────────────────────────


async def get_job(session: AsyncSession, job_id: str, user_id: str) -> GenerationJob | None:
    """Return a generation job belonging to *user_id*, or None."""
    stmt = (
        select(GenerationJob)
        .where(GenerationJob.id == job_id, GenerationJob.user_id == user_id)
        .options(selectinload(GenerationJob.profile))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
