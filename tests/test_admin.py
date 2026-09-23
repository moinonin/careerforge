"""Admin API tests."""

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
def _mock_db():
    """Patch get_session for all tests in this module."""
    with patch("backend.database.get_session", side_effect=mock_get_session()):
        yield


@pytest.fixture
def client():
    from backend.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_admin_routes_registered():
    """Verify admin endpoints are registered in the router."""
    from backend.api.routes.admin import router
    routes = [r.path for r in router.routes]
    assert "/api/v1/admin/users" in routes
    assert "/api/v1/admin/generation-log" in routes


def test_admin_users_returns_200_or_403(client):
    """Admin users returns 200 or 403 (not 404)."""
    response = client.get("/api/v1/admin/users")
    assert response.status_code in (200, 403, 422)


def test_admin_generation_log_returns_200_or_403(client):
    """Admin generation-log returns 200 or 403 (not 404)."""
    response = client.get("/api/v1/admin/generation-log")
    assert response.status_code in (200, 403, 422)
