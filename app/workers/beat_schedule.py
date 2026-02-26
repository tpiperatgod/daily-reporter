"""Dynamic Celery Beat schedule management.

This module handles loading topics from the database and registering
them with Celery Beat for periodic execution.
"""

from celery.schedules import crontab
from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.core.config import settings
import pytz

logger = get_logger(__name__)


async def get_enabled_topics_from_db():
    """
    Fetch all enabled topics from the database.

    Returns:
        list: List of topic dictionaries
    """
    from sqlalchemy import select
    from app.db.session import get_async_session_local
    from app.db.models import Topic

    # Ensure session is initialized (needed for Beat process)
    AsyncSessionLocal = get_async_session_local()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Topic).where(Topic.is_enabled == True))
        topics = result.scalars().all()

        # Convert to list of dicts
        return [
            {
                "id": str(topic.id),
                "name": topic.name,
                "cron_expression": topic.cron_expression,
                "query": topic.query,
            }
            for topic in topics
        ]


def parse_cron_expression(cron_str: str, timezone_str: str = None) -> crontab:
    """
    Parse cron expression string into Celery crontab schedule with timezone.

    Args:
        cron_str: Cron expression in format "m h d mon dow"
        timezone_str: Timezone string (e.g., "Asia/Shanghai", "UTC")
                     If None, uses settings.CRON_TIMEZONE

    Returns:
        celery.schedules.crontab: Celery schedule object with timezone

    Raises:
        ValueError: If cron expression is invalid
    """
    if timezone_str is None:
        timezone_str = settings.CRON_TIMEZONE

    parts = cron_str.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_str}. Expected format: 'minute hour day month weekday'")

    minute, hour, day, month, day_of_week = parts

    # Get timezone object
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_str}, falling back to UTC")
        tz = pytz.UTC

    # Create crontab schedule
    schedule = crontab(
        minute=minute,
        hour=hour,
        day_of_month=day,
        month_of_year=month,
        day_of_week=day_of_week,
    )

    # Override timezone attribute
    schedule.tz = tz

    return schedule


async def update_beat_schedule():
    """
    Update Celery Beat schedule with enabled topics from database.

    This function should be called periodically (e.g., every 5 minutes)
    to sync the schedule with database changes.
    """
    logger.info("Updating beat schedule from database...")

    try:
        # Fetch enabled topics
        topics = await get_enabled_topics_from_db()
        logger.info(f"Found {len(topics)} enabled topics")

        # Build schedule dictionary
        schedule = {}

        for topic in topics:
            try:
                # Parse cron expression with timezone
                cron_schedule = parse_cron_expression(topic["cron_expression"], timezone_str=settings.CRON_TIMEZONE)

                # Add to schedule
                task_name = f"collect_data_{topic['id']}"
                schedule[task_name] = {
                    "task": "app.workers.tasks.collect_data",
                    "schedule": cron_schedule,
                    "args": (topic["id"],),
                }

                logger.info(
                    f"Registered topic '{topic['name']}' in beat schedule",
                    extra={
                        "topic_id": topic["id"],
                        "cron": topic["cron_expression"],
                        "timezone": settings.CRON_TIMEZONE,
                    },
                )

            except Exception as e:
                logger.error(
                    f"Failed to parse cron expression for topic '{topic['name']}'",
                    extra={
                        "topic_id": topic["id"],
                        "cron_expression": topic["cron_expression"],
                        "error": str(e),
                    },
                )
                continue

        # Update Celery app's beat schedule
        celery_app.conf.beat_schedule = schedule

        logger.info(
            f"Beat schedule updated with {len(schedule)} tasks",
            extra={"num_tasks": len(schedule)},
        )

        return schedule

    except Exception as e:
        logger.error(f"Failed to update beat schedule: {e}")
        raise


# Sync wrapper for use in non-async contexts
def update_beat_schedule_sync():
    """
    Synchronous wrapper for update_beat_schedule.

    This can be called from Celery Beat's initialization.
    """
    import asyncio

    return asyncio.run(update_beat_schedule())


# Load initial schedule from database when module is imported
logger.info("Loading initial beat schedule from database...")
try:
    initial_schedule = update_beat_schedule_sync()
    logger.info(
        f"Successfully loaded {len(initial_schedule)} tasks from database at startup",
        extra={"task_names": list(initial_schedule.keys())},
    )
except Exception as e:
    logger.error(f"Failed to load initial beat schedule: {e}", exc_info=True)
    # Set empty schedule and log error
    celery_app.conf.beat_schedule = {}

# Log final schedule state
logger.info(
    "Beat schedule initialization complete",
    extra={
        "num_tasks": len(celery_app.conf.beat_schedule),
        "task_names": list(celery_app.conf.beat_schedule.keys()),
    },
)


__all__ = ["update_beat_schedule", "update_beat_schedule_sync"]
