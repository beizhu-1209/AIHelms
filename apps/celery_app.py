from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "aihelms",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.beat_schedule_filename = "../data/celerybeat/schedule"

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=settings.celery_prefetch_multiplier,
    worker_concurrency=settings.celery_worker_concurrency or None,
)

celery_app.conf.beat_schedule = {
    "cleanup-audit-logs": {
        "task": "audit_log.cleanup",
        "schedule": crontab(hour=3, minute=0),
    },
    "sync-llm-logs": {
        "task": "llm_log.sync",
        "schedule": settings.llm_log_sync_interval_minutes * 60,
    },
    "cleanup-llm-logs": {
        "task": "llm_log.cleanup",
        "schedule": crontab(hour=4, minute=0),
    },
    "efficiency-aggregate": {
        "task": "efficiency.aggregate",
        "schedule": 5 * 60,
    },
}

# 显式导入 tasks 包以注册所有 celery 任务
# （autodiscover 在 beat 子进程中找不到 tasks 模块）
import tasks  # noqa: E402, F401
