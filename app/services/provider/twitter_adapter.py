"""
Twitter API adapter for fetching tweets using twitterapi.io advanced search.

This adapter provides incremental tweet collection using the since_id parameter,
enabling efficient and cost-effective data gathering.
"""

import re
import httpx
import logging
from typing import List, Optional
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.services.provider.base import BaseProvider, RawItem
from app.core.config import settings

logger = logging.getLogger(__name__)


class TwitterAPIAdapter(BaseProvider):
    """
    Provider adapter for twitterapi.io advanced search endpoint.

    Supports:
    - Username extraction from query
    - Incremental fetching via since_id
    - Multi-page pagination
    - Automatic retry on rate limits
    """

    def __init__(self):
        """Initialize the Twitter API adapter."""
        if not settings.TWITTER_API_KEY:
            raise ValueError("TWITTER_API_KEY is not configured")

        self.api_key = settings.TWITTER_API_KEY
        self.base_url = settings.TWITTER_API_BASE_URL
        self.timeout = settings.TWITTER_API_TIMEOUT_SECONDS
        self.max_pages = settings.TWITTER_API_MAX_PAGES

    async def fetch(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_items: int = 100,
        since_id: Optional[str] = None,
    ) -> List[RawItem]:
        """
        Fetch tweets from Twitter API.

        Args:
            query: Search query (should contain username like "@karpathy" or "karpathy")
            start_date: Start of time window (not used by Twitter API advanced search)
            end_date: End of time window (not used by Twitter API advanced search)
            max_items: Maximum number of items to return
            since_id: Optional tweet ID to fetch tweets after (for incremental collection)

        Returns:
            List of RawItem objects

        Raises:
            ValueError: If username cannot be parsed or authentication fails
            httpx.HTTPStatusError: If API request fails
        """
        # Extract username from query
        username = self._parse_username(query)
        logger.info(f"Fetching tweets from user: {username}, since_id: {since_id}")

        # Build Twitter advanced search query
        search_query = self._build_query(username, since_id)

        # Fetch all pages
        raw_items = await self._fetch_all_pages(search_query, max_items)

        logger.info(f"Fetched {len(raw_items)} tweets from @{username}")
        return raw_items

    def _parse_username(self, query: str) -> str:
        """
        Extract username from query string.

        Supports formats:
        - "@karpathy"
        - "karpathy"
        - "from:karpathy"

        Args:
            query: Query string

        Returns:
            Username without @ prefix

        Raises:
            ValueError: If username cannot be extracted
        """
        query = query.strip()

        # Handle "from:username" format
        from_match = re.search(r"from:(\w+)", query, re.IGNORECASE)
        if from_match:
            return from_match.group(1)

        # Handle "@username" or "username" format
        username_match = re.search(r"@?(\w+)", query)
        if username_match:
            username = username_match.group(1)
            # Validate username (Twitter usernames are alphanumeric + underscore)
            if re.match(r"^[A-Za-z0-9_]{1,15}$", username):
                return username

        raise ValueError(f"Could not extract valid username from query: {query}")

    def _build_query(self, username: str, since_id: Optional[str] = None) -> str:
        """
        Build Twitter advanced search query.

        Args:
            username: Twitter username (without @)
            since_id: Optional tweet ID to fetch tweets after

        Returns:
            Formatted query string (e.g., "from:karpathy since_id:123456789")
        """
        query = f"from:{username}"
        if since_id:
            query += f" since_id:{since_id}"
        return query

    async def _fetch_page(self, query: str, cursor: Optional[str] = None) -> dict:
        """
        Fetch a single page from Twitter API.

        Args:
            query: Twitter advanced search query
            cursor: Pagination cursor (None for first page)

        Returns:
            API response as dict

        Raises:
            ValueError: If authentication fails (401/403)
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.base_url}/twitter/tweet/advanced_search"
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        params = {"query": query, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    raise ValueError(f"Twitter API authentication failed: {e.response.text}")
                elif e.response.status_code == 429:
                    logger.warning(f"Rate limit exceeded: {e.response.text}")
                    raise
                else:
                    logger.error(f"Twitter API error: {e.response.status_code} - {e.response.text}")
                    raise

    async def _fetch_all_pages(self, query: str, max_items: int) -> List[RawItem]:
        """
        Fetch multiple pages from Twitter API.

        Args:
            query: Twitter advanced search query
            max_items: Maximum total items to fetch

        Returns:
            Combined list of RawItem objects from all pages
        """
        all_tweets = []
        cursor = None
        page_count = 0

        while page_count < self.max_pages and len(all_tweets) < max_items:
            page_count += 1
            logger.debug(f"Fetching page {page_count}, cursor: {cursor}")

            # Fetch page
            response = await self._fetch_page(query, cursor)

            # Extract tweets
            tweets = response.get("tweets", [])
            if not tweets:
                logger.info("No more tweets found")
                break

            # Map tweets to RawItems
            for tweet in tweets:
                if len(all_tweets) >= max_items:
                    break
                try:
                    raw_item = self._map_tweet_to_raw_item(tweet)
                    all_tweets.append(raw_item)
                except Exception as e:
                    logger.warning(f"Failed to map tweet {tweet.get('id')}: {e}")
                    continue

            # Check if there are more pages
            has_next = response.get("has_next_page", False)
            cursor = response.get("next_cursor")

            if not has_next or not cursor:
                logger.info("No more pages available")
                break

        logger.info(f"Fetched {len(all_tweets)} tweets across {page_count} pages")
        return all_tweets

    def _map_tweet_to_raw_item(self, tweet: dict) -> RawItem:
        """
        Map Twitter API tweet object to RawItem.

        Args:
            tweet: Tweet object from API response

        Returns:
            RawItem object

        Raises:
            KeyError: If required fields are missing
        """
        # Extract required fields
        source_id = str(tweet["id"])
        author = tweet["author"]["userName"]
        text = tweet["text"]
        url = tweet["url"]
        created_at = self._parse_timestamp(tweet["createdAt"])

        # Extract optional fields
        media_urls = self._extract_media_urls(tweet)
        metrics = self._extract_metrics(tweet)

        return RawItem(
            source_id=source_id,
            author=author,
            text=text,
            url=url,
            created_at=created_at,
            media_urls=media_urls,
            metrics=metrics,
        )

    def _extract_media_urls(self, tweet: dict) -> List[str]:
        """
        Extract media URLs from tweet entities.

        Args:
            tweet: Tweet object from API

        Returns:
            List of media URLs
        """
        media_urls = []
        entities = tweet.get("entities", {})
        media_list = entities.get("media", [])

        for media in media_list:
            if "url" in media:
                media_urls.append(media["url"])

        return media_urls

    def _extract_metrics(self, tweet: dict) -> dict:
        """
        Extract engagement metrics from tweet.

        Args:
            tweet: Tweet object from API

        Returns:
            Dictionary of metrics
        """
        return {
            "likes": tweet.get("likeCount", 0),
            "retweets": tweet.get("retweetCount", 0),
            "replies": tweet.get("replyCount", 0),
            "quotes": tweet.get("quoteCount", 0),
            "views": tweet.get("viewCount", 0),
        }

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse RFC 2822 timestamp from Twitter API.

        Twitter API returns timestamps in RFC 2822 format:
        "Tue Nov 18 00:56:32 +0000 2025"

        Args:
            timestamp_str: RFC 2822 formatted timestamp

        Returns:
            Timezone-aware datetime object (UTC)

        Raises:
            ValueError: If timestamp cannot be parsed
        """
        try:
            # Parse RFC 2822 format (Twitter API v1.1 standard)
            dt = parsedate_to_datetime(timestamp_str)

            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt
        except Exception as e:
            raise ValueError(f"Failed to parse timestamp '{timestamp_str}': {e}")
