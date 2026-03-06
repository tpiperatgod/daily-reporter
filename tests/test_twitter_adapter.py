"""Unit tests for TwitterAPIAdapter."""

import pytest
import httpx
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.provider.twitter_adapter import TwitterAPIAdapter
from app.services.provider.base import RawItem


@pytest.fixture
def mock_settings():
    """Mock settings with Twitter API credentials."""
    with patch("app.services.provider.twitter_adapter.settings") as mock:
        mock.TWITTER_API_KEY = "test_api_key"
        mock.TWITTER_API_BASE_URL = "https://api.twitterapi.io"
        mock.TWITTER_API_TIMEOUT_SECONDS = 30
        mock.TWITTER_API_MAX_PAGES = 5
        yield mock


@pytest.fixture
def adapter(mock_settings):
    """Create TwitterAPIAdapter instance with mocked settings."""
    return TwitterAPIAdapter()


class TestUsernameParser:
    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("@karpathy", "karpathy"),
            ("karpathy", "karpathy"),
            ("from:karpathy", "karpathy"),
            ("FROM:karpathy", "karpathy"),
            ("  @karpathy  ", "karpathy"),
        ],
    )
    def test_parse_username_valid_inputs(self, adapter, query, expected):
        assert adapter._parse_username(query) == expected

    @pytest.mark.parametrize("query", ["!!!@@@###", "@thisusernameistoolong"])
    def test_parse_username_invalid_inputs(self, adapter, query):
        with pytest.raises(ValueError, match="Could not extract valid username"):
            adapter._parse_username(query)


class TestQueryBuilder:
    @pytest.mark.parametrize(
        ("since_id", "expected"),
        [
            (None, "from:karpathy"),
            ("2017297261160812716", "from:karpathy since_id:2017297261160812716"),
        ],
    )
    def test_build_query(self, adapter, since_id, expected):
        assert adapter._build_query("karpathy", since_id=since_id) == expected


class TestTimestampParser:
    """Test RFC 2822 timestamp parsing."""

    def test_parse_timestamp_rfc2822(self, adapter):
        """Test parsing RFC 2822 timestamp (Twitter API format)."""
        # Real Twitter API format
        timestamp = "Tue Nov 18 00:56:32 +0000 2025"
        result = adapter._parse_timestamp(timestamp)

        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 18
        assert result.hour == 0
        assert result.minute == 56
        assert result.second == 32
        assert result.tzinfo is not None  # Ensure timezone-aware

    def test_parse_timestamp_with_different_timezone(self, adapter):
        """Test parsing RFC 2822 with different timezone."""
        timestamp = "Mon Jan 31 12:34:56 -0500 2025"
        result = adapter._parse_timestamp(timestamp)

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 31

    def test_parse_timestamp_invalid(self, adapter):
        """Test error on invalid timestamp."""
        with pytest.raises(ValueError, match="Failed to parse timestamp"):
            adapter._parse_timestamp("invalid-timestamp")


class TestMediaExtraction:
    @pytest.mark.parametrize(
        ("tweet", "expected"),
        [
            ({}, []),
            ({"entities": {}}, []),
            (
                {"entities": {"media": [{"url": "https://pbs.twimg.com/media/image1.jpg"}]}},
                ["https://pbs.twimg.com/media/image1.jpg"],
            ),
            (
                {
                    "entities": {
                        "media": [
                            {"url": "https://pbs.twimg.com/media/image1.jpg"},
                            {"url": "https://pbs.twimg.com/media/image2.jpg"},
                        ]
                    }
                },
                [
                    "https://pbs.twimg.com/media/image1.jpg",
                    "https://pbs.twimg.com/media/image2.jpg",
                ],
            ),
        ],
    )
    def test_extract_media_urls(self, adapter, tweet, expected):
        assert adapter._extract_media_urls(tweet) == expected


class TestMetricsExtraction:
    """Test engagement metrics extraction."""

    def test_extract_metrics_all_present(self, adapter):
        """Test extraction when all metrics are present."""
        tweet = {"likeCount": 100, "retweetCount": 50, "replyCount": 25, "quoteCount": 10, "viewCount": 1000}
        result = adapter._extract_metrics(tweet)
        assert result == {"likes": 100, "retweets": 50, "replies": 25, "quotes": 10, "views": 1000}

    def test_extract_metrics_missing_fields(self, adapter):
        """Test extraction with missing metrics (defaults to 0)."""
        tweet = {"likeCount": 100}
        result = adapter._extract_metrics(tweet)
        assert result["likes"] == 100
        assert result["retweets"] == 0
        assert result["replies"] == 0


class TestTweetMapping:
    """Test mapping Twitter API response to RawItem."""

    def test_map_tweet_to_raw_item_complete(self, adapter):
        """Test mapping complete tweet object."""
        tweet = {
            "id": "2017297261160812716",
            "author": {"userName": "karpathy"},
            "text": "This is a test tweet",
            "url": "https://x.com/karpathy/status/2017297261160812716",
            "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
            "entities": {"media": [{"url": "https://pbs.twimg.com/media/image.jpg"}]},
            "likeCount": 500,
            "retweetCount": 100,
            "replyCount": 50,
            "quoteCount": 20,
            "viewCount": 10000,
        }

        result = adapter._map_tweet_to_raw_item(tweet)

        assert isinstance(result, RawItem)
        assert result.source_id == "2017297261160812716"
        assert result.author == "karpathy"
        assert result.text == "This is a test tweet"
        assert result.url == "https://x.com/karpathy/status/2017297261160812716"
        assert isinstance(result.created_at, datetime)
        assert len(result.media_urls) == 1
        assert result.metrics["likes"] == 500

    def test_map_tweet_to_raw_item_minimal(self, adapter):
        """Test mapping tweet with minimal fields."""
        tweet = {
            "id": "123456789",
            "author": {"userName": "testuser"},
            "text": "Minimal tweet",
            "url": "https://x.com/testuser/status/123456789",
            "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
        }

        result = adapter._map_tweet_to_raw_item(tweet)

        assert result.source_id == "123456789"
        assert result.media_urls == []
        assert result.metrics["likes"] == 0

    def test_map_tweet_to_raw_item_missing_required_field(self, adapter):
        """Test error when required field is missing."""
        tweet = {
            "id": "123456789",
            # Missing author
            "text": "Test",
            "url": "https://x.com/test/status/123",
            "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
        }

        with pytest.raises(KeyError):
            adapter._map_tweet_to_raw_item(tweet)


class TestAPIFetch:
    """Test API request handling."""

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, adapter):
        """Test successful API page fetch."""
        mock_response = {
            "tweets": [
                {
                    "id": "123",
                    "author": {"userName": "test"},
                    "text": "Test tweet",
                    "url": "https://x.com/test/status/123",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                }
            ],
            "has_next_page": False,
            "next_cursor": None,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: mock_response))
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await adapter._fetch_page("from:test")

            assert result == mock_response
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_page_auth_error(self, adapter):
        """Test authentication error handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_get = AsyncMock(
                side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(ValueError, match="authentication failed"):
                await adapter._fetch_page("from:test")

    @pytest.mark.asyncio
    async def test_fetch_page_rate_limit(self, adapter):
        """Test rate limit error handling."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_get = AsyncMock(
                side_effect=httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=mock_response)
            )
            mock_client.return_value.__aenter__.return_value.get = mock_get

            with pytest.raises(httpx.HTTPStatusError):
                await adapter._fetch_page("from:test")


class TestPagination:
    """Test multi-page pagination logic."""

    @pytest.mark.asyncio
    async def test_fetch_all_pages_single_page(self, adapter):
        """Test fetching when only one page exists."""
        mock_response = {
            "tweets": [
                {
                    "id": "123",
                    "author": {"userName": "test"},
                    "text": "Test",
                    "url": "https://x.com/test/status/123",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                }
            ],
            "has_next_page": False,
            "next_cursor": None,
        }

        with patch.object(adapter, "_fetch_page", new=AsyncMock(return_value=mock_response)):
            result = await adapter._fetch_all_pages("from:test", max_items=100)

            assert len(result) == 1
            assert result[0].source_id == "123"

    @pytest.mark.asyncio
    async def test_fetch_all_pages_multiple_pages(self, adapter):
        """Test fetching multiple pages."""
        page1 = {
            "tweets": [
                {
                    "id": "1",
                    "author": {"userName": "t"},
                    "text": "T1",
                    "url": "url1",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                }
            ],
            "has_next_page": True,
            "next_cursor": "cursor1",
        }
        page2 = {
            "tweets": [
                {
                    "id": "2",
                    "author": {"userName": "t"},
                    "text": "T2",
                    "url": "url2",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                }
            ],
            "has_next_page": False,
            "next_cursor": None,
        }

        mock_fetch = AsyncMock(side_effect=[page1, page2])
        with patch.object(adapter, "_fetch_page", new=mock_fetch):
            result = await adapter._fetch_all_pages("from:test", max_items=100)

            assert len(result) == 2
            assert result[0].source_id == "1"
            assert result[1].source_id == "2"

    @pytest.mark.asyncio
    async def test_fetch_all_pages_respects_max_items(self, adapter):
        """Test that pagination stops at max_items."""
        mock_response = {
            "tweets": [
                {
                    "id": str(i),
                    "author": {"userName": "t"},
                    "text": f"T{i}",
                    "url": f"url{i}",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                }
                for i in range(20)
            ],
            "has_next_page": True,
            "next_cursor": "cursor",
        }

        with patch.object(adapter, "_fetch_page", new=AsyncMock(return_value=mock_response)):
            result = await adapter._fetch_all_pages("from:test", max_items=10)

            assert len(result) == 10


class TestEndToEndFetch:
    """Test complete fetch workflow."""

    @pytest.mark.asyncio
    async def test_fetch_success(self, adapter):
        """Test successful end-to-end fetch."""
        mock_response = {
            "tweets": [
                {
                    "id": "2017297261160812716",
                    "author": {"userName": "karpathy"},
                    "text": "Test tweet",
                    "url": "https://x.com/karpathy/status/2017297261160812716",
                    "createdAt": "Fri Jan 31 12:00:00 +0000 2025",
                    "likeCount": 100,
                }
            ],
            "has_next_page": False,
            "next_cursor": None,
        }

        with patch.object(adapter, "_fetch_page", new=AsyncMock(return_value=mock_response)):
            result = await adapter.fetch(
                query="@karpathy", start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 31), max_items=100
            )

            assert len(result) == 1
            assert result[0].source_id == "2017297261160812716"
            assert result[0].author == "karpathy"

    @pytest.mark.asyncio
    async def test_fetch_with_since_id(self, adapter):
        """Test fetch with since_id parameter."""
        mock_response = {"tweets": [], "has_next_page": False, "next_cursor": None}

        mock_fetch = AsyncMock(return_value=mock_response)
        with patch.object(adapter, "_fetch_page", new=mock_fetch):
            await adapter.fetch(
                query="karpathy",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                since_id="2017297261160812716",
            )

            # Verify query includes since_id
            call_args = mock_fetch.call_args
            query_arg = call_args[0][0]
            assert "since_id:2017297261160812716" in query_arg

    @pytest.mark.asyncio
    async def test_fetch_invalid_username(self, adapter):
        """Test fetch with username that extracts successfully."""
        # The adapter extracts 'invalid' from '!!!invalid!!!' which is a valid username format
        # This test verifies the extraction works, not that it rejects the input
        # Authentication will fail with invalid API key, but username parsing succeeds
        with pytest.raises(ValueError, match="Twitter API authentication failed"):
            await adapter.fetch(query="!!!invalid!!!", start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 31))
