from typing import Protocol, List, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional


class RawItem(BaseModel):
    """
    Raw data model for items collected from external sources.

    Represents a tweet/post before being stored in the database.
    """
    source_id: str  # Tweet ID or unique identifier from source
    author: str  # Username or display name
    text: str  # Tweet/post content
    url: str  # URL to the original post
    created_at: datetime  # When the post was created
    media_urls: List[str] = []  # List of media URLs (images, videos)
    metrics: dict = {}  # Engagement metrics (likes, retweets, etc.)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseProvider(Protocol):
    """
    Protocol defining the interface for data providers.

    All providers must implement the fetch method to retrieve items
    from external sources (Twitter/X, Mock, etc.).
    """

    async def fetch(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_items: int = 100
    ) -> List[RawItem]:
        """
        Fetch items from external source matching the query.

        Args:
            query: Search query string
            start_date: Start of time window
            end_date: End of time window
            max_items: Maximum number of items to return

        Returns:
            List of RawItem objects

        Raises:
            Exception: If fetch fails
        """
        ...
