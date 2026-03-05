"""Celery tasks for the X-News-Digest pipeline."""

import asyncio
import inspect
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.db.models import Topic, Item, User, UserDigest
from app.services.provider.factory import get_provider
from app.services.llm.client import LLMClient
from app.services.embedding.factory import get_embedding_provider
from app.services.notifier.renderer import render_markdown_digest
from app.core.config import settings

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.collect_data", max_retries=3)
def collect_data(self, topic_id: str):
    """
    Collect data from Twitter/X for a topic.

    Args:
        topic_id: UUID of the topic to collect data for

    Workflow:
        1. Load topic from DB
        2. Calculate time window (last_collection_timestamp to now)
        3. Fetch items from provider
        4. Generate embeddings and check for duplicates
        5. Insert new items into DB
        6. Update last_collection_timestamp
        7. Chain to generate_digest if new items were collected
    """
    logger.info(f"Starting data collection for topic {topic_id}")

    # Run async task in sync context
    return asyncio.run(_collect_data_async(self, topic_id))


async def _collect_data_async(self, topic_id: str):
    """Async implementation of collect_data task."""
    from app.db.session import get_async_session_local

    try:
        async with get_async_session_local()() as session:
            # 1. Load topic
            topic_result = await session.execute(select(Topic).where(Topic.id == topic_id))
            topic = topic_result.scalar_one_or_none()

            if not topic:
                logger.error(f"Topic {topic_id} not found")
                return {"status": "error", "message": "Topic not found"}

            if not topic.is_enabled:
                logger.warning(f"Topic {topic.name} is disabled, skipping")
                return {"status": "skipped", "message": "Topic is disabled"}

            logger.info(
                f"Collecting data for topic: {topic.name}",
                extra={"topic_id": topic_id, "query": topic.query},
            )

            # 2. Calculate time window
            end_date = datetime.now(UTC)
            if topic.last_collection_timestamp:
                # Use last collection timestamp
                start_date = topic.last_collection_timestamp
            else:
                # First run - go back 24 hours
                start_date = end_date - timedelta(hours=24)

            logger.info(
                f"Time window: {start_date} to {end_date}",
                extra={"start": start_date.isoformat(), "end": end_date.isoformat()},
            )

            # 3. Fetch items from provider
            provider = get_provider()

            # Check if provider supports since_id parameter
            fetch_kwargs = {
                "query": topic.query,
                "start_date": start_date,
                "end_date": end_date,
                "max_items": 100,
            }

            # Add since_id if available and provider supports it
            if topic.last_tweet_id:
                sig = inspect.signature(provider.fetch)
                if "since_id" in sig.parameters:
                    fetch_kwargs["since_id"] = topic.last_tweet_id
                    logger.info(f"Using since_id: {topic.last_tweet_id}")

            raw_items = await provider.fetch(**fetch_kwargs)

            logger.info(f"Fetched {len(raw_items)} items from provider")

            if not raw_items:
                logger.info("No items fetched, updating timestamp")
                topic.last_collection_timestamp = end_date
                await session.commit()
                return {
                    "status": "success",
                    "message": "No new items",
                    "items_collected": 0,
                }

            # 4. Process items with deduplication using batch embeddings
            embedding_provider = get_embedding_provider()
            llm_client = LLMClient(embedding_provider=embedding_provider)
            new_items = []
            duplicates = 0

            # Generate embeddings in batch for all items
            texts = [raw_item.text for raw_item in raw_items]
            logger.info(f"Generating embeddings for {len(texts)} items in batch")

            try:
                embedding_hashes = await llm_client.generate_embedding_hashes_batch(texts)
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                # Fall back to None for all hashes
                embedding_hashes = [None] * len(texts)

            # Batch check for existing items (fixes N+1 query problem)
            from app.db.utils import batch_check_exists

            # Collect all source_ids and embedding_hashes
            source_ids = [raw_item.source_id for raw_item in raw_items]
            embedding_hashes_non_null = [h for h in embedding_hashes if h is not None]

            # Batch check existing source_ids (1 query total - GLOBAL uniqueness)
            existing_source_ids = await batch_check_exists(
                session,
                Item,
                Item.source_id,
                source_ids,
            )

            # Batch check existing embedding hashes (1 query total)
            existing_hashes = (
                await batch_check_exists(
                    session,
                    Item,
                    Item.embedding_hash,
                    embedding_hashes_non_null,
                    additional_filters=[Item.topic_id == topic_id],
                )
                if embedding_hashes_non_null
                else set()
            )

            # Process each item with in-memory duplicate checking
            seen_source_ids = set()  # Track source_ids within this batch

            for raw_item, embedding_hash in zip(raw_items, embedding_hashes):
                # Check for intra-batch duplicate source_id
                if raw_item.source_id in seen_source_ids:
                    duplicates += 1
                    logger.debug(f"Skipping intra-batch duplicate source_id: {raw_item.source_id}")
                    continue
                seen_source_ids.add(raw_item.source_id)

                # Check for duplicate by source_id (in-memory)
                if raw_item.source_id in existing_source_ids:
                    duplicates += 1
                    continue

                # Also check by embedding_hash if available (in-memory)
                if embedding_hash and embedding_hash in existing_hashes:
                    duplicates += 1
                    logger.debug(f"Duplicate found via embedding hash: {raw_item.source_id}")
                    continue

                # Create new item
                item = Item(
                    topic_id=topic_id,
                    source_id=raw_item.source_id,
                    author=raw_item.author,
                    text=raw_item.text,
                    url=raw_item.url,
                    created_at=raw_item.created_at,
                    collected_at=datetime.now(UTC),
                    media_urls=raw_item.media_urls if raw_item.media_urls else None,
                    metrics=raw_item.metrics if raw_item.metrics else None,
                    embedding_hash=embedding_hash,
                )
                new_items.append(item)

            # 5. Insert new items
            if new_items:
                session.add_all(new_items)
                await session.commit()
                logger.info(f"Inserted {len(new_items)} new items")
            else:
                logger.info("No new items after deduplication")

            # 6. Update last_collection_timestamp and last_tweet_id
            topic.last_collection_timestamp = end_date

            # Track highest tweet ID (Twitter IDs are chronological integers)
            if raw_items:
                max_tweet_id = None
                for raw_item in raw_items:
                    try:
                        # Compare tweet IDs as integers
                        current_id = int(raw_item.source_id)
                        if max_tweet_id is None or current_id > max_tweet_id:
                            max_tweet_id = current_id
                    except ValueError:
                        # Skip non-numeric IDs
                        continue

                if max_tweet_id is not None:
                    topic.last_tweet_id = str(max_tweet_id)
                    logger.info(f"Updated last_tweet_id to: {topic.last_tweet_id}")

            await session.commit()

            await llm_client.close()

            # 7. Chain to generate_digest if we have new items
            if new_items:
                logger.info("Chaining to generate_digest task")

                # Compute tweet-based time window from actual tweet created_at timestamps
                tweet_window_end = max(item.created_at for item in new_items)
                if topic.last_item_created_at:
                    tweet_window_start = topic.last_item_created_at
                else:
                    tweet_window_start = min(item.created_at for item in new_items)

                # Advance the watermark for the next collection cycle
                topic.last_item_created_at = tweet_window_end
                await session.commit()

                generate_digest.delay(
                    topic_id=topic_id,
                    window_start=tweet_window_start.isoformat(),
                    window_end=tweet_window_end.isoformat(),
                )

            return {
                "status": "success",
                "message": "Data collected successfully",
                "items_collected": len(new_items),
                "duplicates_skipped": duplicates,
            }

    except Exception as e:
        logger.error(f"Data collection failed: {e}", exc_info=True)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2**self.request.retries * 60  # 60s, 120s, 240s
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="app.workers.tasks.generate_digest", max_retries=1)
def generate_digest(self, topic_id: str, window_start: str, window_end: str):
    """
    DEPRECATED: Topic-scoped digest generation is decommissioned.

    This task is retained for task name compatibility only.
    User-scoped digest generation should use generate_user_digest instead.

    Args:
        topic_id: UUID of the topic (ignored)
        window_start: Start of time window (ignored)
        window_end: End of time window (ignored)

    Returns:
        Always returns success with deprecation message
    """
    logger.info("Topic-scoped generate_digest task called - decommissioned, returning success")
    return {"status": "success", "message": "Topic-scoped digest generation decommissioned - use user-scoped pipeline"}


async def _generate_digest_async(self, topic_id: str, window_start: str, window_end: str):
    """DEPRECATED: Async implementation removed - task is now a stub."""
    # This function is retained for import compatibility only
    return {"status": "success", "message": "Decommissioned"}


@celery_app.task(bind=True, name="app.workers.tasks.notify", max_retries=2)
def notify(self, digest_id: str):
    """
    DEPRECATED: Topic-scoped notifications are decommissioned.

    This task is retained for task name compatibility only.
    User-scoped notifications should use notify_user_digest instead.

    Args:
        digest_id: UUID of the digest (ignored)

    Returns:
        Always returns success with deprecation message
    """
    logger.info("Topic-scoped notify task called - decommissioned, returning success")
    return {"status": "success", "message": "Topic-scoped notifications decommissioned - use user-scoped pipeline"}


async def _notify_async(self, digest_id: str):
    """DEPRECATED: Async implementation removed - task is now a stub."""
    # This function is retained for import compatibility only
    return {"status": "success", "message": "Decommissioned"}


# =============================================================================
# User Pipeline Tasks
# =============================================================================


def parse_time_window(time_window: str) -> int:
    mapping = {"4h": 4, "12h": 12, "24h": 24, "1d": 24}
    if time_window not in mapping:
        raise ValueError(f"Invalid time_window: {time_window}")
    return mapping[time_window]


@celery_app.task(bind=True, name="app.workers.tasks.collect_user_topics", max_retries=3)
def collect_user_topics(self, user_id: str, time_window: str = "24h"):
    """
    Collect data from Twitter/X for all topics in user.topics.

    Args:
        user_id: UUID of the user

    Workflow:
        1. Load user and their topics list
        2. For each topic in user.topics, collect items
        3. Aggregate results
        4. Chain to generate_user_digest
    """
    logger.info(
        f"Starting user topic collection for user {user_id}",
        extra={"time_window": time_window},
    )
    return asyncio.run(_collect_user_topics_async(self, user_id, time_window))


async def _collect_user_topics_async(self, user_id: str, time_window: str = "24h"):
    """Async implementation of collect_user_topics task.

    Collects data from all topics in user.topics JSONB array.
    """
    from uuid import UUID
    from app.db.session import get_async_session_local
    from app.db.utils import batch_check_exists

    try:
        async with get_async_session_local()() as session:
            # 1. Load user (no eager loading needed - topics is JSONB column)
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found")
                return {"status": "error", "message": "User not found"}

            # 2. Handle empty topics list
            if not user.topics:
                logger.info(f"User {user_id} has no topics")
                return {
                    "status": "success",
                    "message": "No topics configured",
                    "user_id": user_id,
                    "items_collected": 0,
                }

            # 3. Load Topic objects from user.topics UUID strings
            try:
                topic_uuids = [UUID(tid) for tid in user.topics]
            except ValueError as e:
                logger.error(f"Invalid UUID in user.topics for user {user_id}: {e}")
                return {
                    "status": "error",
                    "message": f"Invalid topic UUID in user configuration: {e}",
                    "user_id": user_id,
                }

            topics_result = await session.execute(select(Topic).where(Topic.id.in_(topic_uuids)))
            topics = topics_result.scalars().all()

            if not topics:
                logger.info(f"No valid topics found for user {user_id}")
                return {
                    "status": "success",
                    "message": "No valid topics found",
                    "user_id": user_id,
                    "items_collected": 0,
                }

            logger.info(f"Collecting data for user {user_id} with {len(topics)} topics")

            try:
                hours = parse_time_window(time_window)
            except ValueError as e:
                logger.error(str(e))
                return {
                    "status": "error",
                    "message": str(e),
                    "user_id": user_id,
                    "time_window": time_window,
                }

            try:
                config_tz = ZoneInfo(settings.CRON_TIMEZONE)
            except ZoneInfoNotFoundError:
                logger.error(f"Invalid CRON_TIMEZONE: {settings.CRON_TIMEZONE}")
                return {
                    "status": "error",
                    "message": "Invalid timezone configuration",
                    "user_id": user_id,
                    "time_window": time_window,
                }

            now_tz = datetime.now(config_tz)
            window_end_utc = now_tz.astimezone(UTC)
            window_start_utc = (now_tz - timedelta(hours=hours)).astimezone(UTC)

            logger.info(
                f"Time window (configured tz): {now_tz - timedelta(hours=hours)} to {now_tz}",
                extra={
                    "time_window": time_window,
                    "timezone": settings.CRON_TIMEZONE,
                    "window_start_utc": window_start_utc.isoformat(),
                    "window_end_utc": window_end_utc.isoformat(),
                },
            )

            # Track aggregated results
            total_items_collected = 0
            topics_processed = 0
            enabled_topics = []

            # Get provider once (shared across topics)
            provider = get_provider()

            # 4. Process each topic
            for topic in topics:
                if not topic.is_enabled:
                    logger.info(f"Topic {topic.name} is disabled, skipping")
                    continue

                enabled_topics.append(topic)

                logger.info(
                    f"Collecting data for topic: {topic.name}",
                    extra={"topic_id": str(topic.id), "query": topic.query},
                )

                # Calculate time window for this topic
                end_date = datetime.now(UTC)
                if topic.last_collection_timestamp:
                    start_date = topic.last_collection_timestamp
                else:
                    start_date = end_date - timedelta(hours=24)

                logger.info(
                    f"Time window: {start_date} to {end_date}",
                    extra={"start": start_date.isoformat(), "end": end_date.isoformat()},
                )

                # Fetch items from provider
                fetch_kwargs = {
                    "query": topic.query,
                    "start_date": start_date,
                    "end_date": end_date,
                    "max_items": 100,
                }

                # Add since_id if available and provider supports it
                if topic.last_tweet_id:
                    sig = inspect.signature(provider.fetch)
                    if "since_id" in sig.parameters:
                        fetch_kwargs["since_id"] = topic.last_tweet_id
                        logger.info(f"Using since_id: {topic.last_tweet_id}")

                try:
                    raw_items = await provider.fetch(**fetch_kwargs)
                except Exception as e:
                    logger.error(f"Failed to fetch items for topic {topic.name}: {e}")
                    continue

                logger.info(f"Fetched {len(raw_items)} items from provider for topic {topic.name}")

                if not raw_items:
                    logger.info(f"No items fetched for topic {topic.name}")
                    topic.last_collection_timestamp = end_date
                    await session.commit()
                    topics_processed += 1
                    continue

                # 5. Process items with deduplication using batch embeddings
                embedding_provider = get_embedding_provider()
                llm_client = LLMClient(embedding_provider=embedding_provider)
                new_items = []
                duplicates = 0

                # Generate embeddings in batch for all items
                texts = [raw_item.text for raw_item in raw_items]
                logger.info(f"Generating embeddings for {len(texts)} items in batch")

                try:
                    embedding_hashes = await llm_client.generate_embedding_hashes_batch(texts)
                except Exception as e:
                    logger.error(f"Batch embedding generation failed: {e}")
                    embedding_hashes = [None] * len(texts)

                # Batch check for existing items (fixes N+1 query problem)
                source_ids = [raw_item.source_id for raw_item in raw_items]
                embedding_hashes_non_null = [h for h in embedding_hashes if h is not None]

                # Batch check existing source_ids (GLOBAL uniqueness)
                existing_source_ids = await batch_check_exists(
                    session,
                    Item,
                    Item.source_id,
                    source_ids,
                )

                # Batch check existing embedding hashes (topic-scoped)
                existing_hashes = (
                    await batch_check_exists(
                        session,
                        Item,
                        Item.embedding_hash,
                        embedding_hashes_non_null,
                        additional_filters=[Item.topic_id == topic.id],
                    )
                    if embedding_hashes_non_null
                    else set()
                )

                # Process each item with in-memory duplicate checking
                seen_source_ids = set()

                for raw_item, embedding_hash in zip(raw_items, embedding_hashes):
                    # Check for intra-batch duplicate source_id
                    if raw_item.source_id in seen_source_ids:
                        duplicates += 1
                        logger.debug(f"Skipping intra-batch duplicate source_id: {raw_item.source_id}")
                        continue
                    seen_source_ids.add(raw_item.source_id)

                    # Check for duplicate by source_id (in-memory)
                    if raw_item.source_id in existing_source_ids:
                        duplicates += 1
                        continue

                    # Also check by embedding_hash if available
                    if embedding_hash and embedding_hash in existing_hashes:
                        duplicates += 1
                        logger.debug(f"Duplicate found via embedding hash: {raw_item.source_id}")
                        continue

                    # Create new item
                    item = Item(
                        topic_id=topic.id,
                        source_id=raw_item.source_id,
                        author=raw_item.author,
                        text=raw_item.text,
                        url=raw_item.url,
                        created_at=raw_item.created_at,
                        collected_at=datetime.now(UTC),
                        media_urls=raw_item.media_urls if raw_item.media_urls else None,
                        metrics=raw_item.metrics if raw_item.metrics else None,
                        embedding_hash=embedding_hash,
                    )
                    new_items.append(item)

                # 6. Insert new items
                if new_items:
                    session.add_all(new_items)
                    await session.commit()
                    logger.info(f"Inserted {len(new_items)} new items for topic {topic.name}")

                    total_items_collected += len(new_items)
                else:
                    logger.info(f"No new items after deduplication for topic {topic.name}")

                # 7. Update last_collection_timestamp and last_tweet_id
                topic.last_collection_timestamp = end_date

                # Track highest tweet ID
                if raw_items:
                    max_tweet_id = None
                    for raw_item in raw_items:
                        try:
                            current_id = int(raw_item.source_id)
                            if max_tweet_id is None or current_id > max_tweet_id:
                                max_tweet_id = current_id
                        except ValueError:
                            continue

                    if max_tweet_id is not None:
                        topic.last_tweet_id = str(max_tweet_id)
                        logger.info(f"Updated last_tweet_id to: {topic.last_tweet_id}")

                await session.commit()
                await llm_client.close()
                topics_processed += 1

            if not enabled_topics:
                logger.info(f"No enabled topics for user {user_id}")
                return {
                    "status": "success",
                    "message": "No enabled topics",
                    "user_id": user_id,
                    "items_collected": total_items_collected,
                    "topics_processed": topics_processed,
                    "time_window": time_window,
                }

            topic_uuids_for_window = [topic.id for topic in enabled_topics]
            items_result = await session.execute(
                select(Item)
                .where(Item.topic_id.in_(topic_uuids_for_window))
                .where(Item.created_at >= window_start_utc)
                .where(Item.created_at <= window_end_utc)
                .order_by(Item.created_at.desc())
                .limit(1000)
            )
            items_in_window = items_result.scalars().all()

            if not items_in_window:
                logger.info(f"No items found in time window {time_window} for user {user_id}")
                return {
                    "status": "success",
                    "message": "No items in time window",
                    "user_id": user_id,
                    "items_collected": total_items_collected,
                    "topics_processed": topics_processed,
                    "time_window": time_window,
                }

            logger.info(
                f"Chaining to generate_user_digest task with {len(items_in_window)} items in window",
                extra={"time_window": time_window},
            )
            topic_ids = [str(topic.id) for topic in enabled_topics]
            topic_names = {str(topic.id): topic.name for topic in enabled_topics}
            generate_user_digest.delay(
                user_id=user_id,
                topic_ids=topic_ids,
                topic_names=topic_names,
                window_start=window_start_utc.isoformat(),
                window_end=window_end_utc.isoformat(),
            )

            return {
                "status": "success",
                "message": f"Collected {total_items_collected} items from {topics_processed} topics",
                "user_id": user_id,
                "items_collected": total_items_collected,
                "topics_processed": topics_processed,
                "time_window": time_window,
            }

    except Exception as e:
        logger.error(f"Error in collect_user_topics for user {user_id}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
        }


@celery_app.task(bind=True, name="app.workers.tasks.generate_user_digest", max_retries=1)
def generate_user_digest(
    self,
    user_id: str,
    topic_ids: list[str],
    topic_names: dict[str, str],
    window_start: str,
    window_end: str,
):
    """
    Generate a personalized digest for a user from all topics in user.topics.

    Args:
        user_id: UUID of the user
        topic_ids: List of topic UUIDs (strings) for this digest
        topic_names: Mapping of topic_id -> topic_name for display
        window_start: Start of time window (ISO format string)
        window_end: End of time window (ISO format string)

    Workflow:
        1. Parse time window
        2. Query items from all topic_ids in time window
        3. Call LLM to generate personalized digest
        4. Store user-specific digest
        5. Chain to notify_user_digest
    """
    logger.info(
        f"Generating user digest for user {user_id}",
        extra={"window_start": window_start, "window_end": window_end, "topic_count": len(topic_ids)},
    )
    return asyncio.run(_generate_user_digest_async(self, user_id, topic_ids, topic_names, window_start, window_end))


async def _generate_user_digest_async(
    self,
    user_id: str,
    topic_ids: list[str],
    topic_names: dict[str, str],
    window_start: str,
    window_end: str,
):
    """Async implementation of generate_user_digest task.

    Context handoff contract (Task 7):
    - topic_ids: Required list of topic UUID strings
    - topic_names: Required mapping of topic_id -> topic_name
    - window_start/window_end: Required ISO format timestamp strings

    Error semantics (Task 9):
    - Deterministic validation errors return error dicts without retry
    - Transient execution errors are retry-eligible
    """
    from uuid import UUID
    from app.db.session import get_async_session_local

    # Helper for deterministic validation errors (Task 9)
    def _make_validation_error(message: str) -> dict:
        """Create a deterministic error response (no retry)."""
        return {
            "status": "error",
            "message": message,
            "user_id": user_id,
            "_deterministic": True,  # Flag for testing/debugging
        }

    try:
        async with get_async_session_local()() as session:
            # 1. Validate required context parameters (deterministic - no retry)
            if not topic_ids:
                logger.error("topic_ids is required but empty")
                return _make_validation_error("topic_ids required")

            if topic_names is None:
                logger.error("topic_names is required but None")
                return _make_validation_error("topic_names required")

            if not window_start:
                logger.error("window_start is required but empty")
                return _make_validation_error("window_start required")

            if not window_end:
                logger.error("window_end is required but empty")
                return _make_validation_error("window_end required")

            # 2. Parse time window (deterministic - no retry on format errors)
            try:
                window_start_dt = datetime.fromisoformat(window_start)
                window_end_dt = datetime.fromisoformat(window_end)
            except ValueError as e:
                logger.error(f"Invalid ISO timestamp in window parameters: {e}")
                return _make_validation_error(f"Invalid window timestamp format: {e}")

            # 3. Parse topic_ids to UUIDs (deterministic - no retry on format errors)
            try:
                topic_uuids = [UUID(tid) for tid in topic_ids]
            except ValueError as e:
                logger.error(f"Invalid UUID in topic_ids: {e}")
                return _make_validation_error(f"Invalid topic UUID in topic_ids: {e}")

            # 4. Query items for all topics in time window (transient - retry eligible)
            items_result = await session.execute(
                select(Item)
                .where(Item.topic_id.in_(topic_uuids))
                .where(Item.created_at >= window_start_dt)
                .where(Item.created_at <= window_end_dt)
                .order_by(Item.created_at.desc())
            )
            items = items_result.scalars().all()

            # 5. If no items, return early (deterministic - no items found)
            if not items:
                logger.info(f"No items in time window for user {user_id}")
                return {
                    "status": "success",
                    "message": "No items in time window",
                    "user_id": user_id,
                }

            logger.info(f"Found {len(items)} items for user digest")

            # 6. Convert items to dicts for LLM
            items_dict = [
                {
                    "id": str(item.id),
                    "text": item.text,
                    "author": item.author,
                    "url": item.url,
                    "created_at": item.created_at.isoformat(),
                    "metrics": item.metrics or {},
                    "topic_name": topic_names.get(str(item.topic_id), "Unknown"),
                }
                for item in items
            ]

            # 7. Generate digest using LLM (transient - retry eligible)
            embedding_provider = get_embedding_provider()
            llm_client = LLMClient(embedding_provider=embedding_provider)
            digest_result = await llm_client.generate_digest(
                topic="Aggregated Topics",
                items=items_dict,
                time_window_start=window_start_dt,
                time_window_end=window_end_dt,
            )

            # 8. Render markdown
            rendered_content = render_markdown_digest(
                topic_name="User Digest",
                digest_result=digest_result,
                time_window_start=window_start_dt,
                time_window_end=window_end_dt,
            )

            # 9. Create UserDigest record (transient - retry eligible)
            user_digest = UserDigest(
                user_id=user_id,
                topic_ids=[str(tid) for tid in topic_uuids],
                time_window_start=window_start_dt,
                time_window_end=window_end_dt,
                summary_json=digest_result.model_dump(),
                rendered_content=rendered_content,
            )
            session.add(user_digest)
            await session.flush()  # Get the digest ID

            logger.info(
                f"Created user digest {user_digest.id}",
                extra={
                    "user_digest_id": str(user_digest.id),
                    "highlights": len(digest_result.highlights),
                    "items_analyzed": len(items),
                    "topics_included": len(topic_ids),
                },
            )

            await session.commit()
            await llm_client.close()

            # 10. Chain to notify_user_digest
            notify_user_digest.delay(str(user_digest.id))

            # 11. Return result
            return {
                "status": "success",
                "message": "User digest generated",
                "user_id": user_id,
                "user_digest_id": str(user_digest.id),
                "items_analyzed": len(items),
                "topics_included": len(topic_ids),
            }

    except Exception as e:
        logger.error(f"User digest generation failed: {e}", exc_info=True)

        # Task 9: Retry guard - only retry transient execution failures
        # Robustness: Handle cases where self.request or self.max_retries might not be available
        try:
            can_retry = (
                hasattr(self, "request")
                and hasattr(self.request, "retries")
                and hasattr(self, "max_retries")
                and self.request.retries < self.max_retries
            )
        except (AttributeError, TypeError):
            # In tests or unusual contexts, default to no retry
            can_retry = False

        if can_retry:
            countdown = 30  # 30 seconds
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "error", "message": str(e), "user_id": user_id}


@celery_app.task(bind=True, name="app.workers.tasks.notify_user_digest", max_retries=2)
def notify_user_digest(self, user_digest_id: str):
    """
    Send notification for a user-specific digest.

    Args:
        user_digest_id: UUID of the user digest

    Workflow:
        1. Load user digest and user
        2. Determine notification channels from user preferences
        3. Send to enabled channels (feishu/email)
        4. Update delivery status
    """
    logger.info(f"Starting user digest notification for digest {user_digest_id}")
    return asyncio.run(_notify_user_digest_async(self, user_digest_id))


async def _notify_user_digest_async(self, user_digest_id: str):
    """Async implementation of notify_user_digest task.

    Sends notification for a user digest via configured channels (Feishu/Email)
    and creates delivery records for tracking using the shared delivery service.
    """
    from app.db.session import get_async_session_local
    from app.db.models import UserDigest
    from app.services.notifier.delivery import send_digest_to_user
    from app.core.constants import NotificationChannel, DeliveryStatus

    try:
        async with get_async_session_local()() as session:
            # 1. Load UserDigest with User
            result = await session.execute(
                select(UserDigest).options(selectinload(UserDigest.user)).where(UserDigest.id == user_digest_id)
            )
            user_digest = result.scalar_one_or_none()

            if not user_digest:
                logger.error(f"UserDigest {user_digest_id} not found")
                return {"status": "error", "message": "UserDigest not found"}

            user = user_digest.user

            # 2. Determine notification channels from user-level enable flags
            channels = []
            # FEISHU requires both enable flag and webhook URL
            if user.enable_feishu and user.feishu_webhook_url:
                channels.append(NotificationChannel.FEISHU)
            # EMAIL requires both enable flag and email address
            if user.enable_email and user.email:
                channels.append(NotificationChannel.EMAIL)

            if not channels:
                logger.info(f"No notification channels enabled for user {user.id}")
                return {
                    "status": "success",
                    "message": "No channels enabled",
                    "user_digest_id": user_digest_id,
                    "channels": [],
                    "successful": 0,
                    "failed": 0,
                }

            # 3. Use shared service to send notifications (idempotent to prevent duplicates on retry)
            deliveries = await send_digest_to_user(
                user=user,
                channels=channels,
                session=session,
                user_digest=user_digest,
                idempotent=True,
            )

            # 4. Aggregate results
            successful = sum(1 for d in deliveries if d.status == DeliveryStatus.SUCCESS)
            failed = sum(1 for d in deliveries if d.status == DeliveryStatus.FAILED)
            channels_used = [d.channel for d in deliveries if d.status == DeliveryStatus.SUCCESS]

            await session.commit()

            logger.info(
                "User digest notifications completed",
                extra={
                    "user_digest_id": user_digest_id,
                    "user_id": str(user.id),
                    "successful": successful,
                    "failed": failed,
                },
            )

            return {
                "status": "success",
                "message": "User digest notifications sent",
                "user_digest_id": user_digest_id,
                "channels": channels_used,
                "successful": successful,
                "failed": failed,
            }

    except Exception as e:
        logger.error(f"User digest notification task failed: {e}", exc_info=True)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "error", "message": str(e)}


__all__ = [
    "collect_data",
    "generate_digest",
    # User pipeline tasks
    "collect_user_topics",
    "generate_user_digest",
    "notify_user_digest",
]
