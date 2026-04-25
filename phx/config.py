"""Environment-backed settings for phx."""

from __future__ import annotations

import os

from phx.errors import ConfigError


class Settings:
    """Runtime configuration resolved from environment variables."""

    def __init__(self) -> None:
        self.token: str = os.environ.get("PRODUCTHUNT_TOKEN", "")
        self.base_url: str = os.environ.get("PHX_API_BASE_URL", "https://api.producthunt.com/v2/api/graphql")
        self.default_limit: int = self._read_positive_int("PHX_DEFAULT_LIMIT", default=20)

    def require_token(self) -> str:
        if not self.token:
            raise ConfigError("PRODUCTHUNT_TOKEN environment variable is required")
        return self.token

    @staticmethod
    def _read_positive_int(name: str, *, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(f"{name} must be an integer") from exc
        if value < 1:
            raise ConfigError(f"{name} must be >= 1")
        return value
