"""Sentry initialization and error handler.

Sentry is initialized at startup via ``initialize_sentry()``.
When ``sentry_dsn`` is ``None`` (development default), the module
acts as a no-op stub — all calls are no-ops so dev/test runs
are never affected.
"""

from __future__ import annotations

import logging
import sys

import structlog

from backend.config import settings

logger = structlog.get_logger()

_sentry_initialized: bool = False

# Import sentry_sdk lazily — if not installed, all calls are no-ops
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None  # type: ignore[assignment]


def initialize_sentry() -> None:
    """Initialize Sentry SDK if ``sentry_dsn`` is configured."""
    global _sentry_initialized

    if settings.sentry_dsn is None:
        logger.info("sentry_disabled", reason="no DSN configured")
        return

    if sentry_sdk is None:
        logger.warning("sentry_disabled", reason="sentry_sdk not installed")
        return

    try:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.stdlib import StdlibIntegration

        logging_integration = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            integrations=[
                FastApiIntegration(),
                StdlibIntegration(),
                logging_integration,
            ],
        )
        _sentry_initialized = True
        logger.info("sentry_initialized", dsn=settings.sentry_dsn[:20] + "...")
    except Exception as e:
        logger.warning("sentry_init_failed", error=str(e))


def capture_exception(exc: Exception) -> None:
    """Capture an exception to Sentry if initialized."""
    if not _sentry_initialized or sentry_sdk is None:
        return
    try:
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass  # never let Sentry errors break the app


def capture_message(message: str, level: str = "error") -> None:
    """Capture a message to Sentry if initialized."""
    if not _sentry_initialized or sentry_sdk is None:
        return
    try:
        sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass
