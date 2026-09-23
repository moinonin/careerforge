"""FastAPI router — health & readiness.

Bundled in ``backend.main`` via ``app.include_router(health.router)``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    """Liveness probe for load-balancers and docker-compose healthchecks."""
    return {"status": "ok", "service": "careerforge-backend"}


@router.get("/ready", include_in_schema=False)
async def ready() -> dict:
    """Readiness probe — signals the server is accepting traffic.

    In Sprint 0 this is identical to ``/health``.  Once the DB and other
    downstream services are wired in, this endpoint will verify they are
    reachable before returning 200.
    """
    return {"status": "ready", "service": "careerforge-backend"}
