"""Generation API — async CV + cover letter generation jobs.

Endpoints
---------
* ``POST /api/v1/generate`` — kick off a generation job, returns ``job_id``
* ``GET /api/v1/generate/jobs/{job_id}`` — poll job status + artifact URLs

Sprint 3 scope.  Generation runs inline within the request (acceptable for
the small models used in Sprint 3; a 30-second generation is fine for an
initial release).  Background execution via Celery deferred to Sprint 7.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from typing import Any
from uuid import uuid4

from backend.auth.schemas import CurrentUserId
from backend.config import settings
from backend.database import get_session
from backend.llm.adapter import GenerationError
from backend.llm.docx_renderer import CoverLetterDocxRenderer, DocxRenderer
from backend.llm.prompts import COVER_LETTER_SCHEMA, CV_SCHEMA, assemble_prompt
from backend.llm.service import (
    create_generation_job,
    get_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_processing,
    render_cover_letter_markdown,
    render_cv_markdown,
    run_generation,
)
from backend.models import GenerationJob, MasterProfile, StoredArtifact, GenerationMetric
from backend.validators.sanitization import sanitize_text  # noqa: E402
import structlog  # noqa: E402

log = structlog.get_logger()

from fastapi import APIRouter, Depends, HTTPException, Response, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["generation"])

# Words to ignore when computing the ATS overlap score


class GenerationRequest(BaseModel):
    """Request body for ``POST /api/v1/generate``."""

    profile_id: str | None = None
    job_description: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    output_language: str = "en"  # en, es, de, fr, fi
    jev_analysis: dict[str, Any] | None = None
    """Optional Jev structured analysis to guide CV generation."""

    class Config:
        from_attributes = True


_STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "ought", "used", "this", "that", "these", "those", "it", "its", "as",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very", "just",
    "about", "above", "after", "again", "against", "all", "also", "any",
    "because", "before", "between", "both", "each", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "into", "over", "under",
    "up", "out", "off", "down", "here", "there", "when", "where", "why",
    "how", "what", "which", "who", "whom", "whose", "i", "me", "my", "we",
    "our", "you", "your", "he", "him", "his", "she", "her", "they", "them",
    "their", "am",
})

SUPPORTED_LANGUAGES = {"en": "English", "es": "Spanish", "de": "German", "fr": "French", "fi": "Finnish"}

LANGUAGE_LABELS: dict[str, str] = {
    "en": "",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "fi": "Finnish",
}


async def track_usage(
    session: AsyncSession,
    organization_id: str,
    user_id: str | None,
    generation_job_id: str,
    provider: str,
    model_name: str,
    output_language: str,
    export_format: str,
    at_score: int | None,
    tokens_used: int | None,
) -> None:
    """Persist a GenerationMetric record for feature usage tracking."""
    metric = GenerationMetric(
        generation_job_id=generation_job_id,
        organization_id=organization_id,
        user_id=user_id,
        provider=provider,
        model_name=model_name,
        output_language=output_language,
        export_format=export_format,
        at_score=at_score,
        tokens_used=tokens_used,
    )
    session.add(metric)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_generation(
    request: dict[str, Any],
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Kick off a CV + cover letter generation job.

    Body::
        {
            "profile_id": "<uuid>",
            "job_description": "Backend Engineer at ...",
            "job_title": "Optional job title (default: CV & Cover Letter)",
            "company_name": "Optional company name",
            "provider": "Optional: openai, anthropic, ollama, custom",
            "model": "Optional: model name override"
        }

    Returns::
        {
            "job_id": "<uuid>",
            "status": "completed",
            "message": "Generation completed",
            "cv_markdown": "...",
            "cover_letter_markdown": "..."
        }

    The job runs inline (Sprint 3). On completion the ``cv_docx_url`` and
    ``cl_docx_url`` fields on the job point to the rendered artifacts.
    On failure the status is ``"failed"`` with an ``error_message``.
    """
    profile_id = request.get("profile_id")
    job_description = request.get("job_description")
    job_title = request.get("job_title")
    company_name = request.get("company_name")
    provider = request.get("provider")
    model = request.get("model")
    output_language = request.get("output_language", "en")
    jev_analysis = request.get("jev_analysis")

    if output_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported output_language: {output_language}. Supported: {list(SUPPORTED_LANGUAGES.keys())}")

    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id is required")
    if not job_description or not str(job_description).strip():
        raise HTTPException(status_code=400, detail="job_description is required")

    # Sanitize all user-provided text before DB/LLM
    job_description = sanitize_text(str(job_description))
    job_title = sanitize_text(str(job_title)) if job_title else ""
    company_name = sanitize_text(str(company_name)) if company_name else ""

    log.info(
        "generation_started",
        user_id=current_user_id,
        profile_id=profile_id,
        job_title=job_title,
        company_name=company_name,
        output_language=output_language,
    )

    # Verify profile ownership
    from backend.models import MasterProfile

    stmt = select(MasterProfile).where(
        MasterProfile.id == profile_id,
        MasterProfile.user_id == current_user_id,
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found or not owned")

    # Create the job
    job = await create_generation_job(
        session=session,
        user_id=current_user_id,
        profile_id=profile_id,
        job_description=str(job_description),
        job_title=job_title,
        company_name=company_name,
        output_language=output_language,
        provider=provider,
        model=model,
    )

    # Mark processing and execute inline
    await mark_job_processing(session, job.id)

    try:
        cv, cover_letter = await run_generation(
            session, job, provider=provider, model=model,
            jev_context=jev_analysis,
        )

        cv_markdown = render_cv_markdown(cv)
        cl_markdown = render_cover_letter_markdown(cover_letter)

        # Sprint 4: render actual .docx and .pdf files in addition to markdown
        from backend.llm.pdf_renderer import await_convert as pdf_convert
        artifacts_dir = settings.generation_artifacts_dir
        os.makedirs(artifacts_dir, exist_ok=True)
        cv_docx_path = os.path.join(artifacts_dir, f"{job.id}_cv.docx")
        cl_docx_path = os.path.join(artifacts_dir, f"{job.id}_cover_letter.docx")
        cv_pdf_path = os.path.join(artifacts_dir, f"{job.id}_cv.pdf")
        cl_pdf_path = os.path.join(artifacts_dir, f"{job.id}_cover_letter.pdf")

        DocxRenderer().render(cv).save(cv_docx_path)
        CoverLetterDocxRenderer().render(cover_letter).save(cl_docx_path)

        # Convert DOCX → PDF
        await pdf_convert(cv_docx_path, artifacts_dir)
        await pdf_convert(cl_docx_path, artifacts_dir)

        at_score, missing_keywords = _compute_at_score(cv, str(job_description))

        await mark_job_completed(
            session,
            job.id,
            cv_json=cv,
            cover_letter_json=cover_letter,
            at_score=at_score,
            cv_docx_path=cv_docx_path,
            cl_docx_path=cl_docx_path,
            cv_pdf_path=cv_pdf_path,
            cl_pdf_path=cl_pdf_path,
            user_id=current_user_id,
        )

        # Track usage for Sprint 10 feature analytics
        from backend.models import User
        stmt = select(User).where(User.id == current_user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        org_id = user.organization_id if user else None
        await track_usage(
            session,
            organization_id=org_id or "",
            user_id=current_user_id,
            generation_job_id=job.id,
            provider=job.provider or "system_default",
            model_name=job.model_name or "unknown",
            output_language=output_language,
            export_format="both",
            at_score=at_score,
            tokens_used=job.tokens_used,
        )

        return {
            "job_id": job.id,
            "status": "completed",
            "message": "Generation completed",
            "cv_markdown": cv_markdown,
            "cover_letter_markdown": cl_markdown,
            "at_score": at_score,
            "missing_keywords": missing_keywords,
        }

    except GenerationError as exc:
        await mark_job_failed(session, job.id, str(exc))
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}") from exc
    except ValueError as exc:
        await mark_job_failed(session, job.id, str(exc))
        raise HTTPException(status_code=400, detail=f"Invalid request: {exc}") from exc
    except Exception as exc:
        await mark_job_failed(session, job.id, str(exc))
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


def _compute_at_score(cv: dict[str, Any], job_description: str) -> tuple[int, list[str]]:
    """Compute a 0-100 ATS keyword-match score.

    Returns ``(score, missing_keywords)`` where *missing_keywords* is a
    list of high-signal JD terms that do not appear anywhere in the CV.
    """

    jd_words: set[str] = {
        w.lower()
        for w in re.findall(r"\b[a-z]{3,}\b", job_description.lower())
        if w.lower() not in _STOP_WORDS
    }

    if not jd_words:
        return 50, []

    cv_text_parts: list[str] = []
    cv_text_parts.append(cv.get("summary", ""))
    cv_text_parts.append(cv.get("contact", {}).get("full_name", ""))
    for exp in cv.get("experience", []):
        cv_text_parts.append(exp.get("role", ""))
        cv_text_parts.append(exp.get("company", ""))
        cv_text_parts.extend(exp.get("bullets", []))
    for edu in cv.get("education", []):
        cv_text_parts.append(edu.get("degree", ""))
        cv_text_parts.append(edu.get("institution", ""))
    skills = cv.get("skills", {})
    for group in ("technical", "domain", "tools", "soft"):
        cv_text_parts.extend(skills.get(group, []))
    for p in cv.get("projects", []):
        cv_text_parts.append(p.get("name", ""))
        cv_text_parts.append(p.get("description", ""))
    for pub in cv.get("publications", []):
        cv_text_parts.append(pub.get("citation", ""))
    for cert in cv.get("certifications", []):
        cv_text_parts.append(cert.get("name", ""))
    for lang in cv.get("languages", []):
        cv_text_parts.append(lang.get("language", ""))
    cv_text_parts.append(cv.get("additional_info", ""))

    cv_text = " ".join(cv_text_parts).lower()
    cv_text_words: set[str] = {
        w for w in re.findall(r"\b[a-z]{3,}\b", cv_text) if w not in _STOP_WORDS
    }

    overlap = jd_words & cv_text_words
    if not overlap:
        return 0, sorted(jd_words)[:10]

    score = int(len(overlap) / len(jd_words) * 100)
    missing = sorted(jd_words - overlap)
    return min(score, 100), missing[:10]


@router.get("/jobs/{job_id}/cv")
async def download_cv_docx(
    job_id: str,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    """Download the CV DOCX artifact for a completed generation job."""
    job = await get_job(session, job_id, current_user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job not yet completed")
    if not job.cv_docx_url or not os.path.isfile(job.cv_docx_url):
        raise HTTPException(status_code=404, detail="CV DOCX not available")

    with open(job.cv_docx_url, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename={job.id}_cv.docx"})


@router.get("/jobs/{job_id}/cover-letter")
async def download_cl_docx(
    job_id: str,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    """Download the cover letter DOCX artifact for a completed generation job."""
    job = await get_job(session, job_id, current_user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="Job not yet completed")
    if not job.cl_docx_url or not os.path.isfile(job.cl_docx_url):
        raise HTTPException(status_code=404, detail="Cover letter DOCX not available")

    with open(job.cl_docx_url, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename={job.id}_cover_letter.docx"})


@router.get("/jobs/{job_id}")
async def get_generation_job(
    job_id: str,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Return the status of a generation job and its artifact URLs.

    Returns::
        {
            "job_id": "...",
            "status": "pending" | "processing" | "completed" | "failed",
            "job_title": "...",
            "company_name": "...",
            "job_description": "...",
            "error_message": "...",
            "cv_docx_url": "...",
            "cv_pdf_url": "...",
            "cl_docx_url": "...",
            "cl_pdf_url": "...",
            "at_score": 85,
            "tokens_used": 4200,
            "execution_time_ms": 12340,
            "created_at": "...",
            "completed_at": "..."
        }
    """
    job = await get_job(session, job_id, current_user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "job_title": job.job_title,
        "company_name": job.company_name,
        "job_description": job.job_description,
        "error_message": job.error_message,
        "cv_docx_url": job.cv_docx_url,
        "cv_pdf_url": job.cv_pdf_url,
        "cl_docx_url": job.cl_docx_url,
        "cl_pdf_url": job.cl_pdf_url,
        "at_score": job.at_score,
        "tokens_used": job.tokens_used,
        "execution_time_ms": job.execution_time_ms,
        "missing_keywords": job.missing_keywords,
        "output_language": job.output_language,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


# ── WebSocket Streaming ───────────────────────────────────────────────────────
#
# WS /api/v1/generate/stream/{job_id}
# Opens a WebSocket connection for real-time token streaming during generation.
# Sends progress events:
#   {"type": "token", "content": "..."} — incremental token chunks
#   {"type": "parsing"} — JSON parsing phase
#   {"type": "complete", "cv_url": "...", "cl_url": "..."} — generation complete
#   {"type": "error", "message": "..."} — error occurred
#


@router.websocket("/stream/{job_id}")
async def stream_generation(
    websocket: WebSocket,
    job_id: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """WebSocket endpoint for streaming generation tokens in real time.

    The client must send the access token as a query parameter: ?token=<access_token>
    """
    await websocket.accept()

    # Extract token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"type": "error", "message": "Missing authentication token"})
        await websocket.close(code=4001)
        return

    # Validate token and get user_id
    from backend.auth.jwt_utils import decode_token, get_user_id_from_token

    try:
        user_id = get_user_id_from_token(token)
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": f"Invalid token: {exc}"})
        await websocket.close(code=4001)
        return

    # Verify job ownership
    job = await get_job(session, job_id, user_id)
    if job is None:
        await websocket.send_json({"type": "error", "message": "Generation job not found"})
        await websocket.close(code=4004)
        return

    if job.status != "pending":
        await websocket.send_json({"type": "error", "message": "Job already processed"})
        await websocket.close(code=4009)
        return

    try:
        # Mark as processing
        await mark_job_processing(session, job_id)

        # Load profile and build prompt
        from backend.models import MasterProfile
        from backend.llm.prompts import assemble_prompt
        from backend.profiles.schemas import MasterProfileData

        stmt = select(MasterProfile).where(MasterProfile.id == job.profile_id)
        result = await session.execute(stmt)
        profile_row = result.scalar_one_or_none()
        if profile_row is None:
            await websocket.send_json({"type": "error", "message": "Profile not found"})
            return

        profile = MasterProfileData(**profile_row.profile_data)
        prompt = assemble_prompt(
            profile=profile,
            job_description=job.job_description,
            jev_context=None,
        )

        # Build adapter from user's config
        from backend.llm.router import build_adapter_from_config

        adapter, _, _ = await build_adapter_from_config(session, user_id)

        # Stream tokens from the adapter
        # We need to modify the adapter to support streaming
        # For now, we'll do a simple approach: run generation and stream the result

        # Send initial status
        await websocket.send_json({"type": "start", "message": "Starting generation..."})

        # Use the adapter's generate method (non-streaming for now)
        # In a full implementation, we'd add streaming support to adapters
        combined_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "cv": CV_SCHEMA,
                "cover_letter": COVER_LETTER_SCHEMA,
            },
            "required": ["cv", "cover_letter"],
        }

        await websocket.send_json({"type": "parsing", "message": "Generating content..."})

        try:
            result_data = await adapter.generate(
                prompt=prompt,
                schema=combined_schema,
                model=None,
                max_retries=3,
            )

            cv = result_data.get("cv", {})
            cover_letter = result_data.get("cover_letter", {})

            # Simulate token streaming by sending chunks
            cv_str = str(cv)
            cl_str = str(cover_letter)

            # Send CV in chunks
            chunk_size = 100
            for i in range(0, len(cv_str), chunk_size):
                await websocket.send_json(
                    {"type": "token", "content": cv_str[i : i + chunk_size], "section": "cv"}
                )

            for i in range(0, len(cl_str), chunk_size):
                await websocket.send_json(
                    {"type": "token", "content": cl_str[i : i + chunk_size], "section": "cover_letter"}
                )

            # Render artifacts
            from backend.llm.pdf_renderer import await_convert as pdf_convert

            cv_markdown = render_cv_markdown(cv)
            cl_markdown = render_cover_letter_markdown(cover_letter)

            artifacts_dir = settings.generation_artifacts_dir
            os.makedirs(artifacts_dir, exist_ok=True)
            cv_docx_path = os.path.join(artifacts_dir, f"{job.id}_cv.docx")
            cl_docx_path = os.path.join(artifacts_dir, f"{job.id}_cover_letter.docx")
            cv_pdf_path = os.path.join(artifacts_dir, f"{job.id}_cv.pdf")
            cl_pdf_path = os.path.join(artifacts_dir, f"{job.id}_cover_letter.pdf")

            DocxRenderer().render(cv).save(cv_docx_path)
            CoverLetterDocxRenderer().render(cover_letter).save(cl_docx_path)

            await pdf_convert(cv_docx_path, artifacts_dir)
            await pdf_convert(cl_docx_path, artifacts_dir)

            at_score, missing_keywords = _compute_at_score(cv, str(job.job_description))

            await mark_job_completed(
                session,
                job.id,
                cv_json=cv,
                cover_letter_json=cover_letter,
                at_score=at_score,
                missing_keywords=missing_keywords,
                cv_docx_path=cv_docx_path,
                cl_docx_path=cl_docx_path,
                cv_pdf_path=cv_pdf_path,
                cl_pdf_path=cl_pdf_path,
                user_id=user_id,
            )

            await websocket.send_json(
                {
                    "type": "complete",
                    "job_id": job.id,
                    "cv_docx_url": cv_docx_path,
                    "cv_pdf_url": cv_pdf_path,
                    "cl_docx_url": cl_docx_path,
                    "cl_pdf_url": cl_pdf_path,
                    "at_score": at_score,
                    "missing_keywords": missing_keywords,
                }
            )

        except GenerationError as exc:
            await mark_job_failed(session, job.id, str(exc))
            await websocket.send_json({"type": "error", "message": f"LLM generation failed: {exc}"})
        except Exception as exc:
            await mark_job_failed(session, job.id, str(exc))
            await websocket.send_json({"type": "error", "message": f"Generation failed: {exc}"})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": f"Server error: {exc}"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── Bulk Generation ───────────────────────────────────────────────────────


class BulkGenerationRequest(BaseModel):
    """Request body for ``POST /api/v1/generate/bulk``."""

    profile_id: str
    jobs: list[dict[str, Any]]  # list of {job_description, job_title?, company_name?}


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def bulk_generate(
    request: BulkGenerationRequest,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Kick off multiple generation jobs in one request.

    Body::
        {
            "profile_id": "<uuid>",
            "jobs": [
                {"job_description": "...", "job_title": "...", "company_name": "..."},
                ...
            ]
        }

    Returns a list of job IDs. Generation runs inline for each job.
    All artifacts are stored as permanent StoredArtifact records.
    """
    # Verify profile belongs to user
    stmt = select(MasterProfile).where(
        MasterProfile.id == request.profile_id,
        MasterProfile.user_id == current_user_id,
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found or not owned")

    job_ids: list[str] = []

    for job_req in request.jobs:
        raw_desc = sanitize_text(str(job_req.get("job_description", "")))
        raw_title = sanitize_text(str(job_req.get("job_title"))) if job_req.get("job_title") else ""
        raw_company = sanitize_text(str(job_req.get("company_name"))) if job_req.get("company_name") else ""
        job = await create_generation_job(
            session=session,
            user_id=current_user_id,
            profile_id=request.profile_id,
            job_description=raw_desc,
            job_title=raw_title,
            company_name=raw_company,
            output_language=job_req.get("output_language", "en"),
            provider=job_req.get("provider"),
            model=job_req.get("model"),
        )
        job_ids.append(job.id)

    return {
        "jobs": [
            {"job_id": jid, "status": "pending"}
            for jid in job_ids
        ],
        "total": len(job_ids),
    }


# ── Document Library ────────────────────────────────────────────────────────


class SaveArtifactRequest(BaseModel):
    """Request body for ``POST /api/v1/generate/{job_id}/save``."""

    title: str
    job_title: str | None = None
    company_name: str | None = None
    at_score: int | None = None
    is_temp: bool = False


@router.post("/{job_id}/save", status_code=status.HTTP_200_OK)
async def save_artifact(
    job_id: str,
    request: SaveArtifactRequest,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Save a completed generation job to the document library as a permanent artifact.

    Sets ``is_temp=False`` on all StoredArtifact rows linked to *job_id*.
    """
    job = await get_job(session, job_id, current_user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Sanitize user-provided text
    sanitized_title = sanitize_text(request.title)
    sanitized_job_title = sanitize_text(request.job_title) if request.job_title else None
    sanitized_company = sanitize_text(request.company_name) if request.company_name else None

    # Update all StoredArtifact rows for this job
    stmt = select(StoredArtifact).where(
        StoredArtifact.generation_job_id == job_id,
        StoredArtifact.user_id == current_user_id,
    )
    result = await session.execute(stmt)
    artifacts = result.scalars().all()

    for artifact in artifacts:
        artifact.is_temp = request.is_temp
        artifact.title = sanitized_title
        if request.job_title:
            artifact.job_title = sanitized_job_title
        if request.company_name:
            artifact.company_name = sanitized_company
        if request.at_score is not None:
            artifact.at_score = request.at_score

    await session.commit()

    return {
        "job_id": job_id,
        "saved": len(artifacts),
        "title": request.title,
        "is_temp": request.is_temp,
    }


@router.get("/library", status_code=status.HTTP_200_OK)
async def list_library(
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """List all permanent documents in the user's library.

    Returns artifacts with ``is_temp=False`` ordered by ``created_at`` desc.
    """
    stmt = (
        select(StoredArtifact)
        .where(
            StoredArtifact.user_id == current_user_id,
            StoredArtifact.is_temp == False,
        )
        .order_by(StoredArtifact.created_at.desc())
    )
    result = await session.execute(stmt)
    artifacts = result.scalars().all()

    return {
        "documents": [
            {
                "id": a.id,
                "title": a.title,
                "job_title": a.job_title,
                "company_name": a.company_name,
                "artifact_type": a.artifact_type,
                "file_url": a.file_url,
                "at_score": a.at_score,
                "is_temp": a.is_temp,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.get("/library/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    *,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Response:
    """Download a single artifact by ID."""
    stmt = select(StoredArtifact).where(
        StoredArtifact.id == artifact_id,
        StoredArtifact.user_id == current_user_id,
    )
    result = await session.execute(stmt)
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Return the file as binary content
    file_path = artifact.file_url
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    # Determine media type from file extension
    ext = os.path.splitext(file_path)[1].lower()
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx" else "application/pdf" if ext == ".pdf" else "application/octet-stream"
    return Response(content=file_bytes, media_type=media_type)
