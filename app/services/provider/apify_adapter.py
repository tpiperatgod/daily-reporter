from typing import List
from datetime import datetime
from apify_client import ApifyClientAsync
from app.services.provider.base import BaseProvider, RawItem
from app.core.config import settings
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)


class ApifyAdapter:
    """
    Apify-powered provider for fetching Twitter/X data.

    Uses the Apify Twitter Scraper Lite actor to collect tweets.
    Requires APIFY_API_TOKEN to be configured.
    """

    ACTOR_ID = "apify/twitter-scraper-lite-2"

    def __init__(self):
        """Initialize the Apify adapter."""
        if not settings.APIFY_API_TOKEN:
            raise ValueError("APIFY_API_TOKEN must be set to use ApifyAdapter")

        self.client = ApifyClientAsync(token=settings.APIFY_API_TOKEN)
        self.timeout = settings.APIFY_ACTOR_TIMEOUT_SECONDS

    async def fetch(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_items: int = 100
    ) -> List[RawItem]:
        """
        Fetch tweets from Twitter/X using Apify.

        Args:
            query: Search query for Twitter
            start_date: Start of time window (only fetch tweets after this)
            end_date: End of time window (only fetch tweets before this)
            max_items: Maximum number of items to fetch

        Returns:
            List of RawItem objects

        Raises:
            Exception: If Apify API call fails
        """
        logger.info(
            f"Fetching tweets with Apify",
            extra={
                "query": query,
                "max_items": max_items,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        try:
            # Prepare input for Apify actor
            actor_input = {
                "searchQueries": [query],
                "maxItems": max_items,
                "onlyPosts": True,  # Only get posts, not profiles
                "onlyTwitterBlue": False,  # Include all users
            }

            # Run the actor
            run = await self.client.actor(self.ACTOR_ID).call(
                run_input=actor_input,
                timeout_secs=self.timeout
            )

            # Fetch results from the dataset
            dataset_items = []
            async for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                dataset_items.append(item)

            # Map Apify results to RawItem
            items = []
            for tweet in dataset_items:
                try:
                    # Parse tweet creation time
                    created_at = self._parse_timestamp(tweet.get("createdAt"))

                    # Filter by time window
                    if created_at and start_date <= created_at <= end_date:
                        item = RawItem(
                            source_id=tweet.get("id") or tweet.get("tweetId", ""),
                            author=tweet.get("author", {}).get("userName", "unknown"),
                            text=tweet.get("text", ""),
                            url=tweet.get("url", ""),
                            created_at=created_at,
                            media_urls=self._extract_media_urls(tweet),
                            metrics=self._extract_metrics(tweet)
                        )
                        items.append(item)

                except Exception as e:
                    logger.warning(
                        f"Failed to parse tweet from Apify",
                        extra={"error": str(e), "tweet_id": tweet.get("id")}
                    )
                    continue

            logger.info(
                f"Successfully fetched {len(items)} tweets from Apify",
                extra={"query": query, "total_fetched": len(items)}
            )

            return items

        except Exception as e:
            logger.error(
                f"Apify fetch failed",
                extra={
                    "error": str(e),
                    "query": query
                }
            )
            raise

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp from Apify response.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            # Apify returns ISO format timestamps
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except Exception:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None

    def _extract_media_urls(self, tweet: dict) -> List[str]:
        """
        Extract media URLs from tweet.

        Args:
            tweet: Tweet object from Apify

        Returns:
            List of media URLs
        """
        media_urls = []

        # Extract images
        if "media" in tweet and tweet["media"]:
            for media in tweet["media"]:
                if media.get("type") in ["photo", "video", "animated_gif"]:
                    media_url = media.get("mediaUrlHttps") or media.get("media_url")
                    if media_url:
                        media_urls.append(media_url)

        return media_urls

    def _extract_metrics(self, tweet: dict) -> dict:
        """
        Extract engagement metrics from tweet.

        Args:
            tweet: Tweet object from Apify

        Returns:
            Dictionary of metrics
        """
        return {
            "likes": tweet.get("likeCount", 0),
            "retweets": tweet.get("retweetCount", 0),
            "replies": tweet.get("replyCount", 0),
            "views": tweet.get("viewCount", 0),
            "quotes": tweet.get("quoteCount", 0)
        }
