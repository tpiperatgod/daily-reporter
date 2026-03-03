"""Celery tasks for the X-News-Digest pipeline."""

import asyncio
import inspect
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.db.models import Topic, Item, Digest, User, UserDigest
from app.services.provider.factory import get_provider
from app.services.llm.client import LLMClient
from app.services.embedding.factory import get_embedding_provider
from app.services.notifier.renderer import render_markdown_digest

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
    Generate a digest from collected items.

    Args:
        topic_id: UUID of the topic
        window_start: Start of time window (ISO format string)
        window_end: End of time window (ISO format string)

    Workflow:
        1. Load topic
        2. Return early if digest already exists for this window (dedup)
        3. Fetch items by tweet created_at in time window
        4. Call LLM to generate digest
        5. Render markdown
        6. Insert digest record
        7. Chain to notify task
    """
    logger.info(
        f"Generating digest for topic {topic_id}",
        extra={"window_start": window_start, "window_end": window_end},
    )

    return asyncio.run(_generate_digest_async(self, topic_id, window_start, window_end))


async def _generate_digest_async(self, topic_id: str, window_start: str, window_end: str):
    """Async implementation of generate_digest task."""
    from app.db.session import get_async_session_local

    try:
        async with get_async_session_local()() as session:
            # 1. Load topic
            topic_result = await session.execute(select(Topic).where(Topic.id == topic_id))
            topic = topic_result.scalar_one_or_none()

            if not topic:
                logger.error(f"Topic {topic_id} not found")
                return {"status": "error", "message": "Topic not found"}

            # Parse time windows
            start_dt = datetime.fromisoformat(window_start)
            end_dt = datetime.fromisoformat(window_end)

            # 2. Check if a digest already exists for this exact time window (dedup)
            existing_result = await session.execute(
                select(Digest).where(
                    and_(
                        Digest.topic_id == topic_id,
                        Digest.time_window_start == start_dt,
                        Digest.time_window_end == end_dt,
                    )
                )
            )
            existing_digest = existing_result.scalar_one_or_none()
            if existing_digest:
                logger.info(f"Digest already exists for this window, reusing {existing_digest.id}")
                return {
                    "status": "already_exists",
                    "digest_id": str(existing_digest.id),
                    "message": "Digest already exists for this time window",
                }

            # 3. Fetch items in time window (based on tweet created_at, not collected_at)
            items_result = await session.execute(
                select(Item)
                .where(
                    and_(
                        Item.topic_id == topic_id,
                        Item.created_at >= start_dt,
                        Item.created_at <= end_dt,
                    )
                )
                .order_by(Item.created_at.desc())
            )
            items = items_result.scalars().all()

            if not items:
                logger.info("No items to digest")
                return {"status": "skipped", "message": "No items to digest"}

            logger.info(f"Found {len(items)} items for digest")

            # Convert items to dicts for LLM
            items_dict = [
                {
                    "id": str(item.id),
                    "text": item.text,
                    "author": item.author,
                    "url": item.url,
                    "created_at": item.created_at.isoformat(),
                    "metrics": item.metrics or {},
                }
                for item in items
            ]

            # 4. Generate digest with LLM
            embedding_provider = get_embedding_provider()
            llm_client = LLMClient(embedding_provider=embedding_provider)
            digest_result = await llm_client.generate_digest(
                topic=topic.name,
                items=items_dict,
                time_window_start=start_dt,
                time_window_end=end_dt,
            )

            # 5. Render markdown
            rendered_content = render_markdown_digest(
                topic_name=topic.name,
                digest_result=digest_result,
                time_window_start=start_dt,
                time_window_end=end_dt,
            )

            # 6. Insert digest record
            digest = Digest(
                topic_id=topic_id,
                time_window_start=start_dt,
                time_window_end=end_dt,
                summary_json=digest_result.dict(),
                rendered_content=rendered_content,
            )
            session.add(digest)
            await session.flush()  # Get the digest ID

            logger.info(
                f"Created digest {digest.id}",
                extra={
                    "digest_id": str(digest.id),
                    "highlights": len(digest_result.highlights),
                },
            )

            await session.commit()
            await llm_client.close()


            return {
                "status": "success",
                "message": "Digest generated successfully",
                "digest_id": str(digest.id),
                "highlights": len(digest_result.highlights),
            }

    except Exception as e:
        logger.error(f"Digest generation failed: {e}", exc_info=True)

        # Retry once
        if self.request.retries < self.max_retries:
            countdown = 30  # 30 seconds
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "error", "message": str(e)}


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


@celery_app.task(bind=True, name="app.workers.tasks.collect_user_topics", max_retries=3)
def collect_user_topics(self, user_id: str):
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
    logger.info(f"Starting user topic collection for user {user_id}")
    return asyncio.run(_collect_user_topics_async(self, user_id))


async def _collect_user_topics_async(self, user_id: str):
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

            topics_result = await session.execute(
                select(Topic).where(Topic.id.in_(topic_uuids))
            )
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

            # Track aggregated results
            total_items_collected = 0
            all_new_items = []
            topics_processed = 0
            min_item_created_at = None
            max_item_created_at = None

            # Get provider once (shared across topics)
            provider = get_provider()

            # 4. Process each topic
            for topic in topics:
                if not topic.is_enabled:
                    logger.info(f"Topic {topic.name} is disabled, skipping")
                    continue

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

                    # Track for aggregated time window
                    for item in new_items:
                        if min_item_created_at is None or item.created_at < min_item_created_at:
                            min_item_created_at = item.created_at
                        if max_item_created_at is None or item.created_at > max_item_created_at:
                            max_item_created_at = item.created_at

                    all_new_items.extend(new_items)
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

            # 8. Chain to generate_user_digest if we have new items
            if all_new_items:
                logger.info("Chaining to generate_user_digest task")
                generate_user_digest.delay(
                    user_id=user_id,
                    window_start=min_item_created_at.isoformat(),
                    window_end=max_item_created_at.isoformat(),
                )

            return {
                "status": "success",
                "message": f"Collected {total_items_collected} items from {topics_processed} topics",
                "user_id": user_id,
                "items_collected": total_items_collected,
                "topics_processed": topics_processed,
            }

    except Exception as e:
        logger.error(f"Error in collect_user_topics for user {user_id}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
        }

@celery_app.task(bind=True, name="app.workers.tasks.generate_user_digest", max_retries=1)
def generate_user_digest(self, user_id: str, window_start: str, window_end: str):
    """
    Generate a personalized digest for a user from all topics in user.topics.

    Args:
        user_id: UUID of the user
        window_start: Start of time window (ISO format string)
        window_end: End of time window (ISO format string)

    Workflow:
        1. Load user and their topics list
        2. Fetch items from all topics in time window
        3. Call LLM to generate personalized digest
        4. Store user-specific digest
        5. Chain to notify_user_digest
    """
    logger.info(
        f"Generating user digest for user {user_id}",
        extra={"window_start": window_start, "window_end": window_end},
    )
    return asyncio.run(_generate_user_digest_async(self, user_id, window_start, window_end))


async def _generate_user_digest_async(self, user_id: str, window_start: str, window_end: str):
    """Async implementation of generate_user_digest task."""
    from uuid import UUID
    from app.db.session import get_async_session_local

    try:
        async with get_async_session_local()() as session:
            # 1. Parse time window
            window_start_dt = datetime.fromisoformat(window_start)
            window_end_dt = datetime.fromisoformat(window_end)

            # 2. Load user (no eager loading needed - topics is JSONB column)
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found")
                return {"status": "error", "message": "User not found", "user_id": user_id}

            # 3. Handle empty topics list
            if not user.topics:
                logger.info(f"User {user_id} has no topics")
                return {
                    "status": "success",
                    "message": "User has no topics configured",
                    "user_id": user_id,
                }

            # 4. Load Topic objects from user.topics UUID strings
            try:
                topic_uuids = [UUID(tid) for tid in user.topics]
            except ValueError as e:
                logger.error(f"Invalid UUID in user.topics for user {user_id}: {e}")
                return {
                    "status": "error",
                    "message": f"Invalid topic UUID in user configuration: {e}",
                    "user_id": user_id,
                }

            topics_result = await session.execute(
                select(Topic).where(Topic.id.in_(topic_uuids))
            )
            topics = topics_result.scalars().all()

            if not topics:
                logger.info(f"No valid topics found for user {user_id}")
                return {
                    "status": "success",
                    "message": "No valid topics found",
                    "user_id": user_id,
                }

            # 5. Get topic_ids and topic_names from loaded topics
            topic_ids = [topic.id for topic in topics]
            topic_names = {topic.id: topic.name for topic in topics}

            # 6. Query items for all topics in time window
            items_result = await session.execute(
                select(Item)
                .where(Item.topic_id.in_(topic_ids))
                .where(Item.created_at >= window_start_dt)
                .where(Item.created_at <= window_end_dt)
                .order_by(Item.created_at.desc())
            )
            items = items_result.scalars().all()

            # 7. If no items, return early
            if not items:
                logger.info(f"No items in time window for user {user_id}")
                return {
                    "status": "success",
                    "message": "No items in time window",
                    "user_id": user_id,
                }

            logger.info(f"Found {len(items)} items for user digest")

            # 8. Convert items to dicts for LLM
            items_dict = [
                {
                    "id": str(item.id),
                    "text": item.text,
                    "author": item.author,
                    "url": item.url,
                    "created_at": item.created_at.isoformat(),
                    "metrics": item.metrics or {},
                    "topic_name": topic_names.get(item.topic_id, "Unknown"),
                }
                for item in items
            ]

            # 9. Generate digest using LLM
            embedding_provider = get_embedding_provider()
            llm_client = LLMClient(embedding_provider=embedding_provider)
            digest_result = await llm_client.generate_digest(
                topic="Aggregated Topics",
                items=items_dict,
                time_window_start=window_start_dt,
                time_window_end=window_end_dt,
            )

            # 10. Render markdown
            rendered_content = render_markdown_digest(
                topic_name="User Digest",
                digest_result=digest_result,
                time_window_start=window_start_dt,
                time_window_end=window_end_dt,
            )

            # 11. Create UserDigest record
            user_digest = UserDigest(
                user_id=user_id,
                topic_ids=[str(tid) for tid in topic_ids],
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

            # 12. Chain to notify_user_digest
            notify_user_digest.delay(str(user_digest.id))

            # 13. Return result
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

        # Retry once
        if self.request.retries < self.max_retries:
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
