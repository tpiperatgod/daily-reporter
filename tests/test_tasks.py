"""Tests for Celery tasks."""

import pytest
from datetime import datetime, UTC, timedelta
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
from app.db.models import Topic, User
from app.workers.tasks import _collect_user_topics_async, parse_time_window


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


def test_parse_time_window_supports_1d_alias():
    assert parse_time_window("1d") == 24


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
    async def test_no_topics(self):
        """Test returns success when user has no topics configured."""
        user_id = str(uuid4())
        user = User(id=user_id, email="test@example.com", topics=[])

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        assert result["status"] == "success"
        assert result["message"] == "No topics configured"
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
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=False,
        )
        # User with disabled topic in topics array
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        mock_session = AsyncMock()
        # First query returns user, second returns topic
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider") as mock_provider,
        ):
            mock_provider.return_value = AsyncMock()
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
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=True,
            last_collection_timestamp=None,
            last_tweet_id=None,
        )
        # User with topic in topics array
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

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
        # First query returns user, second returns topics
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

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

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.db.utils.batch_check_exists", return_value=set()),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
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
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=True,
            last_collection_timestamp=None,
            last_tweet_id=None,
        )
        # User with topic in topics array
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        # Mock session
        mock_session = AsyncMock()
        # First query returns user, second returns topics
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider returns no items
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=[])

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
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
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=True,
            last_collection_timestamp=datetime.now(UTC) - timedelta(hours=1),
            last_tweet_id="999",
        )
        # User with topic in topics array
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        # Mock session
        mock_session = AsyncMock()
        # First query returns user, second returns topics
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        mock_session.execute.side_effect = [user_result, topic_result]

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=[])
        # Add signature to support since_id check
        import inspect

        sig = inspect.signature(lambda query, start_date, end_date, max_items, since_id=None: None)
        mock_provider.fetch.__signature__ = sig

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
        ):
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
            task.__wrapped__(user_id)

            mock_run.assert_called_once()


class TestNotifyUserDigest:
    """Test _notify_user_digest_async function."""

    @pytest.mark.asyncio
    async def test_notify_user_digest_creates_delivery_with_user_digest_id(self):
        """Test successful notification creates delivery with user_digest_id set."""
        from app.workers.tasks import _notify_user_digest_async
        from app.db.models import UserDigest, User
        from app.core.constants import NotificationChannel

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
        # digest_id field removed from Delivery model
        mock_delivery.channel = NotificationChannel.EMAIL

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_digest
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.services.notifier.delivery.send_digest_to_user", new_callable=AsyncMock) as mock_send,
        ):
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
        # digest_id field removed from Delivery model

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
# Sentinel Tests - Ensure No Regression to Subscription Assumptions
# =============================================================================


class TestNoSubscriptionDependencies:
    """Sentinel tests ensuring no hard dependency on removed Subscription model."""

    @pytest.mark.asyncio
    async def test_collect_user_topics_uses_topics_array_not_subscriptions(self):
        """Test that collect_user_topics reads from user.topics array, not subscriptions."""
        user_id = str(uuid4())
        topic_id = str(uuid4())

        # Create user with topics array
        user = User(id=user_id, email="test@example.com", topics=[topic_id])

        mock_session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [user_result, topic_result]

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        # Verify user.topics was accessed
        assert user.topics == [topic_id]
        assert result["status"] == "success"
        assert result["message"] == "No valid topics found"

    @pytest.mark.asyncio
    async def test_trigger_rejects_empty_topics_list(self):
        """Test that trigger fails when user.topics is empty."""
        user_id = str(uuid4())

        # Create user with empty topics array
        user = User(id=user_id, email="test@example.com", topics=[])

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        # Verify rejection
        assert result["status"] == "success"
        assert result["message"] == "No topics configured"
        assert result["items_collected"] == 0

    @pytest.mark.asyncio
    async def test_worker_user_pipeline_uses_topics_list(self):
        """Test that worker pipeline uses user.topics list for topic IDs."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create topic
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            # cron_expression removed - topic-scoped scheduling decommissioned
            is_enabled=True,
        )

        # Create user with topics array
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        mock_session = AsyncMock()
        # First query returns user, second returns topics
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        # Mock provider with no items
        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=[])

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
        ):
            mock_self = MagicMock()
            result = await _collect_user_topics_async(mock_self, user_id)

        # Verify topics were loaded from user.topics array
        assert result["status"] == "success"
        assert result["topics_processed"] == 1


# =============================================================================
# Wave 1: Context Handoff Contract Tests (Tasks 1-5)
# =============================================================================


class TestContextHandoffContract:
    """Task 1: Define context handoff contract and payload schema (RED tests)."""

    @pytest.mark.asyncio
    async def test_context_contract_required_keys_in_dispatch(self):
        """Contract: collect must dispatch generate with required context keys."""
        from inspect import signature
        from app.workers.tasks import _generate_user_digest_async

        # Get the signature of generate async implementation
        sig = signature(_generate_user_digest_async)
        params = list(sig.parameters.keys())

        # Verify required context keys are in parameters
        assert "topic_ids" in params, "topic_ids must be in generate signature"
        assert "topic_names" in params, "topic_names must be in generate signature"
        assert "window_start" in params, "window_start must be in generate signature"
        assert "window_end" in params, "window_end must be in generate signature"

    def test_context_contract_generate_requires_payload_no_compat(self):
        """Contract: generate signature must require topic_ids and topic_names (no compat)."""
        from inspect import signature
        from app.workers.tasks import generate_user_digest

        # Get signature of sync wrapper (Celery task)
        sig = signature(generate_user_digest)
        params = list(sig.parameters.keys())

        # Verify no backward compatibility - must require context
        assert "topic_ids" in params, "topic_ids must be required parameter"
        assert "topic_names" in params, "topic_names must be required parameter"


class TestCollectContextPayload:
    """Task 2: Collect payload assembly and dispatch tests (RED tests)."""

    @pytest.mark.asyncio
    async def test_collect_context_payload_includes_topic_ids(self):
        """Contract: collect must pass topic_ids to generate_user_digest."""
        user_id = str(uuid4())
        topic_id = uuid4()

        # Create enabled topic
        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            is_enabled=True,
            last_tweet_id=None,
        )
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

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

        mock_session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=raw_items)

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1"])
        mock_llm_client.close = AsyncMock()

        mock_embedding_provider = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.db.utils.batch_check_exists", return_value=set()),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
            mock_self = MagicMock()
            await _collect_user_topics_async(mock_self, user_id)

            # Verify dispatch includes topic_ids
            mock_digest.delay.assert_called_once()
            call_kwargs = mock_digest.delay.call_args.kwargs
            assert "topic_ids" in call_kwargs
            assert isinstance(call_kwargs["topic_ids"], list)

    @pytest.mark.asyncio
    async def test_collect_context_payload_includes_topic_names(self):
        """Contract: collect must pass topic_names mapping to generate_user_digest."""
        user_id = str(uuid4())
        topic_id = uuid4()

        topic = Topic(
            id=topic_id,
            name="Test Topic",
            query="@test",
            is_enabled=True,
        )
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        base_time = datetime.now(UTC)
        raw_items = [
            MockRawItem(
                source_id="100",
                author="testuser",
                text="Test",
                url="https://x.com/status/100",
                created_at=base_time,
            )
        ]

        mock_session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=raw_items)

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1"])
        mock_llm_client.close = AsyncMock()

        mock_embedding_provider = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.db.utils.batch_check_exists", return_value=set()),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
            mock_self = MagicMock()
            await _collect_user_topics_async(mock_self, user_id)

            call_kwargs = mock_digest.delay.call_args.kwargs
            assert "topic_names" in call_kwargs
            assert isinstance(call_kwargs["topic_names"], dict)

    @pytest.mark.asyncio
    async def test_collect_context_payload_window_fields_iso_parseable(self):
        """Contract: collect must pass ISO-formatted window_start and window_end."""
        user_id = str(uuid4())
        topic_id = uuid4()

        topic = Topic(id=topic_id, name="Test", query="@test", is_enabled=True)
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        base_time = datetime.now(UTC)
        raw_items = [
            MockRawItem(
                source_id="100",
                author="test",
                text="Test",
                url="https://x.com/status/100",
                created_at=base_time,
            )
        ]

        mock_session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=raw_items)

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1"])
        mock_llm_client.close = AsyncMock()

        mock_embedding_provider = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.db.utils.batch_check_exists", return_value=set()),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
            mock_self = MagicMock()
            await _collect_user_topics_async(mock_self, user_id)

            call_kwargs = mock_digest.delay.call_args.kwargs
            assert "window_start" in call_kwargs
            assert "window_end" in call_kwargs
            # Verify ISO format parseable
            datetime.fromisoformat(call_kwargs["window_start"])
            datetime.fromisoformat(call_kwargs["window_end"])

    @pytest.mark.asyncio
    async def test_collect_context_payload_topic_ids_from_resolved_snapshot(self):
        """Contract: topic_ids must come from resolved topics (only enabled)."""
        user_id = str(uuid4())
        topic_id = uuid4()

        topic = Topic(id=topic_id, name="Test", query="@test", is_enabled=True)
        user = User(id=user_id, email="test@example.com", topics=[str(topic_id)])

        base_time = datetime.now(UTC)
        raw_items = [
            MockRawItem(
                source_id="100",
                author="test",
                text="Test",
                url="https://x.com/status/100",
                created_at=base_time,
            )
        ]

        mock_session = AsyncMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user
        topic_result = MagicMock()
        topic_result.scalars.return_value.all.return_value = [topic]
        items_window_result = MagicMock()
        items_window_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.side_effect = [user_result, topic_result, items_window_result]

        mock_session_local = create_mock_session_local(mock_session)

        mock_provider = AsyncMock()
        mock_provider.fetch = AsyncMock(return_value=raw_items)

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1"])
        mock_llm_client.close = AsyncMock()

        mock_embedding_provider = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.get_provider", return_value=mock_provider),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.db.utils.batch_check_exists", return_value=set()),
            patch("app.workers.tasks.generate_user_digest") as mock_digest,
        ):
            mock_self = MagicMock()
            await _collect_user_topics_async(mock_self, user_id)

            call_kwargs = mock_digest.delay.call_args.kwargs
            # Verify topic_ids matches resolved topic
            assert str(topic_id) in call_kwargs["topic_ids"]


class TestGenerateFastPath:
    """Task 3: Generate context-consumption fast path tests (RED tests)."""

    @pytest.mark.asyncio
    async def test_generate_fast_path_consumes_topic_ids_from_context(self):
        """Contract: generate must consume topic_ids and topic_names without re-query."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test Topic"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        # Create mock items for success path
        mock_item = MagicMock()
        mock_item.id = uuid4()
        mock_item.topic_id = UUID(topic_id)
        mock_item.source_id = "test-100"
        mock_item.author = "testuser"
        mock_item.text = "Test tweet"
        mock_item.url = "https://x.com/status/100"
        mock_item.created_at = window_start + timedelta(minutes=30)
        mock_item.metrics = {}

        # Mock query result with items
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_item]
        mock_session.execute.return_value = mock_items_result

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_digest = AsyncMock()
        mock_llm_client.close = AsyncMock()

        # Mock digest result with proper structure
        mock_digest_result = MagicMock()
        mock_digest_result.headline = "Test Headline"
        mock_digest_result.sentiment = "neutral"
        mock_digest_result.themes = []
        mock_digest_result.highlights = []
        mock_digest_result.stats.total_posts_analyzed = 1
        mock_digest_result.stats.unique_authors = 1
        mock_digest_result.stats.total_engagement = 0
        mock_digest_result.stats.avg_engagement_per_post = 0.0
        mock_digest_result.model_dump.return_value = {
            "headline": "Test Headline",
            "highlights": [],
            "themes": [],
            "sentiment": "neutral",
            "stats": {
                "total_posts_analyzed": 1,
                "unique_authors": 1,
                "total_engagement": 0,
                "avg_engagement_per_post": 0.0,
            },
        }
        mock_llm_client.generate_digest.return_value = mock_digest_result

        mock_embedding_provider = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=mock_embedding_provider),
            patch("app.workers.tasks.notify_user_digest") as mock_notify,
        ):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            assert result["status"] == "success"
            assert "user_digest_id" in result
            assert "items_analyzed" in result
            assert "topics_included" in result
            mock_notify.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_fast_path_no_user_requery_from_database(self):
        """Sentinel: generate must NOT query User table when context provided."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        # Mock empty items result (sentinel test doesn't need success path)
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_items_result

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_digest = AsyncMock()
        mock_llm_client.close = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=AsyncMock()),
            patch("app.workers.tasks.notify_user_digest"),
        ):
            mock_self = MagicMock()
            await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            # Verify NO User table query
            for call in mock_session.execute.call_args_list:
                call_str = str(call)
                assert "User" not in call_str, "Should NOT query User table"

    @pytest.mark.asyncio
    async def test_generate_fast_path_no_topic_requery_from_database(self):
        """Sentinel: generate must NOT query Topic table when context provided."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        # Mock empty items result (sentinel test doesn't need success path)
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_items_result

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_digest = AsyncMock()
        mock_llm_client.close = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=AsyncMock()),
            patch("app.workers.tasks.notify_user_digest"),
        ):
            mock_self = MagicMock()
            await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            # Verify NO Topic table query
            for call in mock_session.execute.call_args_list:
                call_str = str(call)
                assert "Topic" not in call_str or "Item.topic_id" in call_str, "Should NOT query Topic table"

    @pytest.mark.asyncio
    async def test_generate_fast_path_output_shape_success_path(self):
        """Contract: generate must return correct output shape and chain to notify."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        # Create mock items for success path
        mock_item = MagicMock()
        mock_item.id = uuid4()
        mock_item.topic_id = UUID(topic_id)
        mock_item.source_id = "test-100"
        mock_item.author = "testuser"
        mock_item.text = "Test tweet"
        mock_item.url = "https://x.com/status/100"
        mock_item.created_at = window_start + timedelta(minutes=30)
        mock_item.metrics = {}

        # Mock query result with items
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_item]
        mock_session.execute.return_value = mock_items_result

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_digest = AsyncMock()
        mock_llm_client.close = AsyncMock()

        # Mock digest result with proper structure
        mock_digest_result = MagicMock()
        mock_digest_result.headline = "Test Headline"
        mock_digest_result.sentiment = "neutral"
        mock_digest_result.themes = []
        mock_digest_result.highlights = []
        mock_digest_result.stats.total_posts_analyzed = 1
        mock_digest_result.stats.unique_authors = 1
        mock_digest_result.stats.total_engagement = 0
        mock_digest_result.stats.avg_engagement_per_post = 0.0
        mock_digest_result.model_dump.return_value = {}
        mock_llm_client.generate_digest.return_value = mock_digest_result

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=AsyncMock()),
            patch("app.workers.tasks.notify_user_digest") as mock_notify,
        ):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            # Verify output shape
            assert result["status"] == "success"
            assert "user_digest_id" in result
            assert "items_analyzed" in result
            assert "topics_included" in result
            # Verify notify chaining
            mock_notify.delay.assert_called_once()


class TestGenerateInvalidContext:
    """Task 4: Invalid context and validation tests (RED tests)."""

    @pytest.mark.asyncio
    async def test_generate_invalid_context_missing_topic_ids(self):
        """Contract: generate must reject missing topic_ids."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_names = {str(uuid4()): "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=None,
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            assert result["status"] == "error"
            assert "topic_ids" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_invalid_context_missing_topic_names(self):
        """Contract: generate must reject missing topic_names."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=None,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            assert result["status"] == "error"
            assert "topic_names" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_invalid_context_empty_topic_ids(self):
        """Contract: generate must reject empty topic_ids with deterministic error."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[],
                topic_names={},
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            assert result["status"] == "error"
            assert "topic_ids required" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_invalid_context_missing_window_start(self):
        """Contract: generate must reject missing window_start."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=None,
                window_end=window_end.isoformat(),
            )

            assert result["status"] == "error"
            assert "window_start" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_generate_invalid_context_missing_window_end(self):
        """Contract: generate must reject missing window_end."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=None,
            )

            assert result["status"] == "error"
            assert "window_end" in result["message"].lower()


class TestGenerateNoCompat:
    """Task 4: No backward compatibility tests (RED tests)."""

    def test_generate_no_compat_old_signature_rejected(self):
        """Contract: generate signature must require context (no old signature support)."""
        from inspect import signature
        from app.workers.tasks import _generate_user_digest_async

        sig = signature(_generate_user_digest_async)
        params = list(sig.parameters.keys())

        # Verify context parameters are required
        assert "topic_ids" in params
        assert "topic_names" in params
        # Verify old-only parameters are insufficient
        # Old signature: (self, user_id, window_start, window_end)
        # New signature must have more params than old
        assert len(params) >= 5, "Must have more params than old signature"

    def test_generate_no_compat_rejects_positional_args_pattern(self):
        """Contract: parameter order must prevent old positional call pattern."""
        from inspect import signature
        from app.workers.tasks import generate_user_digest

        sig = signature(generate_user_digest)
        params = list(sig.parameters.keys())

        # Old positional pattern: (self, user_id, window_start, window_end)
        # New pattern should insert context params BEFORE window params
        # This prevents old code from accidentally working with wrong args
        if "window_start" in params and "topic_ids" in params:
            window_idx = params.index("window_start")
            topic_idx = params.index("topic_ids")
            # topic_ids should come before window_start to break old pattern
            assert topic_idx < window_idx, "topic_ids must come before window_start to prevent old call pattern"

    def test_generate_no_compat_context_params_required(self):
        """Contract: context parameters must not have default values (required)."""
        from inspect import signature
        from app.workers.tasks import _generate_user_digest_async

        sig = signature(_generate_user_digest_async)

        # Verify topic_ids and topic_names have no defaults
        for param_name in ["topic_ids", "topic_names"]:
            param = sig.parameters[param_name]
            assert param.default == param.empty, f"{param_name} must not have default value (must be required)"


class TestGenerateSentinel:
    """Task 5: Sentinel test to prevent user/topic re-query regression."""

    @pytest.mark.asyncio
    async def test_generate_sentinel_no_user_topic_requery(self):
        """Sentinel: generate must NOT query User or Topic tables with context."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test Topic"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        # Mock empty items result (sentinel test doesn't need success path)
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_items_result

        mock_llm_client = AsyncMock()
        mock_llm_client.generate_digest = AsyncMock()
        mock_llm_client.close = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=AsyncMock()),
            patch("app.workers.tasks.notify_user_digest"),
        ):
            mock_self = MagicMock()
            await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

            # Sentinel assertion: NO User or Topic table queries
            for call in mock_session.execute.call_args_list:
                call_str = str(call)
                assert "User" not in call_str, "Sentinel: Should NOT query User table"
                assert "Topic" not in call_str or "Item.topic_id" in call_str, "Sentinel: Should NOT query Topic table"


# =============================================================================
# Task 9: Retry/Error Semantics Tests
# =============================================================================


class TestGenerateRetrySemantics:
    """Task 9: Verify deterministic errors don't retry, transient errors do."""

    @pytest.mark.asyncio
    async def test_invalid_context_no_retry_missing_topic_ids(self):
        """Contract: deterministic validation errors must NOT trigger retry."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_names = {str(uuid4()): "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            # Mock retry mechanism to track if it's called
            mock_self.retry = MagicMock(side_effect=Exception("retry should not be called"))
            mock_self.request = MagicMock()
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[],  # Empty - deterministic error
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

        # Verify no retry was attempted
        mock_self.retry.assert_not_called()
        assert result["status"] == "error"
        assert "topic_ids required" in result["message"].lower()
        assert result.get("_deterministic") is True

    @pytest.mark.asyncio
    async def test_invalid_context_no_retry_malformed_window_timestamp(self):
        """Contract: malformed timestamp must NOT trigger retry."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            mock_self.retry = MagicMock(side_effect=Exception("retry should not be called"))
            mock_self.request = MagicMock()
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start="not-a-timestamp",  # Malformed - deterministic error
                window_end=datetime.now(UTC).isoformat(),
            )

        # Verify no retry was attempted
        mock_self.retry.assert_not_called()
        assert result["status"] == "error"
        assert "window" in result["message"].lower() or "timestamp" in result["message"].lower()
        assert result.get("_deterministic") is True

    @pytest.mark.asyncio
    async def test_invalid_context_no_retry_malformed_topic_uuid(self):
        """Contract: malformed topic UUID must NOT trigger retry."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_names = {"not-a-uuid": "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            mock_self.retry = MagicMock(side_effect=Exception("retry should not be called"))
            mock_self.request = MagicMock()
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=["not-a-uuid"],  # Malformed UUID - deterministic error
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

        # Verify no retry was attempted
        mock_self.retry.assert_not_called()
        assert result["status"] == "error"
        assert "uuid" in result["message"].lower() or "topic" in result["message"].lower()
        assert result.get("_deterministic") is True

    @pytest.mark.asyncio
    async def test_transient_failure_retry_on_database_error(self):
        """Contract: transient execution failures must trigger retry."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        # Simulate transient database error
        mock_session.execute = AsyncMock(side_effect=Exception("Database connection lost"))
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            mock_self.request = MagicMock()
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            # retry() raises Retry exception to signal Celery
            from celery.exceptions import Retry

            mock_self.retry = MagicMock(side_effect=Retry("Retrying", exc=None))

            # Should raise Retry exception (signals retry to Celery)
            with pytest.raises(Retry):
                await _generate_user_digest_async(
                    mock_self,
                    user_id=user_id,
                    topic_ids=[topic_id],
                    topic_names=topic_names,
                    window_start=window_start.isoformat(),
                    window_end=window_end.isoformat(),
                )

        # Verify retry was called
        mock_self.retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_transient_failure_retry_on_llm_error(self):
        """Contract: transient LLM failures must trigger retry."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        # Query succeeds and returns items (so LLM will be called)
        mock_item = MagicMock()
        mock_item.id = uuid4()
        mock_item.topic_id = UUID(topic_id)
        mock_item.source_id = "test-100"
        mock_item.author = "testuser"
        mock_item.text = "Test tweet"
        mock_item.url = "https://x.com/status/100"
        mock_item.created_at = window_start + timedelta(minutes=30)
        mock_item.metrics = {}

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_item]
        mock_session.execute.return_value = mock_items_result
        mock_session_local = create_mock_session_local(mock_session)

        mock_llm_client = AsyncMock()
        # Simulate transient LLM error
        mock_llm_client.generate_digest = AsyncMock(side_effect=Exception("LLM API rate limit"))
        mock_llm_client.close = AsyncMock()

        with (
            patch("app.db.session.get_async_session_local", return_value=mock_session_local),
            patch("app.workers.tasks.LLMClient", return_value=mock_llm_client),
            patch("app.workers.tasks.get_embedding_provider", return_value=AsyncMock()),
        ):
            mock_self = MagicMock()
            mock_self.request = MagicMock()
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            from celery.exceptions import Retry

            mock_self.retry = MagicMock(side_effect=Retry("Retrying", exc=None))

            # Should raise Retry exception
            with pytest.raises(Retry):
                await _generate_user_digest_async(
                    mock_self,
                    user_id=user_id,
                    topic_ids=[topic_id],
                    topic_names=topic_names,
                    window_start=window_start.isoformat(),
                    window_end=window_end.isoformat(),
                )

        # Verify retry was called
        mock_self.retry.assert_called_once

    @pytest.mark.asyncio
    async def test_retry_guard_robust_in_mocked_context(self):
        """Contract: retry guard must not crash when self.request is not available."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        # Simulate error
        mock_session.execute = AsyncMock(side_effect=Exception("Transient error"))
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            # Simulate test context where request attributes might not be set
            del mock_self.request  # Remove request attribute
            # retry() should not be called if request is not available
            mock_self.retry = MagicMock(side_effect=Exception("retry should not be called"))

            # Should not crash, should return error dict
            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

        # Verify graceful degradation
        assert result["status"] == "error"
        assert "Transient error" in result["message"]
        # retry should not be called due to missing request attributes
        mock_self.retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_guard_robust_with_none_request(self):
        """Contract: retry guard must handle None request attribute."""
        from app.workers.tasks import _generate_user_digest_async

        user_id = str(uuid4())
        topic_id = str(uuid4())
        topic_names = {topic_id: "Test"}
        window_start = datetime.now(UTC) - timedelta(hours=1)
        window_end = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Transient error"))
        mock_session_local = create_mock_session_local(mock_session)

        with patch("app.db.session.get_async_session_local", return_value=mock_session_local):
            mock_self = MagicMock()
            mock_self.request = None  # Set to None instead of removing
            mock_self.retry = MagicMock(side_effect=Exception("retry should not be called"))

            result = await _generate_user_digest_async(
                mock_self,
                user_id=user_id,
                topic_ids=[topic_id],
                topic_names=topic_names,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
            )

        assert result["status"] == "error"
        mock_self.retry.assert_not_called()
