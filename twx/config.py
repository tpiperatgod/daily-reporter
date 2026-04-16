"""Environment-backed settings for twx."""

from __future__ import annotations

import os


class Settings:
    """Runtime configuration resolved from environment variables."""

    def __init__(self) -> None:
        self.api_key: str = os.environ.get("TWITTER_API_KEY", "")
        self.base_url: str = os.environ.get("TWX_API_BASE_URL", "https://api.twitterapi.io")
        self.default_limit: int = int(os.environ.get("TWX_DEFAULT_LIMIT", "20"))

    def require_api_key(self) -> str:
        """Return the API key or raise ConfigError."""
        if not self.api_key:
            from twx.errors import ConfigError

            raise ConfigError("TWITTER_API_KEY environment variable is required")
        return self.api_key
