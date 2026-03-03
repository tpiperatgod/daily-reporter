"""Dynamic Celery Beat schedule management.

DECOMMISSIONED: Topic-scoped scheduling has been removed.

This module previously handled loading topics from the database and registering
them with Celery Beat for periodic execution. Now it returns empty schedules
for API compatibility.

User-scoped scheduling is handled separately at the user level.
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
        # Note: cron_expression removed - topic-scoped scheduling is decommissioned
        # User-scoped scheduling is handled at the user level
        return [
            {
                "id": str(topic.id),
                "name": topic.name,
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

    DECOMMISSIONED: Topic-scoped scheduling has been removed.
    User-scoped scheduling is now handled at the user level.
    This function returns an empty schedule for compatibility.

    Returns:
        dict: Empty schedule dictionary
    """
    logger.info(
        "Beat schedule update requested - topic-scoped scheduling is decommissioned, returning empty schedule"
    )

    # Topic-scoped pipeline is decommissioned
    # User-scoped scheduling is handled separately via user-level cron triggers
    schedule = {}

    # Update Celery app's beat schedule with empty dict
    celery_app.conf.beat_schedule = schedule

    logger.info(
        "Beat schedule updated (empty - topic-scoped scheduling decommissioned)",
        extra={"num_tasks": 0},
    )

    return schedule


# Sync wrapper for use in non-async contexts
def update_beat_schedule_sync():
    """
    Synchronous wrapper for update_beat_schedule.

    This can be called from Celery Beat's initialization.
    """
    import asyncio

    return asyncio.run(update_beat_schedule())


# Load initial schedule when module is imported
# Note: Topic-scoped scheduling is decommissioned
logger.info("Loading initial beat schedule (topic-scoped scheduling decommissioned)...")
try:
    initial_schedule = update_beat_schedule_sync()
    logger.info(
        "Beat schedule loaded (empty - topic-scoped scheduling decommissioned)",
        extra={"num_tasks": 0},
    )
except Exception as e:
    logger.error(f"Failed to initialize beat schedule: {e}", exc_info=True)
    celery_app.conf.beat_schedule = {}



__all__ = ["update_beat_schedule", "update_beat_schedule_sync"]
