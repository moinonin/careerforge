"""T6: Burst rate-limit test — free-tier user hammering /api/v1/generate."""

from __future__ import annotations

import pytest


class _FakePipeline:
    """Minimal async pipeline emulating a Redis sorted set."""

    def __init__(self, store: dict):
        self._store = store
        self._ops: list[tuple] = []

    def zremrangebyscore(self, key, lo, hi):
        self._ops.append(("zrem", key, float(hi)))

    def zcard(self, key):
        self._ops.append(("zcard", key))

    def zadd(self, key, mapping):
        self._ops.append(("zadd", key, mapping))

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))

    async def execute(self):
        import time

        results = []
        for op in self._ops:
            if op[0] == "zrem":
                key, cutoff = op[1], op[2]
                zset = self._store.get(key, {})
                self._store[key] = {m: s for m, s in zset.items() if s > cutoff}
                results.append(0)
            elif op[0] == "zcard":
                results.append(len(self._store.get(op[1], {})))
            elif op[0] == "zadd":
                key, mapping = op[1], op[2]
                self._store.setdefault(key, {}).update(mapping)
                results.append(1)
            elif op[0] == "expire":
                results.append(1)
        return results


class _FakeRedis:
    def __init__(self):
        self.store: dict = {}

    def pipeline(self):
        return _FakePipeline(self.store)


@pytest.mark.asyncio
async def test_free_tier_burst_is_throttled():
    """A free-tier user bursting POST /generate past the limit gets 429s."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from backend.auth.jwt_utils import create_access_token
    from backend.main import create_app
    from fastapi.testclient import TestClient

    fake_profile = MagicMock()
    fake_profile.id = "p1"
    fake_profile.user_id = "burst-user"

    fake_job = MagicMock()
    fake_job.id = "job-1"

    async def _exec(stmt):
        r = MagicMock()
        r.scalar_one_or_none.return_value = fake_profile
        return r

    async def _trial_session():
        session = MagicMock()
        session.execute = AsyncMock(side_effect=_exec)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    async def _fake_user():
        return "burst-user"

    fake_redis = _FakeRedis()
    token = create_access_token("burst-user", "burst@example.com")

    with (
        patch("backend.middleware.rate_limit.settings.environment", "production"),
        patch("backend.middleware.rate_limit.Redis.from_url", return_value=fake_redis),
        patch("backend.middleware.rate_limit._get_tier", return_value="free"),
        patch(
            "backend.api.routes.generate.create_generation_job",
            new_callable=AsyncMock,
            side_effect=lambda **kw: fake_job,
        ),
        patch(
            "backend.api.routes.generate.mark_job_processing",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.api.routes.generate._run_generation_inline",
            new_callable=AsyncMock,
            return_value={"job_id": "job-1", "status": "completed"},
        ),
    ):
        # Fresh app inside the patch context so the middleware stack picks up
        # the production environment flag (module-level app may already be built).
        app = create_app()
        from backend.auth.schemas import get_current_user_id
        from backend.database import get_session

        app.dependency_overrides[get_session] = _trial_session
        app.dependency_overrides[get_current_user_id] = _fake_user

        client = TestClient(app)
        statuses = []
        for _ in range(5):
            resp = client.post(
                "/api/v1/generate",
                json={"profile_id": "p1", "job_description": "Some job desc"},
                headers={"Authorization": f"Bearer {token}"},
            )
            statuses.append(resp.status_code)

    # Free tier: 1 generation per 30s — the first request passes, the rest throttle
    assert statuses[0] != 429, f"first request was throttled: {statuses}"
    assert 429 in statuses[1:], f"burst not throttled: {statuses}"
