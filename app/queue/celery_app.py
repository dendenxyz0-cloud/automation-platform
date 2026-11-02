from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "automation_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.orders"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="order_processing",
    task_routes={
        "process_order_task": {"queue": "order_processing"},
    },
)
