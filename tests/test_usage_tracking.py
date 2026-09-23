"""Feature usage tracking tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.models import GenerationMetric


async def mock_get_session():
    async def _gen():
        mock_sess = MagicMock(spec=AsyncMock)
        mock_sess.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_sess.add = MagicMock()
        yield mock_sess
    return _gen()


@pytest.fixture(autouse=True)
def mock_db(mock_get_session):
    pass


def test_generation_metric_model():
    """GenerationMetric has all required fields."""
    cols = {c.name for c in GenerationMetric.__table__.columns}
    assert "generation_job_id" in cols
    assert "organization_id" in cols
    assert "user_id" in cols
    assert "provider" in cols
    assert "model_name" in cols
    assert "output_language" in cols
    assert "export_format" in cols
    assert "at_score" in cols
    assert "tokens_used" in cols
