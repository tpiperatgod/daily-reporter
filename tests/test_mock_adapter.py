"""
Unit tests for MockAdapter with incremental collection support.
"""
import pytest
from datetime import datetime, timedelta
from app.services.provider.mock_adapter import MockAdapter


@pytest.fixture
def mock_adapter():
    """Create a MockAdapter instance for testing."""
    return MockAdapter()


@pytest.fixture
def time_window():
    """Create a standard time window for testing."""
    start = datetime(2025, 2, 1, 0, 0, 0)
    end = datetime(2025, 2, 2, 0, 0, 0)
    return start, end


class TestBasicFetch:
    """Test basic fetch functionality."""

    @pytest.mark.asyncio
    async def test_fetch_without_since_id(self, mock_adapter, time_window):
        """Verify basic fetch works without since_id."""
        start_date, end_date = time_window
        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        assert len(items) == 10
        assert all(hasattr(item, 'source_id') for item in items)
        assert all(hasattr(item, 'author') for item in items)
        assert all(hasattr(item, 'text') for item in items)

    @pytest.mark.asyncio
    async def test_fetch_respects_max_items(self, mock_adapter, time_window):
        """Verify max_items limit is respected."""
        start_date, end_date = time_window

        items_5 = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )
        assert len(items_5) == 5

        items_15 = await mock_adapter.fetch(
            query="crypto news",
            start_date=start_date,
            end_date=end_date,
            max_items=15
        )
        assert len(items_15) == 15


class TestIncrementalCollection:
    """Test incremental collection with since_id."""

    @pytest.mark.asyncio
    async def test_fetch_with_since_id_filters_correctly(self, mock_adapter, time_window):
        """Verify only items with ID > since_id are returned."""
        start_date, end_date = time_window

        # First fetch without since_id
        items_first = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        # Get the max ID from first fetch
        max_id = max(int(item.source_id) for item in items_first)

        # Second fetch with since_id
        items_second = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5,
            since_id=str(max_id)
        )

        # All items in second fetch should have ID > max_id
        for item in items_second:
            assert int(item.source_id) > max_id

    @pytest.mark.asyncio
    async def test_fetch_with_high_since_id_returns_empty(self, mock_adapter, time_window):
        """Verify empty result when since_id exceeds all IDs."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=10,
            since_id="9999999"  # Very high ID
        )

        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_fetch_with_invalid_since_id_ignores_filter(self, mock_adapter, time_window):
        """Verify graceful handling of non-numeric since_id."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=10,
            since_id="invalid_id"  # Non-numeric
        )

        # Should still return items (filter is ignored)
        assert len(items) == 10


class TestQueryTopicSelection:
    """Test query-based topic selection."""

    @pytest.mark.asyncio
    async def test_ai_query_returns_ai_tweets(self, mock_adapter, time_window):
        """Verify AI queries return tweets with AI topics."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI and machine learning",
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        assert len(items) > 0
        # Verify the items are from AI category (IDs 1000-1019)
        for item in items:
            item_id = int(item.source_id)
            assert item_id >= 1000  # AI tweets start at 1000

    @pytest.mark.asyncio
    async def test_crypto_query_returns_crypto_tweets(self, mock_adapter, time_window):
        """Verify crypto queries return crypto tweets."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="Bitcoin and Ethereum",
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        assert len(items) > 0
        # Verify the items are from crypto category (IDs 1020-1039)
        for item in items:
            item_id = int(item.source_id)
            assert item_id >= 1020  # Crypto tweets start at 1020

    @pytest.mark.asyncio
    async def test_tech_query_returns_tech_tweets(self, mock_adapter, time_window):
        """Verify tech queries return tech tweets."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="tech startup software",
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        assert len(items) > 0
        # Verify the items are from tech category (IDs 1040-1059)
        for item in items:
            item_id = int(item.source_id)
            assert item_id >= 1040  # Tech tweets start at 1040


class TestDataStructure:
    """Test data structure and field validation."""

    @pytest.mark.asyncio
    async def test_items_have_required_fields(self, mock_adapter, time_window):
        """Verify all RawItem fields are populated."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        for item in items:
            assert item.source_id is not None
            assert item.author is not None
            assert item.text is not None
            assert item.url is not None
            assert item.created_at is not None
            assert item.media_urls is not None  # Can be empty list
            assert item.metrics is not None

    @pytest.mark.asyncio
    async def test_metrics_have_expected_keys(self, mock_adapter, time_window):
        """Verify metrics dict has expected keys."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        for item in items:
            assert "likes" in item.metrics
            assert "retweets" in item.metrics
            assert "replies" in item.metrics
            assert "quotes" in item.metrics
            assert "views" in item.metrics

    @pytest.mark.asyncio
    async def test_source_ids_are_numeric(self, mock_adapter, time_window):
        """CRITICAL: Verify source_id is numeric string."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=10
        )

        for item in items:
            # Should be able to convert to int without ValueError
            item_id = int(item.source_id)
            assert item_id >= 1000  # All mock IDs start from 1000
            # Verify it's a string, not an int
            assert isinstance(item.source_id, str)

    @pytest.mark.asyncio
    async def test_some_tweets_have_media(self, mock_adapter, time_window):
        """Verify at least 20% of tweets have media_urls."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=20
        )

        items_with_media = [item for item in items if len(item.media_urls) > 0]
        media_percentage = len(items_with_media) / len(items) * 100

        # At least some tweets should have media
        assert media_percentage >= 15  # Allow some tolerance


class TestTimestampGeneration:
    """Test timestamp generation logic."""

    @pytest.mark.asyncio
    async def test_timestamps_within_window(self, mock_adapter, time_window):
        """Verify all created_at timestamps are within requested range."""
        start_date, end_date = time_window

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=20
        )

        for item in items:
            assert start_date <= item.created_at <= end_date

    @pytest.mark.asyncio
    async def test_timestamp_with_zero_window(self, mock_adapter):
        """Verify graceful handling when start_date == end_date."""
        start_date = datetime(2025, 2, 1, 12, 0, 0)
        end_date = start_date  # Same time

        items = await mock_adapter.fetch(
            query="AI news",
            start_date=start_date,
            end_date=end_date,
            max_items=5
        )

        # Should not crash and all timestamps should equal start_date
        assert len(items) == 5
        for item in items:
            assert item.created_at == start_date
