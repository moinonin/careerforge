"""Admin dashboard APIs — user list, generation log, and metrics."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import CurrentUserId
from backend.database import get_session
from backend.models import User, GenerationJob, GenerationMetric

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def _require_admin(
    current_user_id: Annotated[str, CurrentUserId],
) -> str:
    """Verify the caller is an admin user."""
    async for session in get_session():
        stmt = select(User).where(User.id == current_user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    if user is None or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user_id


@router.get("/users")
async def admin_user_list(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user_id: str = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List all users with pagination."""
    offset = (page - 1) * page_size

    count_stmt = select(func.count(User.id))
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "organization_id": u.organization_id,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/generation-log")
async def admin_generation_log(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, description="Filter by job status"),
    current_user_id: str = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List generation jobs with optional status filter."""
    offset = (page - 1) * page_size

    stmt = select(GenerationJob)
    count_stmt = select(func.count(GenerationJob.id))

    if status_filter:
        stmt = stmt.where(GenerationJob.status == status_filter)
        count_stmt = count_stmt.where(GenerationJob.status == status_filter)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        stmt.order_by(GenerationJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()

    return {
        "generations": [
            {
                "id": j.id,
                "user_id": j.user_id,
                "job_title": j.job_title,
                "company_name": j.company_name,
                "status": j.status,
                "output_language": j.output_language,
                "tokens_used": j.tokens_used,
                "execution_time_ms": j.execution_time_ms,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/metrics")
async def admin_metrics(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Return generation metrics for admin dashboard."""
    total_stmt = select(func.count()).select_from(GenerationJob)
    total_result = await session.execute(total_stmt)
    total_generations = total_result.scalar_one()

    provider_stmt = select(GenerationJob.provider, func.count()).group_by(GenerationJob.provider)
    provider_result = await session.execute(provider_stmt)
    providers = {row[0]: row[1] for row in provider_result.all()}

    at_stmt = select(func.avg(GenerationJob.at_score))
    at_result = await session.execute(at_stmt)
    avg_ats = at_result.scalar_one()

    metric_stmt = select(func.count()).select_from(GenerationMetric)
    metric_result = await session.execute(metric_stmt)
    total_metrics = metric_result.scalar_one()

    tokens_stmt = select(func.avg(GenerationMetric.tokens_used))
    tokens_result = await session.execute(tokens_stmt)
    avg_tokens = tokens_result.scalar_one()

    return {
        "total_generations": total_generations,
        "total_metrics": total_metrics,
        "generations_by_provider": providers,
        "average_at_score": round(avg_ats, 1) if avg_ats else None,
        "average_tokens_used": round(avg_tokens, 1) if avg_tokens else None,
    }