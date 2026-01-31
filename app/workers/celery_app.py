"""Celery application configuration and initialization."""

from celery import Celery
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "x_news_digest",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]  # Auto-discover tasks
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_acks_late=True,  # Acknowledge after task completion
    worker_prefetch_multiplier=1,  # Disable prefetching for fairness

    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Use extended result format

    # Retry settings
    task_default_retry_delay=60,  # Default retry delay: 60 seconds
    task_max_retries=3,  # Default max retries

    # Worker settings
    worker_concurrency=2,  # Number of worker processes
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks

    # Beat scheduler settings
    beat_scheduler_filename="celerybeat-schedule",
    beat_max_loop_interval=300,  # Check schedule every 5 minutes
)

logger.info(
    "Celery app initialized",
    extra={
        "broker": settings.CELERY_BROKER_URL,
        "backend": settings.CELERY_RESULT_BACKEND,
        "worker_concurrency": celery_app.conf.worker_concurrency
    }
)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Setup periodic tasks after Celery app is configured.

    This is called when the worker starts.
    """
    from app.workers.beat_schedule import update_beat_schedule

    logger.info("Setting up periodic tasks...")
    # Note: Dynamic schedule is loaded via beat_schedule.py
    # This is just a hook for any additional setup


# Health check task
@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """
    Simple health check task to verify Celery is working.

    Returns:
        dict: Health status
    """
    logger.info("Health check task executed")
    return {
        "status": "healthy",
        "task_id": self.request.id
    }


__all__ = ["celery_app"]
