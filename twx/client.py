"""twitterapi.io HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from twx.errors import UpstreamError


class TwitterApiClient:
    """HTTP client wrapping twitterapi.io endpoints."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.twitterapi.io",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
        }
        if transport is not None:
            self._client = httpx.Client(
                base_url=base_url,
                headers=headers,
                transport=transport,
            )
        else:
            self._client = httpx.Client(
                base_url=base_url,
                headers=headers,
                timeout=30.0,
            )

    def get_user_tweets(
        self,
        *,
        username: str,
        cursor: str | None = None,
        include_replies: bool = False,
    ) -> dict[str, Any]:
        """Fetch tweets from a user timeline."""
        params: dict[str, Any] = {
            "userName": username,
        }
        if cursor is not None:
            params["cursor"] = cursor
        if include_replies:
            params["includeReplies"] = "true"
        return self._get("/twitter/user/last_tweets", params=params)

    def get_search_tweets(
        self,
        *,
        query: str,
        mode: str = "latest",
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Search tweets by query."""
        params: dict[str, Any] = {
            "query": query,
            "queryType": "Top" if mode == "top" else "Latest",
        }
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/twitter/tweet/advanced_search", params=params)

    def get_trending_tweets(
        self,
        *,
        query: str,
        mode: str = "top",
    ) -> dict[str, Any]:
        """Fetch trending tweets (uses search with Top mode)."""
        return self.get_search_tweets(query=query, mode=mode)

    def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        """Make a GET request and handle errors."""
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"HTTP request failed: {exc}") from exc

        if response.status_code == 429:
            raise UpstreamError("Rate limited by upstream API", retryable=True)
        if response.status_code >= 500:
            raise UpstreamError(f"Upstream server error: {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise UpstreamError(f"Upstream client error: {response.status_code}", retryable=False)

        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TwitterApiClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
