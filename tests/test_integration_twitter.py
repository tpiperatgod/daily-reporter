"""Integration tests for Twitter API adapter."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.db.models import Topic, Item
from app.services.provider.factory import get_provider
from app.services.provider.twitter_adapter import TwitterAPIAdapter
from app.workers.tasks import _collect_data_async


@pytest.fixture
def mock_twitter_settings():
    """Mock settings for Twitter API provider."""
    with patch("app.core.config.settings") as mock_settings:
        # Configure for Twitter API
        mock_settings.X_PROVIDER = "TWITTER_API"
        mock_settings.TWITTER_API_KEY = "test_key"
        mock_settings.TWITTER_API_BASE_URL = "https://api.twitterapi.io"
        mock_settings.TWITTER_API_TIMEOUT_SECONDS = 30
        mock_settings.TWITTER_API_MAX_PAGES = 5
        yield mock_settings


@pytest_asyncio.fixture
async def test_topic(async_session):
    """Create a test topic in database."""
    topic = Topic(
        id=uuid4(),
        name="Test Topic",
        query="@karpathy",
        cron_expression="0 0 * * *",
        is_enabled=True,
        last_collection_timestamp=None,
        last_tweet_id=None
    )
    async_session.add(topic)
    await async_session.commit()
    await async_session.refresh(topic)
    return topic


class TestProviderFactory:
    """Test provider factory selection."""

    def test_factory_returns_twitter_adapter(self, mock_twitter_settings):
        """Test factory returns TwitterAPIAdapter when configured."""
        # Mock embedding provider to avoid Ollama service calls
        with patch("app.workers.tasks.get_embedding_provider") as mock_embed:
            mock_embed.return_value = AsyncMock()

        with patch("app.services.provider.factory.settings", mock_twitter_settings):
            provider = get_provider()
            assert isinstance(provider, TwitterAPIAdapter)

    def test_factory_twitter_api_missing_key(self):
        """Test factory raises error when API key is missing."""
        with patch("app.services.provider.twitter_adapter.settings") as mock_settings:
            mock_settings.TWITTER_API_KEY = None
            mock_settings.TWITTER_API_BASE_URL = "https://api.twitterapi.io"
            mock_settings.TWITTER_API_TIMEOUT_SECONDS = 30
            mock_settings.TWITTER_API_MAX_PAGES = 5

            with patch("app.services.provider.factory.settings") as factory_settings:
                factory_settings.X_PROVIDER = "TWITTER_API"
                factory_settings.UPPER = lambda s: s.upper()

                with pytest.raises(ValueError, match="TWITTER_API_KEY"):
                    get_provider()


class TestIncrementalCollection:
    """Test incremental collection using since_id."""

    @pytest.mark.asyncio
    async def test_first_collection_no_since_id(self, async_session, test_topic, mock_twitter_settings):
        """Test first collection run without since_id."""
        # Generate unique source IDs for this test
        id1 = str(uuid4().int % 1000000000)
        id2 = str(uuid4().int % 1000000000)

        mock_tweets = {
            "tweets": [
                {
                    "id": id1,
                    "author": {"userName": "karpathy"},
                    "text": "First tweet",
                    "url": f"https://x.com/karpathy/status/{id1}",
                    "createdAt": "Fri Jan 31 10:00:00 +0000 2025"
                },
                {
                    "id": id2,
                    "author": {"userName": "karpathy"},
                    "text": "Second tweet",
                    "url": f"https://x.com/karpathy/status/{id2}",
                    "createdAt": "Fri Jan 31 11:00:00 +0000 2025"
                }
            ],
            "has_next_page": False,
            "next_cursor": None
        }

        with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=type('Response', (), {
                'status_code': 200,
                'json': lambda self=None: mock_tweets,
                'raise_for_status': lambda self=None: None
            })())
            mock_client.return_value.__aenter__.return_value.get = mock_get

            # Mock LLM client and embedding provider
            with patch("app.workers.tasks.LLMClient") as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.generate_embedding_hashes_batch = AsyncMock(return_value=["hash1", "hash2"])
                mock_llm.close = AsyncMock()
                mock_llm_class.return_value = mock_llm

                # Mock embedding provider to avoid Ollama service calls
                with patch("app.workers.tasks.get_embedding_provider") as mock_embed:
                    mock_embed.return_value = AsyncMock()

                    # Mock batch_check_exists to return empty (no duplicates)
                    with patch("app.db.utils.batch_check_exists", return_value=set()):

                        # Mock settings in worker
                        with patch("app.services.provider.factory.settings", mock_twitter_settings):
                            with patch("app.workers.tasks.generate_digest"):
                                # Create mock task instance with retry tracking
                                mock_task = MagicMock()
                                mock_task.request = MagicMock()
                                mock_task.request.retries = 0
                                mock_task.max_retries = 3

                                # Run collection
                                result = await _collect_data_async(
                                    mock_task,  # self (task instance)
                                    str(test_topic.id)
                                )

                        # Verify results
                        assert result["status"] == "success"
                        assert result["items_collected"] == 2

                        # Reload topic
                        await async_session.refresh(test_topic)

                        # Verify last_tweet_id was updated to highest ID
                        assert test_topic.last_tweet_id == str(max(int(id1), int(id2)))
                        assert test_topic.last_collection_timestamp is not None

                        # Verify items were created
                        items = await async_session.execute(
                            Item.__table__.select().where(Item.topic_id == test_topic.id)
                        )
                        items_list = items.fetchall()
                        assert len(items_list) == 2

    @pytest.mark.asyncio
    async def test_second_collection_with_since_id(self, async_session, test_topic, mock_twitter_settings):
        """Test second collection run uses since_id."""
        # Generate unique source IDs for this test
        old_id = str(uuid4().int % 1000000000)
        new_id = str(uuid4().int % 1000000000)

        # Set up topic with existing last_tweet_id
        test_topic.last_tweet_id = old_id
        test_topic.last_collection_timestamp = datetime.utcnow() - timedelta(hours=1)
        await async_session.commit()

        mock_tweets = {
            "tweets": [
                {
                    "id": new_id,
                    "author": {"userName": "karpathy"},
                    "text": f"New tweet after {old_id}",
                    "url": f"https://x.com/karpathy/status/{new_id}",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025"
                }
            ],
            "has_next_page": False,
            "next_cursor": None
        }

        with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=type('Response', (), {
                'status_code': 200,
                'json': lambda self=None: mock_tweets,
                'raise_for_status': lambda self=None: None
            })())
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("app.workers.tasks.LLMClient") as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.generate_embedding_hashes_batch = AsyncMock(return_value=["hash456"])
                mock_llm.close = AsyncMock()
                mock_llm_class.return_value = mock_llm

                # Mock embedding provider to avoid Ollama service calls
                with patch("app.workers.tasks.get_embedding_provider") as mock_embed:
                    mock_embed.return_value = AsyncMock()

                    # Mock batch_check_exists to return empty (no duplicates)
                    with patch("app.db.utils.batch_check_exists", return_value=set()):

                        with patch("app.services.provider.factory.settings", mock_twitter_settings):
                            with patch("app.workers.tasks.generate_digest"):
                                # Create mock task instance
                                mock_task = MagicMock()
                                mock_task.request = MagicMock()
                                mock_task.request.retries = 0
                                mock_task.max_retries = 3

                                await _collect_data_async(mock_task, str(test_topic.id))

                                # Verify query included since_id
                                call_args = mock_get.call_args
                                params = call_args[1]['params']
                                assert f"since_id:{old_id}" in params['query']

                                # Verify last_tweet_id updated to new highest
                                await async_session.refresh(test_topic)
                                assert test_topic.last_tweet_id == new_id

    @pytest.mark.asyncio
    async def test_no_new_tweets_preserves_last_tweet_id(self, async_session, test_topic, mock_twitter_settings):
        """Test that last_tweet_id is preserved when no new tweets."""
        test_topic.last_tweet_id = "200"
        await async_session.commit()

        mock_tweets = {
            "tweets": [],
            "has_next_page": False,
            "next_cursor": None
        }

        with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=type('Response', (), {
                'status_code': 200,
                'json': lambda self=None: mock_tweets,
                'raise_for_status': lambda self=None: None
            })())
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("app.services.provider.factory.settings", mock_twitter_settings):
                # Create mock task instance
                mock_task = MagicMock()
                mock_task.request = MagicMock()
                mock_task.request.retries = 0
                mock_task.max_retries = 3

                await _collect_data_async(mock_task, str(test_topic.id))

                # Verify last_tweet_id unchanged
                await async_session.refresh(test_topic)
                assert test_topic.last_tweet_id == "200"


class TestDatabaseUpdates:
    """Test database updates during collection."""

    @pytest.mark.asyncio
    async def test_last_collection_timestamp_updated(self, async_session, test_topic, mock_twitter_settings):
        """Test that last_collection_timestamp is always updated."""
        initial_timestamp = test_topic.last_collection_timestamp

        mock_tweets = {"tweets": [], "has_next_page": False, "next_cursor": None}

        with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=type('Response', (), {
                'status_code': 200,
                'json': lambda self=None: mock_tweets,
                'raise_for_status': lambda self=None: None
            })())
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("app.services.provider.factory.settings", mock_twitter_settings):
                # Create mock task instance
                mock_task = MagicMock()
                mock_task.request = MagicMock()
                mock_task.request.retries = 0
                mock_task.max_retries = 3

                await _collect_data_async(mock_task, str(test_topic.id))

                await async_session.refresh(test_topic)
                assert test_topic.last_collection_timestamp != initial_timestamp
                assert test_topic.last_collection_timestamp is not None

    @pytest.mark.asyncio
    async def test_items_inserted_with_correct_topic_id(self, async_session, test_topic, mock_twitter_settings):
        """Test that collected items have correct topic_id."""
        # Generate unique source ID for this test
        test_id = str(uuid4().int % 1000000000)

        mock_tweets = {
            "tweets": [
                {
                    "id": test_id,
                    "author": {"userName": "karpathy"},
                    "text": "Test",
                    "url": f"https://x.com/karpathy/status/{test_id}",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025"
                }
            ],
            "has_next_page": False,
            "next_cursor": None
        }

        with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=type('Response', (), {
                'status_code': 200,
                'json': lambda self=None: mock_tweets,
                'raise_for_status': lambda self=None: None
            })())
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("app.workers.tasks.LLMClient") as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.generate_embedding_hashes_batch = AsyncMock(return_value=["hash"])
                mock_llm.close = AsyncMock()
                mock_llm_class.return_value = mock_llm

                # Mock embedding provider to avoid Ollama service calls
                with patch("app.workers.tasks.get_embedding_provider") as mock_embed:
                    mock_embed.return_value = AsyncMock()

                    # Mock batch_check_exists to return empty (no duplicates)
                    with patch("app.db.utils.batch_check_exists", return_value=set()):

                        with patch("app.services.provider.factory.settings", mock_twitter_settings):
                            with patch("app.workers.tasks.generate_digest"):
                                # Create mock task instance
                                mock_task = MagicMock()
                                mock_task.request = MagicMock()
                                mock_task.request.retries = 0
                                mock_task.max_retries = 3

                                await _collect_data_async(mock_task, str(test_topic.id))

                                # Verify item has correct topic_id
                                items = await async_session.execute(
                                    Item.__table__.select().where(Item.topic_id == test_topic.id)
                                )
                                items_list = items.fetchall()
                                assert len(items_list) == 1
                                assert str(items_list[0].topic_id) == str(test_topic.id)


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_api_authentication_error(self, async_session, test_topic):
        """Test handling of API authentication errors."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.X_PROVIDER = "TWITTER_API"
            mock_settings.TWITTER_API_KEY = "invalid_key"
            mock_settings.TWITTER_API_BASE_URL = "https://api.twitterapi.io"
            mock_settings.TWITTER_API_TIMEOUT_SECONDS = 30
            mock_settings.TWITTER_API_MAX_PAGES = 5

            with patch("app.services.provider.twitter_adapter.httpx.AsyncClient") as mock_client:
                import httpx
                mock_response = type('Response', (), {
                    'status_code': 401,
                    'text': 'Unauthorized'
                })()
                mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                    "Unauthorized",
                    request=type('Request', (), {})(),
                    response=mock_response
                ))
                mock_client.return_value.__aenter__.return_value.get = mock_get

                with patch("app.services.provider.factory.settings", mock_settings):
                    # Create mock task instance with max retries to avoid retry
                    mock_task = MagicMock()
                    mock_task.request = MagicMock()
                    mock_task.request.retries = 3  # Set to max to avoid retry
                    mock_task.max_retries = 3

                    result = await _collect_data_async(mock_task, str(test_topic.id))

                    # Should return error status
                    assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_disabled_topic_skipped(self, async_session, test_topic):
        """Test that disabled topics are skipped."""
        test_topic.is_enabled = False
        await async_session.commit()

        # Create mock task instance
        mock_task = MagicMock()
        mock_task.request = MagicMock()
        mock_task.request.retries = 0
        mock_task.max_retries = 3

        result = await _collect_data_async(mock_task, str(test_topic.id))

        assert result["status"] == "skipped"
        assert "disabled" in result["message"].lower()


# Pytest fixtures for async database
@pytest_asyncio.fixture
async def async_session():
    """Create async database session for testing."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
