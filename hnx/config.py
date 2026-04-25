"""Environment-backed settings for hnx."""

from __future__ import annotations

import os


class Settings:
    """Runtime configuration resolved from environment variables."""

    def __init__(self) -> None:
        self.base_url: str = os.environ.get("HNX_API_BASE_URL", "https://hacker-news.firebaseio.com/v0")
        self.default_limit: int = int(os.environ.get("HNX_DEFAULT_LIMIT", "30"))
        self.concurrency: int = int(os.environ.get("HNX_CONCURRENCY", "10"))
        self.algolia_base_url: str = os.environ.get("HNX_ALGOLIA_BASE_URL", "https://hn.algolia.com/api/v1")
