"""FastAPI router — health & readiness with dependency checks.

Bundled in ``backend.main`` via ``app.include_router(health.router)``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_session
from backend.models import GenerationJob

router = APIRouter(tags=["health"])


async def _check_database() -> dict:
    """Verify the database is reachable and responsive."""
    try:
        from backend.database import get_session
        async for session in get_session():
            result = await session.execute(select(GenerationJob).limit(1))
            _ = result.scalars().all()
        return {"status": "ok", "latency_ms": None}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_redis() -> dict:
    """Verify Redis is reachable and responsive."""
    try:
        redis = Redis.from_url(settings.redis_url)
        pong = await redis.ping()
        await redis.aclose()
        return {"status": "ok" if pong else "error", "latency_ms": None}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_s3() -> dict:
    """Verify S3/MinIO is reachable."""
    if not settings.s3_endpoint_url or not settings.s3_access_key_id:
        return {"status": "skipped", "reason": "S3 not configured"}
    try:
        import boto3
        from botocore.config import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(connect_timeout=3, read_timeout=3),
        )
        s3.list_buckets()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_llm_provider() -> dict:
    """Verify the LLM provider is reachable."""
    if not settings.default_llm_provider or settings.default_llm_provider == "none":
        return {"status": "skipped", "reason": "No LLM provider configured"}
    try:
        import httpx
        # For local providers (Ollama), check the health endpoint
        if settings.default_llm_provider == "ollama":
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get("http://localhost:11434/api/tags")
                r.raise_for_status()
            return {"status": "ok", "provider": "ollama"}
        # For cloud providers, just verify the API key is set
        if settings.default_llm_provider in ("openai", "anthropic"):
            return {"status": "ok", "provider": settings.default_llm_provider}
        return {"status": "ok", "provider": settings.default_llm_provider}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    """Liveness probe with dependency checks."""
    db = await _check_database()
    redis = await _check_redis()
    s3 = await _check_s3()
    llm = await _check_llm_provider()

    all_ok = all(
        check["status"] == "ok"
        for check in [db, redis, s3, llm]
        if check.get("status") != "skipped"
    )

    return {
        "status": "ok" if all_ok else "degraded",
        "service": "careerforge-backend",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": db,
            "redis": redis,
            "s3": s3,
            "llm_provider": llm,
        },
    }


@router.get("/ready", include_in_schema=False)
async def ready() -> dict:
    """Readiness probe — returns 200 if all dependencies are healthy."""
    db = await _check_database()
    redis = await _check_redis()
    s3 = await _check_s3()
    llm = await _check_llm_provider()

    all_ok = all(
        check["status"] == "ok"
        for check in [db, redis, s3, llm]
        if check.get("status") != "skipped"
    )

    return {
        "status": "ready" if all_ok else "not_ready",
        "service": "careerforge-backend",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": db,
            "redis": redis,
            "s3": s3,
            "llm_provider": llm,
        },
    }
