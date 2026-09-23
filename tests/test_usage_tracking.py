"""Feature usage tracking tests."""

from __future__ import annotations

from backend.models import GenerationMetric


def test_generation_metric_model():
    """GenerationMetric has all required columns."""
    cols = {c.name for c in GenerationMetric.__table__.columns}
    required = {
        "id", "generation_job_id", "organization_id", "user_id",
        "provider", "model_name", "output_language", "export_format",
        "at_score", "tokens_used", "created_at",
    }
    assert required.issubset(cols)
    # Verify relationships exist
    assert hasattr(GenerationMetric, "generation_job")
    assert hasattr(GenerationMetric, "organization")
    assert hasattr(GenerationMetric, "user")
