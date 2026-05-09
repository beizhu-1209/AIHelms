from celery import Celery

from core.config import settings

celery_app = Celery(
    "aihelms",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

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
