import asyncio
import logging

from billiard.exceptions import SoftTimeLimitExceeded

from celery_app import celery_app
from core.config import settings
from core.database import get_worker_session_factory
from services import ai_policies_service

logger = logging.getLogger(__name__)

AUDIT_SOFT_TIME_LIMIT = settings.ai_policies_timeout_seconds + 30
AUDIT_TIME_LIMIT = settings.ai_policies_timeout_seconds + 90


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="ai_policies.skill_audit",
    acks_late=True,
    max_retries=0,
    soft_time_limit=AUDIT_SOFT_TIME_LIMIT,
    time_limit=AUDIT_TIME_LIMIT,
)
def run_skill_audit(self, audit_pk: int) -> None:
    try:
        _run_async(_run(audit_pk))
    except SoftTimeLimitExceeded:
        logger.exception("AI Policies skill audit timed out: audit_pk=%s", audit_pk)
        _run_async(
            ai_policies_service.fail_audit_by_id(
                audit_pk, "安全审查执行超时，请稍后重新发起审查"
            )
        )
        raise
    except Exception:
        logger.exception("AI Policies skill audit task failed: audit_pk=%s", audit_pk)
        _run_async(
            ai_policies_service.fail_audit_by_id(
                audit_pk, "安全审查任务执行失败，请稍后重新发起审查"
            )
        )
        raise


async def _run(audit_pk: int) -> None:
    try:
        async with get_worker_session_factory()() as session:
            await ai_policies_service.process_skill_audit(session, audit_pk)
    except Exception:
        logger.exception("AI Policies skill audit worker failed: audit_pk=%s", audit_pk)
        raise
