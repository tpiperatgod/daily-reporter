"""Tests for hnx.algolia_client.AlgoliaClient."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from hnx.algolia_client import AlgoliaClient
from hnx.errors import UpstreamError


def _story_response() -> dict:
    return {
        "id": 8863,
        "author": "dhouston",
        "title": "My YC app: Dropbox",
        "url": "http://example.com",
        "type": "story",
        "points": 117,
        "created_at": "2007-04-04T19:16:40.000Z",
        "children": [],
    }


def _transport(body, status_code=200, content_type="application/json"):
    if isinstance(body, dict) or isinstance(body, list):
        import json

        raw = json.dumps(body).encode()
    else:
        raw = body.encode() if isinstance(body, str) else body
    return httpx.MockTransport(
        lambda req: httpx.Response(status_code, content=raw, headers={"content-type": content_type})
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_fetch_thread_returns_dict():
    transport = _transport(_story_response())

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    result = run(go())
    assert result["id"] == 8863
    assert result["type"] == "story"


def test_fetch_thread_404_returns_none():
    transport = _transport({"message": "Not found"}, status_code=404)

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(99999999)

    result = run(go())
    assert result is None


def test_fetch_thread_500_raises_upstream_error():
    transport = _transport("Internal Server Error", status_code=500, content_type="text/plain")

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    with pytest.raises(UpstreamError, match="upstream status 500"):
        run(go())


def test_fetch_thread_403_raises_upstream_error():
    transport = _transport("Forbidden", status_code=403, content_type="text/plain")

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    with pytest.raises(UpstreamError, match="upstream status 403"):
        run(go())


def test_fetch_thread_timeout_raises_upstream_error():
    def timeout_handler(request):
        raise httpx.TimeoutException("timed out")

    transport = httpx.MockTransport(timeout_handler)

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    with pytest.raises(UpstreamError, match="HTTP request failed"):
        run(go())


def test_fetch_thread_invalid_json_raises_upstream_error():
    transport = _transport("not json at all", status_code=200, content_type="text/plain")

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    with pytest.raises(UpstreamError, match="invalid JSON"):
        run(go())


def test_fetch_thread_json_list_raises_upstream_error():
    transport = _transport([1, 2, 3], status_code=200)

    async def go():
        async with AlgoliaClient(transport=transport) as client:
            return await client.fetch_thread(8863)

    with pytest.raises(UpstreamError, match="expected dict"):
        run(go())


def test_fetch_thread_uses_correct_path():
    seen = {}

    def capture_handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"id": 1, "type": "story", "children": []})

    transport = httpx.MockTransport(capture_handler)

    async def go():
        async with AlgoliaClient(base_url="https://hn.test/api/v1", transport=transport) as client:
            return await client.fetch_thread(8863)

    run(go())
    assert "/api/v1/items/8863" in seen["url"]
