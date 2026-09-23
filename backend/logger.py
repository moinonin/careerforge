from __future__ import annotations

from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


def configure(environment: str = "development") -> None:
    """Configure structlog once at import time.

    Development   → coloured console output.
    Production    → newline-delimited JSON (log aggregation).
    """
    shared: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.set_exc_info,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if environment == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=shared + [renderer],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request(request_id: str) -> None:
    bind_contextvars(request_id=request_id)


def bind_user(user_id: str) -> None:
    bind_contextvars(user_id=user_id)


def clear() -> None:
    clear_contextvars()


# Convenience logger for modules that do ``from backend.logger import log``
log = structlog.get_logger("careerforge")
