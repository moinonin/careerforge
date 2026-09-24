"""Download artifact endpoint tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def mock_get_session():
    async def _gen():
        yield MagicMock()
    return _gen()


@pytest.fixture(autouse=True)
def _mock_db():
    with patch("backend.database.get_session", side_effect=mock_get_session):
        yield


@pytest.fixture
def client(_mock_db):
    import importlib
    import backend.main
    importlib.reload(backend.main)
    from backend.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_download_artifact_requires_auth(client):
    """download_artifact requires auth — returns 401 when no token."""
    response = client.get("/api/v1/generate/library/test-artifact/download")
    assert response.status_code == 401