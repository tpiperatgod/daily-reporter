"""Regression tests for intra-batch source_id deduplication.

This module tests that duplicate source_ids within a single
collection batch are properly deduplicated before database insert.

The fix uses a seen_source_ids set in app/workers/tasks.py
to track and skip duplicates within a single batch.
"""

import pytest
import pytest_asyncio
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.db.models import Topic, Item
from app.workers.tasks import _collect_data_async
from app.services.provider.base import RawItem


@pytest_asyncio.fixture
async def test_topic(async_session):
    """Create a test topic in database."""
    topic = Topic(
        id=uuid4(),
        name="Dedupe Test Topic",
        query="@test_dedupe",
        # cron_expression removed - topic-scoped scheduling decommissioned
        is_enabled=True,
        last_collection_timestamp=None,
        last_tweet_id=None,
    )
    async_session.add(topic)
    await async_session.commit()
    await async_session.refresh(topic)
    return topic


class TestIntraBatchDuplicateDeduplication:
    """Test intra-batch duplicate source_id handling."""

    @pytest.mark.asyncio
    async def test_intra_batch_duplicate_source_id_dedup(self, async_session, test_topic):
        """Test that duplicate source_ids in a single batch are deduplicated.

        Provider returns 3 items, 2 with same source_id.
        Only 2 items should be stored (1 duplicate skipped).
        No IntegrityError should be raised.
        """
        # Use UUID prefix to avoid conflicts with other tests
        unique_prefix = str(uuid4())[:8]
        mock_items = [
            RawItem(
                source_id=f"{unique_prefix}_100",
                author="testuser",
                text="First unique tweet",
                url="https://x.com/testuser/status/100",
                created_at=datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC),
            ),
            RawItem(  # DUPLICATE source_id
                source_id=f"{unique_prefix}_100",
                author="testuser",
                text="Duplicate tweet (same ID)",
                url="https://x.com/testuser/status/100",
                created_at=datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC),
            ),
            RawItem(
                source_id=f"{unique_prefix}_200",
                author="testuser",
                text="Second unique tweet",
                url="https://x.com/testuser/status/200",
                created_at=datetime(2025, 1, 31, 11, 0, 0, tzinfo=UTC),
            ),
        ]

        # Mock provider to return our test items
        mock_provider = MagicMock()
        mock_provider.fetch = AsyncMock(return_value=mock_items)

        # Mock LLM client
        mock_llm = AsyncMock()
        mock_llm.generate_embedding_hashes_batch = AsyncMock(return_value=["hash100", "hash100", "hash200"])
        mock_llm.close = AsyncMock()

        with patch("app.workers.tasks.get_provider", return_value=mock_provider):
            with patch("app.workers.tasks.get_embedding_provider") as mock_emb:
                mock_emb.return_value = MagicMock()
                with patch("app.workers.tasks.LLMClient", return_value=mock_llm):
                    with patch("app.workers.tasks.generate_digest"):
                        # Run collection - should NOT raise IntegrityError
                        result = await _collect_data_async(
                            None,  # self (task instance)
                            str(test_topic.id),
                        )

                        # Verify successful completion
                        assert result["status"] == "success"
                        # 3 items fetched, 1 duplicate skipped = 2 collected
                        assert result["items_collected"] == 2
                        # Check duplicates_skipped count
                        assert result.get("duplicates_skipped", 0) >= 1

                        # Verify items in database
                        items = await async_session.execute(
                            Item.__table__.select().where(Item.topic_id == test_topic.id)
                        )
                        items_list = items.fetchall()
                        # Only 2 unique items stored
                        assert len(items_list) == 2

                        # Verify the stored source_ids are unique
                        stored_source_ids = {item.source_id for item in items_list}
                        assert stored_source_ids == {
                            f"{unique_prefix}_100",
                            f"{unique_prefix}_200",
                        }

    @pytest.mark.asyncio
    async def test_intra_batch_all_unique_source_ids(self, async_session, test_topic):
        """Control test: all unique source_ids should result in all inserts.

        Provider returns 3 items with unique source_ids.
        All 3 items should be stored.
        """
        # Use UUID prefix to avoid conflicts with other tests
        unique_prefix = str(uuid4())[:8]
        mock_items = [
            RawItem(
                source_id=f"{unique_prefix}_101",
                author="testuser",
                text="First tweet",
                url="https://x.com/testuser/status/101",
                created_at=datetime(2025, 1, 31, 10, 0, 0, tzinfo=UTC),
            ),
            RawItem(
                source_id=f"{unique_prefix}_102",
                author="testuser",
                text="Second tweet",
                url="https://x.com/testuser/status/102",
                created_at=datetime(2025, 1, 31, 11, 0, 0, tzinfo=UTC),
            ),
            RawItem(
                source_id=f"{unique_prefix}_103",
                author="testuser",
                text="Third tweet",
                url="https://x.com/testuser/status/103",
                created_at=datetime(2025, 1, 31, 12, 0, 0, tzinfo=UTC),
            ),
        ]

        # Mock provider to return our test items
        mock_provider = MagicMock()
        mock_provider.fetch = AsyncMock(return_value=mock_items)

        # Mock LLM client with unique hashes for each item
        mock_llm = AsyncMock()
        mock_llm.generate_embedding_hashes_batch = AsyncMock(return_value=["hash101", "hash102", "hash103"])
        mock_llm.close = AsyncMock()

        with patch("app.workers.tasks.get_provider", return_value=mock_provider):
            with patch("app.workers.tasks.get_embedding_provider") as mock_emb:
                mock_emb.return_value = MagicMock()
                with patch("app.workers.tasks.LLMClient", return_value=mock_llm):
                    with patch("app.workers.tasks.generate_digest"):
                        result = await _collect_data_async(
                            None,  # self (task instance)
                            str(test_topic.id),
                        )

                        # Verify all 3 items collected
                        assert result["status"] == "success"
                        assert result["items_collected"] == 3
                        assert result.get("duplicates_skipped", 0) == 0

                        # Verify all 3 items in database
                        items = await async_session.execute(
                            Item.__table__.select().where(Item.topic_id == test_topic.id)
                        )
                        items_list = items.fetchall()
                        assert len(items_list) == 3

                        # Verify all source_ids are present
                        stored_source_ids = {item.source_id for item in items_list}
                        assert stored_source_ids == {
                            f"{unique_prefix}_101",
                            f"{unique_prefix}_102",
                            f"{unique_prefix}_103",
                        }



# Pytest fixtures for async database
@pytest_asyncio.fixture
async def async_session():
    """Create async database session for testing."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
