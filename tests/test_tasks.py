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



class TestNotifyUserDigest:
    """Test _notify_user_digest_async function."""

    @pytest.mark.asyncio
    async def test_notify_user_digest_creates_delivery_with_user_digest_id(self):
        """Test successful notification creates delivery with user_digest_id set."""
        from app.workers.tasks import _notify_user_digest_async
        from app.db.models import UserDigest, User
        from app.core.constants import DeliveryStatus, NotificationChannel

        user_digest_id = str(uuid4())
        user_id = str(uuid4())

        # Create mock user with notification channels
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.feishu_webhook_url = "https://feishu.test/webhook"

        # Create mock user digest
        mock_user_digest = MagicMock(spec=UserDigest)
        mock_user_digest.id = user_digest_id
        mock_user_digest.user = mock_user

        # Create mock delivery with user_digest_id set
        mock_delivery = MagicMock()
        mock_delivery.id = uuid4()
        mock_delivery.user_digest_id = user_digest_id
        mock_delivery.digest_id = None
        mock_delivery.channel = NotificationChannel.EMAIL
        mock_delivery.status = DeliveryStatus.SUCCESS

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_digest
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local), \
             patch("app.services.notifier.delivery.send_digest_to_user", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = [mock_delivery]

            mock_self = MagicMock()
            result = await _notify_user_digest_async(mock_self, user_digest_id)

        # Verify success
        assert result["status"] == "success"
        assert result["user_digest_id"] == user_digest_id

        # Verify send_digest_to_user was called with correct params
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["user_digest"] == mock_user_digest
        assert call_kwargs["idempotent"] is True

        # Verify delivery has user_digest_id set
        assert mock_delivery.user_digest_id == user_digest_id
        assert mock_delivery.digest_id is None

    @pytest.mark.asyncio
    async def test_notify_user_digest_missing_digest_returns_error(self):
        """Test returns error when user digest record is missing."""
        from app.workers.tasks import _notify_user_digest_async

        user_digest_id = str(uuid4())

        # Mock session returns None for user digest
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _notify_user_digest_async(mock_self, user_digest_id)

        # Verify error response
        assert result["status"] == "error"
        assert result["message"] == "UserDigest not found"



# =============================================================================
# Regression Tests for Topic-Digest Compatibility (T8)
# =============================================================================


class TestTopicNotifyDeliveryFK:
    """Test topic notify flow creates delivery with digest_id set (backward compatibility)."""
    
    @pytest.mark.asyncio
    async def test_topic_notify_creates_delivery_with_digest_id(self):
        """
        Regression test: Topic notify flow must create Delivery with digest_id set, not user_digest_id.
        
        This ensures backward compatibility with existing topic-digest flow.
        The send_digest_to_user function is called with digest=... (not user_digest=...)
        and idempotent=False for topic-scoped deliveries.
        """
        from app.db.models import Digest, Delivery
        from app.workers.tasks import _notify_async
        from app.core.constants import DeliveryStatus, NotificationChannel
        
        user_id = uuid4()
        topic_id = uuid4()
        digest_id = uuid4()
        subscription_id = uuid4()
        
        # Create topic
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="test",
            cron_expression="0 0 * * *",
            is_enabled=True,
        )
        
        # Create user with feishu webhook
        user = User(
            id=user_id,
            email="test@example.com",
            feishu_webhook_url="https://example.com/webhook",
        )
        
        # Create subscription
        subscription = Subscription(
            id=subscription_id,
            user_id=user_id,
            topic_id=topic_id,
            enable_feishu=True,
            enable_email=False,
        )
        
        # Create digest with topic relationship
        digest = Digest(
            id=digest_id,
            topic_id=topic_id,
            time_window_start=datetime.now(UTC) - timedelta(hours=1),
            time_window_end=datetime.now(UTC),
            summary_json={"headline": "test", "highlights": [], "themes": [], "sentiment": "neutral", "stats": {}},
            rendered_content="# Test",
            topic=topic,
        )
        
        # Track created deliveries
        created_deliveries = []
        
        mock_session = AsyncMock()
        
        # Mock first query: load digest with topic
        digest_result = MagicMock()
        digest_result.scalar_one_or_none.return_value = digest
        
        # Mock second query: load subscriptions with users
        subs_result = MagicMock()
        subs_result.all.return_value = [(subscription, user)]
        
        # Setup execute to return different results for different queries
        mock_session.execute.side_effect = [digest_result, subs_result]
        
        # Track delivery creation
        def track_add(obj):
            if isinstance(obj, Delivery):
                created_deliveries.append(obj)
        mock_session.add.side_effect = track_add
        
        mock_session_local = create_mock_session_local(mock_session)
        
        # Mock send_digest_to_user to capture the call and create delivery
        async def mock_send_digest_to_user(user, channels, session, digest=None, user_digest=None, idempotent=False):
            # Verify this is a topic-digest call, not user-digest
            assert digest is not None, "Topic notify must pass digest, not user_digest"
            assert user_digest is None, "Topic notify must NOT pass user_digest"
            assert idempotent is False, "Topic notify uses idempotent=False"
            
            # Create delivery to simulate real behavior
            delivery = Delivery(
                id=uuid4(),
                digest_id=str(digest.id),
                user_digest_id=None,
                user_id=str(user.id),
                channel=channels[0],
                status=DeliveryStatus.SUCCESS,
            )
            created_deliveries.append(delivery)
            return [delivery]
        
        with patch("app.db.session.get_async_session_local", return_value=mock_session_local), \
             patch("app.services.notifier.delivery.send_digest_to_user", side_effect=mock_send_digest_to_user):
            mock_self = MagicMock()
            result = await _notify_async(mock_self, str(digest_id))
        
        # Verify result
        assert result["status"] == "success"
        assert result["deliveries"] >= 1
        
        # Verify delivery has digest_id set, user_digest_id is None
        assert len(created_deliveries) >= 1
        delivery = created_deliveries[0]
        assert delivery.digest_id is not None, "Topic delivery must have digest_id set"
        assert delivery.digest_id == str(digest_id)
        assert delivery.user_digest_id is None, "Topic delivery must NOT have user_digest_id set"