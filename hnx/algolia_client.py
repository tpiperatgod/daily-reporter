"""Async HTTP client for the Algolia Hacker News API."""

from __future__ import annotations

from typing import Any

import httpx

from hnx.errors import UpstreamError


class AlgoliaClient:
    """Thin async wrapper over the Algolia HN items endpoint."""

    def __init__(
        self,
        *,
        base_url: str = "https://hn.algolia.com/api/v1",
        timeout: float = 10.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)

    async def fetch_thread(self, story_id: int) -> dict | None:
        path = f"/items/{story_id}"
        try:
            response = await self._client.get(path)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"HTTP request failed for {path}: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise UpstreamError(f"upstream status {response.status_code} for {path}")

        try:
            data: Any = response.json()
        except ValueError as exc:
            raise UpstreamError(f"invalid JSON from {path}") from exc

        if not isinstance(data, dict):
            raise UpstreamError(f"expected dict from {path}, got {type(data).__name__}")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AlgoliaClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
