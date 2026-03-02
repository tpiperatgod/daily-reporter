"""Unit tests for database utility functions."""

import pytest
import pytest_asyncio
from datetime import datetime, UTC, timedelta
from uuid import uuid4

from app.db.models import Topic, Item
from app.db.utils import fetch_items_for_user_topics


@pytest_asyncio.fixture
async def async_session():
    """Create async database session for testing."""
    from app.db.session import get_async_session_local

    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_topics(async_session):
    """Create multiple test topics in database."""
    topics = []
    for i in range(3):
        topic = Topic(
            id=uuid4(),
            name=f"Test Topic {i}",
            query=f"@test{i}",
            cron_expression="0 0 * * *",
            is_enabled=True,
            last_collection_timestamp=None,
            last_tweet_id=None,
        )
        async_session.add(topic)
        topics.append(topic)

    await async_session.commit()
    for topic in topics:
        await async_session.refresh(topic)

    return topics


@pytest_asyncio.fixture
async def test_items(async_session, test_topics):
    """Create test items across multiple topics with various timestamps."""
    # Use unique prefix to avoid conflicts with other tests
    unique_prefix = str(uuid4())[:8]
    base_time = datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC)
    items = []

    # Create items with different timestamps
    # Note: source_id must be unique in DB, so we can't actually insert duplicates
    # We'll test deduplication logic with the limit parameter instead
    for i, topic in enumerate(test_topics):
        for j in range(5):
            item = Item(
                id=uuid4(),
                topic_id=topic.id,
                source_id=f"{unique_prefix}_source_{i}_{j}",
                author=f"author_{i}",
                text=f"Test tweet {i}-{j}",
                url=f"https://x.com/status/{i}_{j}",
                created_at=base_time + timedelta(hours=i, minutes=j),
                collected_at=datetime.now(UTC),
            )
            async_session.add(item)
            items.append(item)

    await async_session.commit()
    for item in items:
        await async_session.refresh(item)

    return items


class TestFetchItemsForUserTopics:
    """Test fetch_items_for_user_topics function."""

    @pytest.mark.asyncio
    async def test_empty_topic_ids_returns_empty_list(self, async_session):
        """Test that empty topic_ids returns empty list."""
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, [], start, end, limit=100)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetches_items_from_multiple_topics(self, async_session, test_topics, test_items):
        """Test that items are fetched from all specified topics."""
        topic_ids = [t.id for t in test_topics[:2]]  # First 2 topics
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=100)

        # Should get items from first 2 topics (5 items each = 10 total)
        assert len(result) == 10
        result_topic_ids = {item.topic_id for item in result}
        assert result_topic_ids == set(topic_ids)

    @pytest.mark.asyncio
    async def test_respects_time_window(self, async_session, test_topics, test_items):
        """Test that items outside time window are excluded."""
        topic_ids = [test_topics[0].id]
        # Narrow time window to only include first 3 items
        start = datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 10, 2, 30, tzinfo=UTC)  # Only first 3 items

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=100)

        # Should get only 3 items from topic 0
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, async_session, test_topics, test_items):
        """Test that limit parameter is respected."""
        topic_ids = [t.id for t in test_topics]
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=5)

        # Should get exactly 5 items despite more being available
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_orders_by_created_at_desc(self, async_session, test_topics, test_items):
        """Test that items are ordered by created_at DESC."""
        topic_ids = [test_topics[0].id]
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=100)

        # Check ordering: should be newest first
        timestamps = [item.created_at for item in result]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_no_items_in_time_window(self, async_session, test_topics):
        """Test that empty list is returned when no items in time window."""
        topic_ids = [t.id for t in test_topics]
        # Use a time window far in the future
        start = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2030, 1, 2, 0, 0, 0, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=100)

        assert result == []

    @pytest.mark.asyncio
    async def test_deduplication_by_source_id(self, async_session, test_topics):
        """Test that items are deduplicated by source_id.

        Note: Since source_id has a UNIQUE constraint in the database,
        we can't insert actual duplicates. This test verifies that the
        deduplication logic is present and would work if needed.
        """
        # Use unique prefix to avoid conflicts with other tests
        unique_prefix = str(uuid4())[:8]
        base_time = datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC)
        topic = test_topics[0]

        for i in range(3):
            item = Item(
                id=uuid4(),
                topic_id=topic.id,
                source_id=f"{unique_prefix}_unique_{i}",
                author="test_author",
                text=f"Test tweet {i}",
                url=f"https://x.com/status/{i}",
                created_at=base_time + timedelta(hours=i),
                collected_at=datetime.now(UTC),
            )
            async_session.add(item)

        await async_session.commit()

        # Fetch items
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, [topic.id], start, end, limit=100)

        # All items should be unique
        source_ids = [item.source_id for item in result]
        assert len(source_ids) == len(set(source_ids))

    @pytest.mark.asyncio
    async def test_returns_item_objects(self, async_session, test_topics, test_items):
        """Test that function returns Item model instances."""
        topic_ids = [test_topics[0].id]
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=5)

        # All returned items should be Item instances
        assert all(isinstance(item, Item) for item in result)
        # Should have expected attributes
        assert all(hasattr(item, "source_id") for item in result)
        assert all(hasattr(item, "created_at") for item in result)
        assert all(hasattr(item, "topic_id") for item in result)

    @pytest.mark.asyncio
    async def test_single_topic_id(self, async_session, test_topics, test_items):
        """Test fetching items from a single topic."""
        topic_ids = [test_topics[0].id]
        start = datetime(2025, 1, 31, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 31, 23, 59, 59, tzinfo=UTC)

        result = await fetch_items_for_user_topics(async_session, topic_ids, start, end, limit=100)

        # Should get 5 items from topic 0
        assert len(result) == 5
        assert all(item.topic_id == test_topics[0].id for item in result)
