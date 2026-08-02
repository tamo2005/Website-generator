"""
workers/celery_app.py — Celery application factory

Broker:  Redis
Backend: Redis (for result storage)
Queues:  default, email, scoring
"""
from celery import Celery

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "website_generator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.email_tasks",
        "workers.scoring_tasks",
        "workers.cleanup_tasks",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Queue routing
    task_routes={
        "workers.email_tasks.*": {"queue": "email"},
        "workers.scoring_tasks.*": {"queue": "scoring"},
        "workers.cleanup_tasks.*": {"queue": "default"},
    },

    # Result TTL — keep results for 1 hour
    result_expires=3600,

    # Retry policy
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "purge-expired-tokens": {
            "task": "workers.cleanup_tasks.purge_expired_tokens",
            "schedule": 3600.0,  # every hour
        },
    },
)
