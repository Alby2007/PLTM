"""Celery application for async background tasks"""

import os
from celery import Celery
from celery.schedules import crontab
from loguru import logger

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "lltm",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "src.workers.tasks.decay_tasks",
        "src.workers.tasks.embedding_tasks",
        "src.workers.tasks.maintenance_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
    },
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
)

# Periodic tasks (Celery Beat schedule)
celery_app.conf.beat_schedule = {
    # Decay processing every 6 hours
    "process-decay-all-users": {
        "task": "src.workers.tasks.decay_tasks.process_decay_all_users",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    
    # Cleanup expired sessions daily
    "cleanup-expired-sessions": {
        "task": "src.workers.tasks.maintenance_tasks.cleanup_expired_sessions",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
    },
    
    # Generate daily reports
    "generate-daily-reports": {
        "task": "src.workers.tasks.maintenance_tasks.generate_daily_reports",
        "schedule": crontab(minute=0, hour=1),  # 1 AM daily
    },
    
    # Cleanup old embeddings weekly
    "cleanup-old-embeddings": {
        "task": "src.workers.tasks.maintenance_tasks.cleanup_old_embeddings",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Sunday 3 AM
    },
    
    # Update cache statistics every 5 minutes
    "update-cache-stats": {
        "task": "src.workers.tasks.maintenance_tasks.update_cache_stats",
        "schedule": 300,  # 5 minutes
    },
}

logger.info(f"Celery app configured: broker={CELERY_BROKER_URL}")
