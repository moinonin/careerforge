"""Error handler tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def mock_get_session():
    async def _gen():
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result
        yield mock_session
    return _gen


@pytest.fixture(autouse=True)
def mock_db():
    """Patch get_session before app import."""
    with patch("backend.database.get_session", side_effect=mock_get_session()):
        yield


def test_health_still_works():
    """Health endpoint works even with error handler installed."""
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_ready_still_works():
    """Ready endpoint works even with error handler installed."""
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200


def test_404_returns_not_found():
    """Non-existent routes return 404."""
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
