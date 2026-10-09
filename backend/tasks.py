"""Celery worker — background generation execution (T3 tightening).

The API dispatches ``run_generation_task`` after creating a job when
``settings.use_celery`` is enabled; otherwise generation runs inline in the
request (default, keeping local dev and the test suite self-contained).

Job recovery: on startup the API re-enqueues jobs stuck in
``processing``/``pending`` so no generation is lost on deploy or crash.
"""

from __future__ import annotations

import asyncio

from celery import Celery

from backend.config import settings

worker = Celery(
    "careerforge",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
worker.conf.update(
    task_acks_late=True,  # re-deliver if the worker dies mid-task
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    worker_max_tasks_per_child=100,
    timezone="UTC",
)


@worker.task(bind=True, max_retries=3, autoretry_for=(ConnectionError,))
def run_generation_task(self, job_id: str, user_id: str) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Run a generation job to completion with retry on transient failure.

    Opens its own async DB session (worker process has no request context).
    Per-job failures mark the job failed; the task itself only retries on
    infrastructure errors (broker/DB connection loss).
    """
    return asyncio.run(_run(job_id, user_id))


async def _run(job_id: str, user_id: str) -> dict[str, str]:
    import backend.database as db_module
    from backend.api.routes.generate import _run_generation_inline
    from backend.database import init_db
    from backend.llm.adapter import GenerationError
    from backend.llm.service import mark_job_failed
    from backend.models import GenerationJob

    await init_db()
    assert db_module._session_factory is not None
    async with db_module._session_factory() as session:
        job = await session.get(GenerationJob, job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        try:
            result = await _run_generation_inline(
                session,
                job,
                user_id,
                provider=job.provider,
                model=job.model_name,
            )
        except (GenerationError, ValueError) as exc:
            await mark_job_failed(session, job_id, str(exc))
            await session.commit()
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        await session.commit()
        return {"job_id": job_id, "status": result.get("status", "completed")}


async def recover_stuck_jobs() -> int:
    """Re-enqueue jobs stuck in ``processing``/``pending`` (e.g. after a deploy).

    Returns the number of jobs re-enqueued. No-op when Celery is disabled —
    inline execution completes within the request, so stuck rows imply a crash
    and are re-dispatched as tasks here regardless.
    """
    from sqlalchemy import select

    import backend.database as db_module
    from backend.database import init_db
    from backend.models import GenerationJob

    await init_db()
    assert db_module._session_factory is not None
    async with db_module._session_factory() as session:
        stmt = select(GenerationJob).where(GenerationJob.status.in_(["pending", "processing"]))
        rows = (await session.execute(stmt)).scalars().all()
        for job in rows:
            run_generation_task.delay(job.id, job.user_id)
        return len(rows)
