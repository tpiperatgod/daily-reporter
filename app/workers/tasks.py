"""Celery tasks for the X-News-Digest pipeline."""

import asyncio
import inspect
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app
from app.core.logging import get_logger
from app.db.models import Topic, Item, Digest, Subscription, User
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

            # Batch check existing source_ids (1 query total)
            existing_source_ids = await batch_check_exists(
                session,
                Item,
                Item.source_id,
                source_ids,
                additional_filters=[Item.topic_id == topic_id],
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
            for raw_item, embedding_hash in zip(raw_items, embedding_hashes):
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

            # 7. Chain to notify task
            notify.delay(str(digest.id))

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
    Send notifications for a digest.

    Args:
        digest_id: UUID of the digest

    Workflow:
        1. Load digest and topic
        2. Query subscriptions for the topic
        3. For each subscription:
           - Create delivery records
           - Send to enabled channels (feishu/email)
           - Update delivery status
        4. Handle partial failures gracefully
    """
    logger.info(f"Starting notifications for digest {digest_id}")

    return asyncio.run(_notify_async(self, digest_id))


async def _notify_async(self, digest_id: str):
    """Async implementation of notify task."""
    from app.db.session import get_async_session_local

    try:
        async with get_async_session_local()() as session:
            # 1. Load digest with topic (eager load to prevent MissingGreenlet)
            digest_result = await session.execute(
                select(Digest).where(Digest.id == digest_id).options(selectinload(Digest.topic))
            )
            digest = digest_result.scalar_one_or_none()

            if not digest:
                logger.error(f"Digest {digest_id} not found")
                return {"status": "error", "message": "Digest not found"}

            topic = digest.topic

            # 2. Query subscriptions
            subs_result = await session.execute(
                select(Subscription, User)
                .join(User, Subscription.user_id == User.id)
                .where(Subscription.topic_id == topic.id)
            )
            subscriptions = subs_result.all()

            if not subscriptions:
                logger.info(f"No subscriptions for topic {topic.name}")
                return {"status": "success", "message": "No subscriptions to notify"}

            logger.info(f"Found {len(subscriptions)} subscriptions")

            # 3. Send notifications using shared delivery service
            from app.services.notifier.delivery import send_digest_to_user
            from app.core.constants import NotificationChannel, DeliveryStatus

            successful = 0
            failed = 0
            deliveries_created = 0

            for subscription, user in subscriptions:
                # Determine channels from subscription settings
                channels = []
                if subscription.enable_feishu:
                    channels.append(NotificationChannel.FEISHU)
                if subscription.enable_email:
                    channels.append(NotificationChannel.EMAIL)

                if not channels:
                    logger.debug(f"No channels enabled for user {user.email}")
                    continue

                # Use shared service to send and track deliveries
                deliveries = await send_digest_to_user(digest=digest, user=user, channels=channels, session=session)

                # Aggregate results
                for delivery in deliveries:
                    deliveries_created += 1
                    if delivery.status == DeliveryStatus.SUCCESS:
                        successful += 1
                    elif delivery.status == DeliveryStatus.FAILED:
                        failed += 1

            await session.commit()

            return {
                "status": "success",
                "message": "Notifications sent",
                "deliveries": deliveries_created,
                "successful": successful,
                "failed": failed,
            }

    except Exception as e:
        logger.error(f"Notification task failed: {e}", exc_info=True)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 60 * (self.request.retries + 1)  # 60s, 120s
            logger.info(f"Retrying in {countdown} seconds...")
            raise self.retry(exc=e, countdown=countdown)

        return {"status": "error", "message": str(e)}


__all__ = ["collect_data", "generate_digest", "notify"]
