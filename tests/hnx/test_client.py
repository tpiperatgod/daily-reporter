"""Tests for hnx.client.HNClient."""

from __future__ import annotations

import httpx
import pytest

from hnx.client import HNClient
from hnx.errors import UpstreamError


def _make_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_story_ids_top() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v0/topstories.json"
        return httpx.Response(200, json=[1, 2, 3, 4, 5])

    async with HNClient(base_url="https://hn.test/v0", concurrency=2, transport=_make_transport(handler)) as c:
        ids = await c.fetch_story_ids("top")

    assert ids == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_fetch_story_ids_rejects_unknown_source() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with HNClient(base_url="https://hn.test/v0", concurrency=2, transport=_make_transport(handler)) as c:
        with pytest.raises(ValueError, match="unknown source"):
            await c.fetch_story_ids("popular")


@pytest.mark.asyncio
async def test_fetch_item_returns_dict() -> None:
    payload = {"id": 42, "type": "story", "time": 1713801600, "by": "x", "score": 1, "title": "t"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v0/item/42.json"
        return httpx.Response(200, json=payload)

    async with HNClient(base_url="https://hn.test/v0", concurrency=2, transport=_make_transport(handler)) as c:
        item = await c.fetch_item(42)

    assert item == payload


@pytest.mark.asyncio
async def test_fetch_item_null_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # HN returns the literal JSON null for missing ids
        return httpx.Response(200, content=b"null", headers={"content-type": "application/json"})

    async with HNClient(base_url="https://hn.test/v0", concurrency=2, transport=_make_transport(handler)) as c:
        item = await c.fetch_item(999)

    assert item is None


@pytest.mark.asyncio
async def test_concurrency_semaphore_caps_inflight(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    current = 0
    peak = 0

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal current, peak
        current += 1
        peak = max(peak, current)
        await asyncio.sleep(0.01)
        current -= 1
        return httpx.Response(
            200, json={"id": 1, "type": "story", "time": 1713801600, "by": "a", "score": 1, "title": "t"}
        )

    # httpx.MockTransport handler can be async
    transport = httpx.MockTransport(slow_handler)

    async with HNClient(base_url="https://hn.test/v0", concurrency=3, transport=transport) as c:
        results = await asyncio.gather(*[c.fetch_item(i) for i in range(10)])

    assert len(results) == 10
    assert peak <= 3, f"peak in-flight {peak} exceeded concurrency cap 3"


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}
    payload = {"id": 1, "type": "story", "time": 1713801600, "by": "a", "score": 1, "title": "t"}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json=payload)

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,  # fast test — no real sleep
    ) as c:
        item = await c.fetch_item(1)

    assert item == payload
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retries_on_500_then_raises_after_max() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, json={"error": "boom"})

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(UpstreamError, match="500"):
            await c.fetch_item(1)

    # max_attempts defaults to 3
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_does_not_retry_on_4xx_other_than_429() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403, json={"error": "forbidden"})

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(UpstreamError, match="403"):
            await c.fetch_item(1)

    assert calls["n"] == 1  # no retries for 403


@pytest.mark.asyncio
async def test_timeout_raises_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout", request=request)

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(UpstreamError, match="HTTP request failed"):
            await c.fetch_item(1)
