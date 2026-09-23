"""Feedback API tests."""

from __future__ import annotations

from backend.models import Feedback


def test_feedback_model():
    """Feedback has all required columns."""
    cols = {c.name for c in Feedback.__table__.columns}
    required = {"id", "user_id", "generation_job_id", "rating", "comment", "created_at"}
    assert required.issubset(cols)
    assert hasattr(Feedback, "user")
    assert hasattr(Feedback, "generation_job")