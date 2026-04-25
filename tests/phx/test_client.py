"""Tests for phx.client.ProductHuntClient."""

from __future__ import annotations

import json

import httpx
import pytest

from phx.client import ProductHuntClient
from phx.errors import UpstreamError


@pytest.mark.asyncio
async def test_fetch_launches_posts_graphql_with_auth_header():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": {"posts": {"nodes": [], "pageInfo": {}, "totalCount": 0}}})

    async with ProductHuntClient(api_key="token-123", transport=httpx.MockTransport(handler)) as client:
        data, raw = await client.fetch_launches(
            posted_after="2026-04-24T00:00:00-07:00",
            posted_before="2026-04-25T00:00:00-07:00",
            limit=20,
            include_raw=True,
        )

    assert captured["headers"]["authorization"] == "Bearer token-123"
    assert "query" in captured["body"]
    assert captured["body"]["variables"]["first"] == 20
    assert captured["body"]["variables"]["postedAfter"] == "2026-04-24T00:00:00-07:00"
    assert data["posts"]["nodes"] == []
    assert raw["data"]["posts"]["totalCount"] == 0


@pytest.mark.asyncio
async def test_fetch_product_sends_slug_variable():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": {"post": None}})

    async with ProductHuntClient(api_key="token-123", transport=httpx.MockTransport(handler)) as client:
        data, raw = await client.fetch_product(ref="cursor", ref_type="slug")

    assert captured["body"]["variables"] == {"id": None, "slug": "cursor"}
    assert data is None
    assert raw is None


@pytest.mark.asyncio
async def test_fetch_product_sends_id_variable():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": {"post": {"id": "123"}}})

    async with ProductHuntClient(api_key="token-123", transport=httpx.MockTransport(handler)) as client:
        await client.fetch_product(ref="123", ref_type="id")

    assert captured["body"]["variables"] == {"id": "123", "slug": None}


@pytest.mark.asyncio
async def test_graphql_errors_map_to_upstream_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "bad query"}]})

    async with ProductHuntClient(api_key="token-123", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(UpstreamError, match="bad query") as excinfo:
            await client.fetch_launches(posted_after="a", posted_before="b", limit=1)

    assert excinfo.value.details["operation"] == "PhxLaunches"


@pytest.mark.asyncio
async def test_http_401_non_retryable_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async with ProductHuntClient(
        api_key="token-123", transport=httpx.MockTransport(handler), retry_backoff=0
    ) as client:
        with pytest.raises(UpstreamError) as excinfo:
            await client.fetch_launches(posted_after="a", posted_before="b", limit=1)

    assert excinfo.value.details["status_code"] == 401
    assert excinfo.value.details["retryable"] is False


@pytest.mark.asyncio
async def test_http_500_retries_then_raises():
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": "server"})

    async with ProductHuntClient(
        api_key="token-123",
        transport=httpx.MockTransport(handler),
        max_attempts=2,
        retry_backoff=0,
    ) as client:
        with pytest.raises(UpstreamError) as excinfo:
            await client.fetch_launches(posted_after="a", posted_before="b", limit=1)

    assert calls == 2
    assert excinfo.value.details["retryable"] is True


@pytest.mark.asyncio
async def test_non_dict_json_maps_to_upstream_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with ProductHuntClient(api_key="token-123", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(UpstreamError, match="expected dict"):
            await client.fetch_launches(posted_after="a", posted_before="b", limit=1)
