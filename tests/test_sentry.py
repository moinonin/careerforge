"""Sentry initialization tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.monitoring.sentry_init import (
    capture_exception,
    capture_message,
    initialize_sentry,
)


def test_initialize_sentry_no_dsn(monkeypatch) -> None:
    """When sentry_dsn is None, initialize_sentry is a no-op."""
    from backend.config import settings

    monkeypatch.setattr(settings, "sentry_dsn", None)
    initialize_sentry()  # should not raise


def test_initialize_sentry_with_dsn(monkeypatch) -> None:
    """When sentry_dsn is set, sentry_sdk.init is called."""
    from backend.config import settings

    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    with patch("backend.monitoring.sentry_init.sentry_sdk") as mock_sentry:
        initialize_sentry()
        mock_sentry.init.assert_called_once()


def test_initialize_sentry_init_fails(monkeypatch) -> None:
    """If sentry_sdk.init raises, the app does not crash."""
    from backend.config import settings

    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    with patch(
        "backend.monitoring.sentry_init.sentry_sdk.init",
        side_effect=Exception("Sentry failed"),
    ):
        initialize_sentry()  # should not raise


def test_initialize_sentry_sdk_none(monkeypatch) -> None:
    """If sentry_sdk is None (not installed), initialize_sentry skips."""
    from backend.config import settings
    import backend.monitoring.sentry_init as sentry_mod

    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    sentry_mod.sentry_sdk = None
    initialize_sentry()  # should not raise


def test_capture_exception_when_disabled() -> None:
    """capture_exception is a no-op when sentry not initialized."""
    import backend.monitoring.sentry_init as sentry_mod
    sentry_mod._sentry_initialized = False
    capture_exception(ValueError("test"))  # should not raise


def test_capture_message_when_disabled() -> None:
    """capture_message is a no-op when sentry not initialized."""
    import backend.monitoring.sentry_init as sentry_mod
    sentry_mod._sentry_initialized = False
    capture_message("test message")  # should not raise


def test_initialize_sentry_sets_flag(monkeypatch) -> None:
    """On successful init, _sentry_initialized is True."""
    from backend.config import settings
    import backend.monitoring.sentry_init as sentry_mod

    monkeypatch.setattr(settings, "sentry_dsn", "https://test@sentry.io/1")
    with patch("backend.monitoring.sentry_init.sentry_sdk") as mock_sentry:
        initialize_sentry()
        assert sentry_mod._sentry_initialized is True
