"""Health endpoint tests — updated for Sprint 9."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "careerforge-backend"
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "s3" in data["checks"]
    assert "llm_provider" in data["checks"]


def test_health_checks_structure(client: TestClient) -> None:
    """Each check has a status field."""
    response = client.get("/health")
    data = response.json()
    for check_name in ["database", "redis", "s3", "llm_provider"]:
        check = data["checks"][check_name]
        assert "status" in check


def test_health_returns_timestamp(client: TestClient) -> None:
    response = client.get("/health")
    data = response.json()
    assert "timestamp" in data


def test_ready_endpoint_returns_200(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "careerforge-backend"
    assert "checks" in data
