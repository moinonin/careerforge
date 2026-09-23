"""Rate limiting middleware tests."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.middleware.rate_limit import (
    RateLimitMiddleware,
    _check_redis_limit,
    _endpoint_category,
    TIER_LIMITS,
)
from backend.main import app


# ── Unit tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_redis_limit_allows_within_window():
    """Requests under the limit are allowed."""
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[None, 0, None, None])
    redis.pipeline.return_value = pipeline
    result = await _check_redis_limit(redis, "ratelimit:user1:generate", 5, 60)
    assert result is True
    pipeline.zremrangebyscore.assert_called_once()
    pipeline.zcard.assert_called_once()
    pipeline.zadd.assert_called_once()
    pipeline.expire.assert_called_once()


@pytest.mark.asyncio
async def test_check_redis_limit_blocks_at_limit():
    """Requests at or over the limit are blocked."""
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[None, 5, None, None])
    redis.pipeline.return_value = pipeline
    result = await _check_redis_limit(redis, "ratelimit:user1:generate", 5, 60)
    assert result is False


@pytest.mark.asyncio
async def test_check_redis_limit_allows_after_window():
    """Old entries are cleaned up and new requests are allowed."""
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(side_effect=[
        [None, 0, None, None],  # First request: zcard=0 → allowed
        [None, 1, None, None],  # Second request: zcard=1 → still < 5
    ])
    redis.pipeline.return_value = pipeline
    result = await _check_redis_limit(redis, "ratelimit:user1:generate", 5, 60)
    assert result is True
    result2 = await _check_redis_limit(redis, "ratelimit:user1:generate", 5, 60)
    assert result2 is True


@pytest.mark.asyncio
async def test_endpoint_category_generate():
    assert _endpoint_category("/api/v1/generate") == "generate"
    assert _endpoint_category("/api/v1/generate/bulk") == "generate"


@pytest.mark.asyncio
async def test_endpoint_category_auth():
    assert _endpoint_category("/api/v1/auth/login") == "auth"


@pytest.mark.asyncio
async def test_endpoint_category_none():
    assert _endpoint_category("/api/v1/profiles") is None
    assert _endpoint_category("/health") is None


@pytest.mark.asyncio
async def test_tier_limits_structure():
    """TIER_LIMITS has expected structure."""
    assert "trial" in TIER_LIMITS
    assert "paid" in TIER_LIMITS
    assert TIER_LIMITS["trial"]["generate"]["requests"] == 1
    assert TIER_LIMITS["trial"]["generate"]["window"] == 30
    assert TIER_LIMITS["paid"]["generate"]["requests"] == 60
    assert TIER_LIMITS["paid"]["generate"]["window"] == 60


@pytest.mark.asyncio
async def test_rate_limit_development_mode_no_op():
    """In development mode, rate limiting is a no-op."""
    with patch("backend.middleware.rate_limit.settings.environment", "development"):
        middleware = RateLimitMiddleware(app)
        assert middleware._enabled is False


@pytest.mark.asyncio
async def test_rate_limit_graceful_on_redis_error():
    """Redis errors gracefully allow the request (no crash)."""
    redis = MagicMock()
    redis.pipeline.side_effect = Exception("Connection refused")

    with patch(
        "backend.middleware.rate_limit.settings.environment", "production"
    ), patch(
        "backend.middleware.rate_limit.Redis.from_url", return_value=redis
    ):
        middleware = RateLimitMiddleware(app)
        middleware._enabled = True

        scope = {
            "type": "http",
            "path": "/api/v1/generate",
            "method": "POST",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "query_string": b"",
            "raw_path": b"/api/v1/generate",
        }
        received = []

        async def capture_send(message):
            received.append(message)

        async def mock_receive():
            return {"type": "http.request", "body": b""}

        # Should not raise — falls through to allow request
        await middleware.__call__(scope, mock_receive, capture_send)
        # Middleware caught Redis error and allowed the request through
        assert len(received) > 0
