from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import CurrentUserId
from backend.database import get_session
from backend.profiles import schemas as profiles_schemas
from backend.profiles import service as profiles_service
from backend.profiles.jev_parser import parse_cv_with_jev

router = APIRouter(tags=["profiles"])

# In-memory parse job store (dev). Production uses Celery + Redis.
_parse_jobs: dict[str, dict] = {}


# ── List profiles ─────────────────────────────────────────────────────────────


class ProfileListResponse(BaseModel):
    profiles: list[dict]


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ProfileListResponse:
    profiles = await profiles_service.list_profiles(session, current_user_id)
    return ProfileListResponse(profiles=profiles)


# ── Get single profile ────────────────────────────────────────────────────────


@router.get("/{profile_id}", response_model=dict)
async def get_profile(
    profile_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    try:
        return await profiles_service.get_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Create profile ────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_profile(
    request: profiles_schemas.ProfileCreateRequest,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    return await profiles_service.create_profile(session, current_user_id, request)


# ── Update profile ────────────────────────────────────────────────────────────


@router.put("/{profile_id}", response_model=dict)
async def update_profile(
    profile_id: str,
    request: profiles_schemas.ProfileUpdateRequest,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    try:
        return await profiles_service.update_profile(session, profile_id, current_user_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Patch section ─────────────────────────────────────────────────────────────


@router.patch("/{profile_id}/sections/{section_name}", response_model=dict)
async def patch_section(
    profile_id: str,
    section_name: str,
    request: profiles_schemas.ProfileSectionPatchRequest,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    if not profiles_schemas.is_valid_section(section_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid section name: {section_name}. Valid sections: {sorted(profiles_schemas.VALID_SECTIONS)}",
        )
    try:
        return await profiles_service.patch_section(
            session, profile_id, current_user_id, section_name, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Delete profile ────────────────────────────────────────────────────────────


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    try:
        await profiles_service.delete_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Set default profile ───────────────────────────────────────────────────────


@router.post("/{profile_id}/set-default", response_model=dict)
async def set_default(
    profile_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    try:
        return await profiles_service.set_default_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Skills autocomplete ───────────────────────────────────────────────────────


class SkillSuggestionResponse(BaseModel):
    suggestions: list[dict[str, str]]


@router.get("/skills/suggestions", response_model=SkillSuggestionResponse)
async def skill_suggestions(
    query: str = Query("", min_length=0, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
) -> SkillSuggestionResponse:
    return SkillSuggestionResponse(suggestions=profiles_service.get_skill_suggestions(query, limit))


# ── Profile import (CV upload trigger) ────────────────────────────────────────


class ProfileImportRequest(BaseModel):
    pass  # file is uploaded as multipart form data


@router.post("/import", status_code=status.HTTP_201_CREATED, response_model=dict)
async def import_cv(
    current_user_id: CurrentUserId,
    file: UploadFile = File(...),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Import a CV file and create a profile automatically.

    Accepts a PDF or DOCX file as multipart upload. Parses with pymupdf + Jev,
    then creates the profile in the database.
    """
    import uuid

    from backend.profiles.schemas import MasterProfileData
    from backend.validators.upload_validation import validate_cv_upload

    parse_job_id = str(uuid.uuid4())
    file_bytes = await file.read()
    try:
        validate_cv_upload(file_bytes, file.filename or "", file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        profile = await parse_cv_with_jev(file_bytes, file.filename or "")
        profile_dict = profile.model_dump()
        # Clean up the contact name (pymupdf sometimes appends document metadata)
        contact = profile_dict.get("contact", {})
        if isinstance(contact, dict):
            name = contact.get("full_name", "")
            # Strip document metadata suffixes: split on | then on ·
            for sep in ("|", "·"):
                while sep in name:
                    name = name.split(sep)[0].strip()
            contact["full_name"] = name
            profile_dict["contact"] = contact

        # Auto-create the profile
        from backend.profiles.service import create_profile

        create_req = profiles_schemas.ProfileCreateRequest(
            title=f"Imported CV — {profile_dict['contact'].get('full_name', 'Unknown')}",
            profile_data=MasterProfileData(**profile_dict),
        )
        created = await create_profile(session, current_user_id, create_req)

        _parse_jobs[parse_job_id] = {
            "status": "completed",
            "profile_data": created["profile_data"],
            "profile_id": created["id"],
        }
    except Exception as e:
        _parse_jobs[parse_job_id] = {
            "status": "failed",
            "message": f"Parse failed: {e}",
        }
        return {"parse_job_id": parse_job_id, "status": "failed", "message": str(e)}
    return {"parse_job_id": parse_job_id, "status": "completed", "profile_id": created["id"]}


@router.get("/import/{parse_job_id}", response_model=dict)
async def import_status(
    parse_job_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Poll the status of a CV parse job.

    Returns the parsed profile_data with confidence flags when complete.
    """
    job = _parse_jobs.get(parse_job_id)
    if not job:
        return {
            "parse_job_id": parse_job_id,
            "status": "not_found",
            "message": "Parse job not found. Upload a CV to start parsing.",
        }
    return job


# ── Career Corpus (NotebookLM-style multi-source evidence vault) ──────────────


class CorpusQueryRequest(BaseModel):
    query: str
    top_k: int = 6


@router.get("/{profile_id}/sources", response_model=dict)
async def list_profile_sources(
    profile_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """List all career corpus sources attached to a profile."""
    try:
        profile = await profiles_service.get_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    sources = (profile.get("profile_data") or {}).get("sources") or []
    summaries = [
        {
            "id": s.get("id"),
            "title": s.get("title"),
            "source_type": s.get("source_type"),
            "filename": s.get("filename"),
            "char_count": s.get("char_count", 0),
            "chunk_count": len(s.get("chunks") or []),
            "uploaded_at": s.get("uploaded_at"),
        }
        for s in sources
    ]
    return {"profile_id": profile_id, "sources": summaries}


@router.post("/{profile_id}/sources", status_code=status.HTTP_201_CREATED, response_model=dict)
async def add_profile_source(
    profile_id: str,
    current_user_id: CurrentUserId,
    file: UploadFile | None = File(None),  # noqa: B008
    title: str | None = Form(None),
    text: str | None = Form(None),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Attach a document (PDF/DOCX/PPTX/MD/TXT) or raw text note to a profile's corpus."""
    from backend.profiles.corpus import build_source_entry, extract_source_text

    if file is None and not (text and text.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a file upload or non-empty text.",
        )

    try:
        profile = await profiles_service.get_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if file is not None:
        raw_bytes = await file.read()
        if len(raw_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Source file exceeds 10 MB limit.",
            )
        filename = file.filename or "source.txt"
        try:
            extracted = extract_source_text(raw_bytes, filename)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not extracted.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable text from uploaded file.",
            )
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "file"
        entry = build_source_entry(
            title=title or filename,
            text=extracted,
            source_type=ext,
            filename=filename,
        )
    else:
        entry = build_source_entry(
            title=title or "Text Note",
            text=text or "",
            source_type="text",
            filename=None,
        )

    profile_data = dict(profile.get("profile_data") or {})
    sources = list(profile_data.get("sources") or [])
    sources.append(entry)
    profile_data["sources"] = sources

    update_req = profiles_schemas.ProfileUpdateRequest(
        profile_data=profiles_schemas.MasterProfileData(**profile_data)
    )
    await profiles_service.update_profile(session, profile_id, current_user_id, update_req)
    return {
        "profile_id": profile_id,
        "source": {
            "id": entry["id"],
            "title": entry["title"],
            "source_type": entry["source_type"],
            "filename": entry["filename"],
            "char_count": entry["char_count"],
            "chunk_count": len(entry["chunks"]),
            "uploaded_at": entry["uploaded_at"],
        },
    }


@router.delete("/{profile_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_source(
    profile_id: str,
    source_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """Remove a source document from a profile's career corpus."""
    try:
        profile = await profiles_service.get_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    profile_data = dict(profile.get("profile_data") or {})
    sources = list(profile_data.get("sources") or [])
    remaining = [s for s in sources if s.get("id") != source_id]
    if len(remaining) == len(sources):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    profile_data["sources"] = remaining
    update_req = profiles_schemas.ProfileUpdateRequest(
        profile_data=profiles_schemas.MasterProfileData(**profile_data)
    )
    await profiles_service.update_profile(session, profile_id, current_user_id, update_req)


@router.post("/{profile_id}/sources/query", response_model=dict)
async def query_profile_sources(
    profile_id: str,
    body: CorpusQueryRequest,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Preview top-K grounded evidence excerpts from the profile corpus for a JD/query."""
    from backend.profiles.corpus import retrieve_relevant_evidence

    try:
        profile = await profiles_service.get_profile(session, profile_id, current_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    sources = (profile.get("profile_data") or {}).get("sources") or []
    top_k = max(1, min(int(body.top_k), 12))
    matches = retrieve_relevant_evidence(sources, body.query, top_k=top_k)
    return {"profile_id": profile_id, "query": body.query, "matches": matches}
