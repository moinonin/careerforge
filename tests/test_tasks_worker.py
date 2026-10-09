"""T3 tests: Celery worker dispatch + startup job recovery + storage backend."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch


def test_worker_module_imports_and_config():
    """backend.tasks.worker is a Celery app with late-ack retry config."""
    from backend.tasks import worker

    assert worker.conf.task_acks_late is True
    assert worker.conf.task_reject_on_worker_lost is True
    assert worker.conf.broker_url is not None
    assert worker.conf.task_default_retry_delay == 30


def test_run_generation_task_marks_failed_missing_job(tmp_path):
    """A task for a nonexistent job returns not_found without raising."""
    import asyncio

    import backend.database as db_module
    import backend.models  # noqa: F401 — register tables on Base.metadata
    from backend.database import Base
    from backend.tasks import run_generation_task
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    prev_engine, prev_factory = db_module.engine, db_module._session_factory
    db_module.engine, db_module._session_factory = engine, factory

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    try:
        result = run_generation_task.run("nonexistent-job", "some-user")
        assert result["status"] == "not_found"
    finally:
        db_module.engine, db_module._session_factory = prev_engine, prev_factory
        asyncio.run(engine.dispose())


def test_recover_stuck_jobs_reenqueues(tmp_path):
    """Startup recovery dispatches a Celery task for each stuck job."""
    import asyncio

    import backend.database as db_module
    from backend.database import Base
    from backend.models import GenerationJob  # registers tables on Base.metadata
    from backend.tasks import recover_stuck_jobs
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t2.db")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    prev_engine, prev_factory = db_module.engine, db_module._session_factory
    db_module.engine, db_module._session_factory = engine, factory

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(
                GenerationJob(
                    id="stuck-1",
                    user_id="u1",
                    profile_id="p1",
                    job_title="t",
                    job_description="d",
                    status="processing",
                )
            )
            session.add(
                GenerationJob(
                    id="done-1",
                    user_id="u1",
                    profile_id="p1",
                    job_title="t",
                    job_description="d",
                    status="completed",
                )
            )
            await session.commit()

    asyncio.run(_setup())
    try:
        with patch("backend.tasks.run_generation_task.delay") as mock_delay:
            count = asyncio.run(recover_stuck_jobs())
        assert count == 1
        mock_delay.assert_called_once_with("stuck-1", "u1")
    finally:
        db_module.engine, db_module._session_factory = prev_engine, prev_factory
        asyncio.run(engine.dispose())


def test_local_storage_save_and_read(tmp_path):
    """LocalStorage copies an outside file into its dir and reads it back."""
    from backend.storage import LocalStorage

    base = tmp_path / "store"
    src = tmp_path / "external.txt"
    src.write_bytes(b"hello artifact")

    storage = LocalStorage(str(base))
    ref = storage.save_file(str(src), "a/b/c.txt")
    assert ref.startswith(str(base))
    assert storage.exists(ref)
    assert storage.read_bytes(ref) == b"hello artifact"


def test_get_storage_defaults_to_local(tmp_path, monkeypatch):
    """Without S3 credentials, get_storage returns LocalStorage."""
    from backend import config
    from backend.storage import LocalStorage, get_storage, reset_storage

    reset_storage()
    monkeypatch.setattr(config.settings, "s3_access_key_id", None)
    monkeypatch.setattr(config.settings, "generation_artifacts_dir", str(tmp_path))
    try:
        storage = get_storage()
        assert isinstance(storage, LocalStorage)
    finally:
        reset_storage()


def test_celery_dispatch_path(tmp_path):
    """With use_celery=True the route enqueues and returns 'queued'."""
    from fastapi.testclient import TestClient

    from backend.config import settings
    from backend.main import app

    app.dependency_overrides.clear()
    from backend.auth.schemas import get_current_user_id
    from backend.database import get_session

    fake_profile = MagicMock()
    fake_profile.id = "p1"
    fake_profile.user_id = "u1"

    async def _mock_session():
        session = AsyncMock()

        async def _execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = fake_profile
            return result

        session.execute = _execute
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    async def _mock_user():
        return "u1"

    app.dependency_overrides[get_session] = _mock_session
    app.dependency_overrides[get_current_user_id] = _mock_user

    async def _fake_create(**kwargs):
        job = MagicMock()
        job.id = "job-123"
        return job

    with (
        patch.object(settings, "use_celery", True),
        patch("backend.api.routes.generate.create_generation_job", side_effect=_fake_create),
        patch("backend.tasks.run_generation_task.delay") as mock_delay,
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/generate",
            json={"profile_id": "p1", "job_description": "Backend engineer"},
        )
        assert resp.status_code == 202, resp.text
        assert resp.json()["status"] == "queued"
        mock_delay.assert_called_once_with("job-123", "u1")
    app.dependency_overrides.clear()
