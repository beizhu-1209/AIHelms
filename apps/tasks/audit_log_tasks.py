import asyncio
import logging
from datetime import datetime, timedelta, timezone

from celery_app import celery_app
from core.config import settings
from core.database import get_worker_session_factory
from repositories import audit_log_repo

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="audit_log.cleanup")
def cleanup_audit_logs():
    _run_async(_cleanup())


async def _cleanup() -> None:
    retention_days = settings.audit_log_retention_days
    if retention_days <= 0:
        logger.info("audit log retention disabled, skip cleanup")
        return
    before = datetime.now(timezone.utc) - timedelta(days=retention_days)
    async with get_worker_session_factory()() as session:
        deleted = await audit_log_repo.delete_before(session, before)
    logger.info("cleaned audit logs before %s, deleted=%s", before.isoformat(), deleted)
