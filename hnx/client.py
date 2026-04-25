"""Async HTTP client for the HackerNews firebase API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from hnx.errors import UpstreamError

VALID_SOURCES = {"top", "new", "best"}
_SOURCE_TO_PATH = {
    "top": "/topstories.json",
    "new": "/newstories.json",
    "best": "/beststories.json",
}


class HNClient:
    """Async wrapper over httpx.AsyncClient for HackerNews endpoints.

    Enforces a concurrency cap on fetch_item via an internal semaphore.
    Retries 429 / 5xx / network errors up to `max_attempts` times with
    exponential backoff (base = retry_backoff seconds, doubling per retry).
    """

    def __init__(
        self,
        *,
        base_url: str = "https://hacker-news.firebaseio.com/v0",
        concurrency: int = 10,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
        max_attempts: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
        )
        self._semaphore = asyncio.Semaphore(concurrency)
        self._max_attempts = max_attempts
        self._retry_backoff = retry_backoff

    async def fetch_story_ids(self, source: str) -> list[int]:
        if source not in VALID_SOURCES:
            raise ValueError(f"unknown source: {source!r} (must be one of {sorted(VALID_SOURCES)})")
        path = _SOURCE_TO_PATH[source]
        data = await self._get_json(path)
        if not isinstance(data, list):
            raise UpstreamError(f"expected list from {path}, got {type(data).__name__}")
        return [int(x) for x in data]

    async def fetch_item(self, item_id: int) -> dict | None:
        async with self._semaphore:
            data = await self._get_json(f"/item/{item_id}.json")
        if data is None:
            return None
        if not isinstance(data, dict):
            raise UpstreamError(f"expected dict or null for item {item_id}, got {type(data).__name__}")
        return data

    async def _get_json(self, path: str) -> Any:
        last_err: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get(path)
            except httpx.HTTPError as exc:
                last_err = UpstreamError(f"HTTP request failed: {exc}")
                await self._sleep_backoff(attempt)
                continue

            status = response.status_code
            if status == 429 or status >= 500:
                last_err = UpstreamError(f"upstream status {status} for {path}")
                await self._sleep_backoff(attempt)
                continue
            if status >= 400:
                raise UpstreamError(f"upstream status {status} for {path}")

            return response.json()

        # Exhausted retries
        if last_err is None:
            raise UpstreamError(f"exhausted retries with no captured error for {path}")
        raise last_err

    async def _sleep_backoff(self, attempt: int) -> None:
        if self._retry_backoff <= 0:
            return
        delay = self._retry_backoff * (2**attempt)
        await asyncio.sleep(delay)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> HNClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
