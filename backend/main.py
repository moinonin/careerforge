from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv  # noqa: E402

load_dotenv(override=True)  # noqa: E402

import structlog  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend.api.routes import health  # noqa: E402
from backend.api.routes.analyzer import router as analyzer_router  # noqa: E402
from backend.api.routes.admin import router as admin_router  # noqa: E402
from backend.api.routes.billing import router as billing_router  # noqa: E402
from backend.api.routes.generate import router as generate_router  # noqa: E402
from backend.api.routes.llm_config import router as llm_config_router  # noqa: E402
from backend.api.routes.organizations import router as organizations_router  # noqa: E402
from backend.auth.router import router as auth_router  # noqa: E402
from backend.auth.router import users_router  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.database import init_db, shutdown_db  # noqa: E402
from backend.middleware.rate_limit import rate_limit_middleware  # noqa: E402
from backend.middleware.security_headers import security_headers_middleware  # noqa: E402
from backend.middleware.request_id import request_id_middleware  # noqa: E402
from backend.middleware.error_handler import error_handler_middleware  # noqa: E402
from backend.profiles.router import router as profiles_router  # noqa: E402

# ── Logging ────────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    """Configure structlog to emit JSON to stdout in production, readable in dev."""
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.set_exc_info,
    ]

    if settings.environment == "production":
        renderer: Any = structlog.processors.JSONRenderer()
        shared_processors.append(structlog.processors.format_exc_info)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
log = structlog.get_logger()

# Initialize Sentry if DSN is configured
from backend.monitoring.sentry_init import initialize_sentry

initialize_sentry()

# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("startup", action="lifespan", environment=settings.environment)
    await init_db()
    log.info("db_connected", action="lifespan")
    yield
    log.info("shutdown", action="lifespan")
    await shutdown_db()

# ── App factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="CareerForge AI API",
        description="ATS-compliant CV and cover letter generation SaaS backend.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — explicit allowlist, never wildcard in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    )

    # Rate limiting (skipped in development)
    app.add_middleware(rate_limit_middleware)

    # Security headers
    app.add_middleware(security_headers_middleware)

    # Request ID middleware (before rate limiting so request_id is available)
    app.add_middleware(request_id_middleware)

    # Error handling
    app.add_middleware(error_handler_middleware)

    # Routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
    app.include_router(profiles_router, prefix="/api/v1/profiles", tags=["profiles"])
    app.include_router(generate_router, prefix="/api/v1/generate", tags=["generation"])
    app.include_router(llm_config_router, prefix="/api/v1/llm-config", tags=["llm-config"])
    app.include_router(organizations_router, tags=["organizations"])
    app.include_router(analyzer_router, prefix="/api/v1/analyzer", tags=["analyzer"])
    app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(admin_router, tags=["admin"])

    @app.get("/health", include_in_schema=False)
    async def health_check() -> dict:
        return {"status": "ok", "service": "careerforge-backend"}

    return app

# ── Module-level app (fastapi dev / uvicorn entry point) ──────────────────

app = create_app()

# ── Module-level helpers for test patching ────────────────────────────────────

def get_settings():
    """Return the Settings class for patching in tests."""
    return settings.__class__


# ── Entry point for `careerforge-server` console script ────────────────────────

def main() -> None:
    """Run the uvicorn server. Called by the `careerforge-server` console script."""
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
