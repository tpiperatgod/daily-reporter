"""Tests for Celery tasks."""

import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

from app.db.models import Topic, Item, User, Subscription
from app.workers.tasks import _collect_user_topics_async


@dataclass
class MockRawItem:
    """Mock raw item from provider."""
    source_id: str
    author: str
    text: str
    url: str
    created_at: datetime
    media_urls: list = None
    metrics: dict = None


class AsyncContextManagerMock:
    """A proper async context manager mock."""
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def create_mock_session_local(mock_session):
    """Create a mock for get_async_session_local that returns an async context manager.
    
    The chain is:
    get_async_session_local() -> callable
    callable() -> async context manager
    async context manager.__aenter__() -> session
    """
    # Create an async context manager
    async_context_manager = AsyncContextManagerMock(mock_session)
    
    # Create a callable that returns the async context manager
    callable_mock = MagicMock(return_value=async_context_manager)
    
    return callable_mock


class TestCollectUserTopics:
    """Test _collect_user_topics_async function."""

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        """Test returns error when user not found."""
        user_id = str(uuid4())

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "error"
        assert result["message"] == "User not found"

    @pytest.mark.asyncio
    async def test_no_subscriptions(self):
        """Test returns success when user has no subscriptions."""
        user_id = str(uuid4())
        user = User(id=user_id, email="test@example.com", subscriptions=[])

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "success"
        assert result["message"] == "No subscriptions"
        assert result["items_collected"] == 0

    @pytest.mark.asyncio
    async def test_skip_disabled_topic(self):
        """Test skips disabled topics."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create disabled topic
        topic = Topic(
            id=topic_id,
            name="Disabled Topic",
            query="@test",
            cron_expression="0 0 * * *",
            is_enabled=False,
        )
        subscription = Subscription(id=uuid4(), user_id=user_id, topic_id=topic_id, topic=topic)
        user = User(id=user_id, email="test@example.com", subscriptions=[subscription])

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "success"
        assert result["topics_processed"] == 0

    @pytest.mark.asyncio
    async def test_successful_collection_with_new_items(self):
        """Test successful collection chains to generate_user_digest."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create enabled topic
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            cron_expression="0 0 * * *",
            is_enabled=True,
            last_collection_timestamp=None,
            last_tweet_id=None,
        )
        subscription = Subscription(id=uuid4(), user_id=user_id, topic_id=topic_id, topic=topic)
        user = User(id=user_id, email="test@example.com", subscriptions=[subscription])

        # Mock raw items
        base_time = datetime.now(UTC)
        raw_items = [
            MockRawItem(
                source_id="100",
                author="testuser",
                text="Test tweet",
                url="https://x.com/status/100",
                created_at=base_time,
            )
        ]

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider - patch where it's used, not where it's defined
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=raw_items)

        # Mock LLM client
        mock_llm_client = AsyncMock()
        mock_llm_client.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1"])
        mock_llm_client.close = AsyncMock()

        # Mock embedding provider
        mock_embedding_provider = AsyncMock()

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local), \
             patch("app.workers.tasks.get_provider", return_value=mock_provider), \
             patch("app.workers.tasks.LLMClient", return_value=mock_llm_client), \
             patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider), \
             patch("app.db.utils.batch_check_exists", return_value=set()), \
             patch("app.workers.tasks.generate_user_digest") as mock_digest:

            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "success"
        assert result["items_collected"] == 1
        assert result["topics_processed"] == 1
        mock_digest.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_new_items_does_not_chain(self):
        """Test that no new items doesn't chain to generate_user_digest."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create enabled topic
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            cron_expression="0 0 * * *",
            is_enabled=True,
            last_collection_timestamp=None,
            last_tweet_id=None,
        )
        subscription = Subscription(id=uuid4(), user_id=user_id, topic_id=topic_id, topic=topic)
        user = User(id=user_id, email="test@example.com", subscriptions=[subscription])

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider returns no items
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=[])

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local), \
             patch("app.workers.tasks.get_provider", return_value=mock_provider), \
             patch("app.workers.tasks.generate_user_digest") as mock_digest:

            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "success"
        assert result["items_collected"] == 0
        mock_digest.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_since_id_when_available(self):
        """Test that since_id is used when topic has last_tweet_id."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create topic with last_tweet_id
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            cron_expression="0 0 * * *",
            is_enabled=True,
            last_collection_timestamp=datetime.now(UTC) - timedelta(hours=1),
            last_tweet_id="999",
        )
        subscription = Subscription(id=uuid4(), user_id=user_id, topic_id=topic_id, topic=topic)
        user = User(id=user_id, email="test@example.com", subscriptions=[subscription])

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=[])
        # Add signature to support since_id check
        import inspect
        sig = inspect.signature(lambda query, start_date, end_date, max_items, since_id=None: None)
        mock_provider.fetch.__signature__ = sig

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local), \
             patch("app.workers.tasks.get_provider", return_value=mock_provider):

            mock_self = MagicMock()
            await _collect_user_topics_async(mock_self, user_id)

        # Verify since_id was passed
        mock_provider.fetch.assert_called_once()
        call_kwargs = mock_provider.fetch.call_args.kwargs
        assert "since_id" in call_kwargs
        assert call_kwargs["since_id"] == "999"


class TestCollectUserTopicsSync:
    """Test sync collect_user_topics task wrapper."""

    def test_sync_wrapper_calls_async(self):
        """Test that sync wrapper calls async implementation."""
        user_id = str(uuid4())

        with patch("app.workers.tasks.asyncio.run") as mock_run:
            mock_run.return_value = {"status": "success"}

            # Use __wrapped__ to get the original function without Celery decorator
            from app.workers.celery_app import celery_app
            task = celery_app.tasks["app.workers.tasks.collect_user_topics"]
            result = task.__wrapped__(user_id)

            mock_run.assert_called_once()
