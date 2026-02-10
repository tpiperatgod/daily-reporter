"""
Integration tests for MockAdapter incremental collection workflow.
Tests the full pipeline: factory → provider → database → incremental collection.
"""
import pytest
import os
from datetime import datetime, timedelta
from sqlalchemy import select
from app.services.provider.factory import get_provider
from app.db.models import Topic, Item
from app.core.config import settings


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set environment to use MockAdapter."""
    monkeypatch.setenv("X_PROVIDER", "MOCK")
    # Force reload of settings
    from app.core.config import settings
    settings.X_PROVIDER = "MOCK"


class TestMockProviderFactory:
    """Test that factory returns MockAdapter correctly."""

    @pytest.mark.asyncio
    async def test_factory_returns_mock_adapter(self):
        """Verify factory returns MockAdapter when X_PROVIDER=MOCK."""
        provider = get_provider()

        # Check the class name
        assert provider.__class__.__name__ == "MockAdapter"


class TestMockIncrementalCollection:
    """Test incremental collection workflow with MockAdapter."""

    @pytest.mark.asyncio
    async def test_first_collection_updates_last_tweet_id(self, async_session):
        """Verify first collection sets last_tweet_id."""
        # Create test topic inline
        topic = Topic(
            name="Test AI Topic for Mock",
            query="AI and machine learning",
            cron_expression="0 9 * * *",
            is_enabled=True,
            last_tweet_id=None
        )
        async_session.add(topic)
        await async_session.commit()
        await async_session.refresh(topic)

        provider = get_provider()

        # First collection
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        items = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        assert len(items) > 0

        # Simulate what the worker does: update last_tweet_id
        max_tweet_id = None
        for item in items:
            try:
                current_id = int(item.source_id)
                if max_tweet_id is None or current_id > max_tweet_id:
                    max_tweet_id = current_id
            except ValueError:
                continue

        assert max_tweet_id is not None

        # Update topic
        topic.last_tweet_id = str(max_tweet_id)
        await async_session.commit()
        await async_session.refresh(topic)

        # Verify last_tweet_id is set
        assert topic.last_tweet_id == str(max_tweet_id)
        assert int(topic.last_tweet_id) >= 1000  # Mock IDs start at 1000

    @pytest.mark.asyncio
    async def test_second_collection_uses_since_id(self, async_session):
        """Verify second collection passes since_id to provider."""
        # Create test topic
        topic = Topic(
            name="Test AI Topic for Mock 2",
            query="AI and machine learning",
            cron_expression="0 9 * * *",
            is_enabled=True,
            last_tweet_id=None
        )
        async_session.add(topic)
        await async_session.commit()
        await async_session.refresh(topic)

        provider = get_provider()

        # First collection
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        items_first = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        # Update last_tweet_id
        max_tweet_id_first = max(int(item.source_id) for item in items_first)
        topic.last_tweet_id = str(max_tweet_id_first)
        await async_session.commit()

        # Second collection with since_id
        items_second = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5,
            since_id=topic.last_tweet_id
        )

        # All items in second collection should have ID > last_tweet_id
        for item in items_second:
            assert int(item.source_id) > int(topic.last_tweet_id)

    @pytest.mark.asyncio
    async def test_last_tweet_id_increases(self, async_session):
        """Verify last_tweet_id increases after each collection."""
        # Create test topic
        topic = Topic(
            name="Test AI Topic for Mock 3",
            query="AI and machine learning",
            cron_expression="0 9 * * *",
            is_enabled=True,
            last_tweet_id=None
        )
        async_session.add(topic)
        await async_session.commit()
        await async_session.refresh(topic)

        provider = get_provider()

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        # Collection 1
        items_1 = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )
        last_id_1 = max(int(item.source_id) for item in items_1)
        topic.last_tweet_id = str(last_id_1)
        await async_session.commit()

        # Collection 2
        items_2 = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5,
            since_id=topic.last_tweet_id
        )

        if len(items_2) > 0:  # Only if there are more items
            last_id_2 = max(int(item.source_id) for item in items_2)
            assert last_id_2 > last_id_1

            # Update and verify
            topic.last_tweet_id = str(last_id_2)
            await async_session.commit()
            await async_session.refresh(topic)

            assert int(topic.last_tweet_id) == last_id_2
            assert int(topic.last_tweet_id) > last_id_1

    @pytest.mark.asyncio
    async def test_no_duplicates_across_collections(self, async_session):
        """Verify no duplicate source_ids in database after multiple collections."""
        # Create test topic
        topic = Topic(
            name="Test AI Topic for Mock 4",
            query="AI and machine learning",
            cron_expression="0 9 * * *",
            is_enabled=True,
            last_tweet_id=None
        )
        async_session.add(topic)
        await async_session.commit()
        await async_session.refresh(topic)

        provider = get_provider()

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        all_source_ids = set()

        # Collection 1
        items_1 = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        for item in items_1:
            # Create Item in database
            db_item = Item(
                topic_id=topic.id,
                source_id=item.source_id,
                author=item.author,
                text=item.text,
                url=item.url,
                created_at=item.created_at,
                media_urls=item.media_urls,
                metrics=item.metrics,
                embedding_hash=None  # Simplified for test
            )
            async_session.add(db_item)
            all_source_ids.add(item.source_id)

        await async_session.commit()

        # Update last_tweet_id
        last_id_1 = max(int(item.source_id) for item in items_1)
        topic.last_tweet_id = str(last_id_1)
        await async_session.commit()

        # Collection 2 with since_id
        items_2 = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=5,
            since_id=topic.last_tweet_id
        )

        # Verify no overlapping source_ids
        new_source_ids = {item.source_id for item in items_2}
        overlap = all_source_ids.intersection(new_source_ids)
        assert len(overlap) == 0, f"Found duplicate source_ids: {overlap}"

        # Add second batch to database
        for item in items_2:
            db_item = Item(
                topic_id=topic.id,
                source_id=item.source_id,
                author=item.author,
                text=item.text,
                url=item.url,
                created_at=item.created_at,
                media_urls=item.media_urls,
                metrics=item.metrics,
                embedding_hash=None
            )
            async_session.add(db_item)
            all_source_ids.add(item.source_id)

        await async_session.commit()

        # Query database to verify uniqueness
        result = await async_session.execute(
            select(Item.source_id).where(Item.topic_id == topic.id)
        )
        db_source_ids = [row[0] for row in result.fetchall()]

        # Check for duplicates in database
        assert len(db_source_ids) == len(set(db_source_ids)), \
            "Found duplicate source_ids in database"

    @pytest.mark.asyncio
    async def test_running_out_of_data(self, async_session):
        """Verify graceful handling when since_id exceeds all available data."""
        # Create test topic
        topic = Topic(
            name="Test AI Topic for Mock 5",
            query="AI and machine learning",
            cron_expression="0 9 * * *",
            is_enabled=True,
            last_tweet_id="9999999"  # Start with very high ID
        )
        async_session.add(topic)
        await async_session.commit()
        await async_session.refresh(topic)

        provider = get_provider()

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        # Attempt to fetch with high since_id
        items = await provider.fetch(
            query=topic.query,
            start_date=start_date,
            end_date=end_date,
            max_items=10,
            since_id=topic.last_tweet_id
        )

        # Should return empty list without crashing
        assert len(items) == 0
