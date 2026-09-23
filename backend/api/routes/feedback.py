"""Feedback router — user ratings for generated CVs."""

from __future__ import annotations

from backend.auth.schemas import CurrentUserId
from backend.config import settings
from backend.database import get_session
from backend.models import Feedback, GenerationJob
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class FeedbackCreate(BaseModel):
    rating: int  # 1 = negative, 2 = positive
    comment: str | None = None
    generation_job_id: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreate,
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Submit feedback for a generated CV.

    Body::
        {"rating": 2, "comment": "Very helpful!", "generation_job_id": "<uuid>"}
    """
    if payload.rating not in (1, 2):
        raise HTTPException(status_code=400, detail="rating must be 1 or 2")

    # Verify generation_job_id belongs to user if provided
    if payload.generation_job_id:
        stmt = select(GenerationJob).where(
            GenerationJob.id == payload.generation_job_id,
            GenerationJob.user_id == current_user_id,
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Generation job not found")

    feedback = Feedback(
        user_id=current_user_id,
        generation_job_id=payload.generation_job_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)

    return {"id": feedback.id, "rating": feedback.rating, "comment": feedback.comment}


@router.get("/my", status_code=status.HTTP_200_OK)
async def get_my_feedback(
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Get current user's feedback history."""
    stmt = select(Feedback).where(Feedback.user_id == current_user_id).order_by(Feedback.created_at.desc())
    result = await session.execute(stmt)
    feedbacks = result.scalars().all()
    return {
        "feedbacks": [
            {"id": f.id, "rating": f.rating, "comment": f.comment, "created_at": f.created_at.isoformat()}
            for f in feedbacks
        ]
    }