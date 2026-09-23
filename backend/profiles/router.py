from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import CurrentUserId
from backend.database import get_session
from backend.profiles import schemas as profiles_schemas
from backend.profiles import service as profiles_service

router = APIRouter(tags=["profiles"])


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
        return await profiles_service.patch_section(session, profile_id, current_user_id, section_name, request)
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


@router.post("/import", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def import_cv(
    current_user_id: CurrentUserId,
    file: UploadFile = File(...),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Trigger CV file import. Accepts a PDF or DOCX file as multipart upload."""
    import uuid
    parse_job_id = str(uuid.uuid4())
    return {"parse_job_id": parse_job_id, "status": "queued"}


@router.get("/import/{parse_job_id}", response_model=dict)
async def import_status(
    parse_job_id: str,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Poll the status of a CV parse job.

    In production, this would check the Celery task state and return
    the parsed profile_data with confidence flags when complete.
    """
    # Placeholder: return not_found until the task is implemented
    return {
        "parse_job_id": parse_job_id,
        "status": "not_found",
        "message": "Parse job not found. The CV parser Celery task is not yet implemented.",
    }
