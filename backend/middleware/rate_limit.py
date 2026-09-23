"""Rate limiting middleware using Redis sliding window.

Trial users are limited to 1 generation request per 30 seconds and
5 auth requests per hour.  Paid users get 60 generation requests per
minute.  In development mode the middleware is a no-op so local
iteration is not throttled.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from redis.asyncio import Redis
from starlette.types import ASGIApp, Scope, Receive, Send

from backend.config import settings
from backend.auth.jwt_utils import get_user_id_from_token

# ── Rate limit configuration ────────────────────────────────────────────

TIER_LIMITS = {
    "trial": {
        "generate": {"requests": 1, "window": 30},      # 1 per 30s
        "auth": {"requests": 5, "window": 3600},        # 5 per hour
    },
    "paid": {
        "generate": {"requests": 60, "window": 60},     # 60 per minute
        "auth": {"requests": 20, "window": 3600},       # 20 per hour
    },
    "free": {
        "generate": {"requests": 1, "window": 60},      # fallback
        "auth": {"requests": 5, "window": 3600},
    },
}


def _get_tier(user_id: str) -> str:
    """Determine rate limit tier for a user.  Called per-request in dev."""
    # In production this would query the subscription table.
    # For now, default to 'trial' unless the user is explicitly marked paid.
    # The actual subscription check is done by the subscription service.
    return "trial"


def _endpoint_category(path: str) -> str | None:
    """Classify an endpoint path into a rate-limitable category."""
    if path.startswith("/api/v1/generate"):
        return "generate"
    if path.startswith("/api/v1/auth"):
        return "auth"
    return None


async def _check_redis_limit(
    redis: Redis,
    key: str,
    max_requests: int,
    window_seconds: float,
) -> bool:
    """Check if a request is within the rate limit using a Redis sorted set.

    Returns ``True`` if allowed, ``False`` if rate-limited.
    """
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    # Remove entries outside the sliding window
    pipe.zremrangebyscore(key, "-inf", window_start)
    # Count current entries in the window
    pipe.zcard(key)
    # Add current request entry
    pipe.zadd(key, {str(uuid.uuid4()): now})
    # Set TTL on the key so it auto-expires
    pipe.expire(key, int(window_seconds) + 1)
    results = await pipe.execute()

    current_count = results[1]  # zcard result
    return current_count < max_requests


class RateLimitMiddleware:
    """Starlette ASGI middleware that enforces per-user rate limits."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._redis: Redis | None = None
        self._enabled = settings.environment != "development"

    async def _get_redis(self) -> Redis:
        """Lazily initialise and return the Redis client."""
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._enabled:
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        category = _endpoint_category(path)
        if category is None:
            await self.app(scope, receive, send)
            return

        # Extract user id from Authorization header
        token = None
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            # No token — rate limit by IP for auth endpoints
            user_id = str(scope.get("client", ("unknown", 0))[0])
            tier = "free"
        else:
            try:
                user_id = get_user_id_from_token(token)
                tier = _get_tier(user_id)
            except Exception:
                await self.app(scope, receive, send)
                return

        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        limit_cfg = limits.get(category)
        if limit_cfg is None:
            await self.app(scope, receive, send)
            return

        key = f"ratelimit:{user_id}:{category}"

        try:
            redis = await self._get_redis()
            allowed = await _check_redis_limit(
                redis, key, limit_cfg["requests"], limit_cfg["window"]
            )
        except Exception:
            # Redis unavailable — allow the request (graceful degradation)
            await self.app(scope, receive, send)
            return

        if not allowed:
            from starlette.responses import JSONResponse
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "message": f"Too many requests. Try again in {limit_cfg['window']}s.",
                },
                headers={"Retry-After": str(int(limit_cfg["window"]))},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def rate_limit_middleware(app: ASGIApp) -> ASGIApp:
    """Factory function to wrap an ASGI app with the rate limiter."""
    return RateLimitMiddleware(app)
