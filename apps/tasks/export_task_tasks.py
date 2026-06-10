import asyncio
import logging

from celery_app import celery_app
from core.database import get_worker_session_factory
from services import export_task_service

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="export_task.generate",
    acks_late=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=360,
)
def generate_export_file(self, task_id: int) -> None:
    try:
        _run_async(_generate(task_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30) from exc


async def _generate(task_id: int) -> None:
    try:
        async with get_worker_session_factory()() as session:
            await export_task_service.process_export_task(session, task_id)
    except Exception:
        logger.exception("export task worker failed: task_id=%s", task_id)

@celery_app.task(name="export_task.cleanup", acks_late=True, time_limit=180)
def cleanup_export_tasks() -> None:
    _run_async(_cleanup())


async def _cleanup() -> None:
    try:
        async with get_worker_session_factory()() as session:
            await export_task_service.cleanup_export_tasks(session)
    except Exception:
        logger.exception("export task cleanup failed")
