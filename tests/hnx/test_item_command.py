"""Tests for hnx.commands.item.fetch_item_cmd."""

from __future__ import annotations

import httpx
import pytest

from hnx.client import HNClient
from hnx.commands.item import fetch_item_cmd
from hnx.errors import FilteredError, NotFoundError


def _item_handler(items: dict[int, dict | None]):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/v0/item/"):
            item_id = int(path[len("/v0/item/") : -len(".json")])
            if item_id not in items:
                return httpx.Response(200, content=b"null", headers={"content-type": "application/json"})
            payload = items[item_id]
            if payload is None:
                return httpx.Response(200, content=b"null", headers={"content-type": "application/json"})
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_fetch_item_cmd_story() -> None:
    items = {
        700: {
            "id": 700,
            "type": "story",
            "by": "a",
            "score": 5,
            "time": 1713801600,
            "title": "T",
            "descendants": 1,
            "url": "https://x.test",
            "kids": [701],
        },
    }
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler(items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_item_cmd(client=c, item_id=700, include_deleted=False)

    dumped = env.model_dump()
    assert dumped["ok"] is True
    assert dumped["data"]["type"] == "story"
    assert dumped["data"]["id"] == 700
    assert dumped["query"] == {"command": "item", "id": 700, "include_deleted": False}
    assert dumped["meta"]["type"] == "story"
    assert dumped["raw"]["id"] == 700


@pytest.mark.asyncio
async def test_fetch_item_cmd_null_raises_not_found() -> None:
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler({})),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(NotFoundError, match="does not exist"):
            await fetch_item_cmd(client=c, item_id=999, include_deleted=False)


@pytest.mark.asyncio
async def test_fetch_item_cmd_deleted_without_flag_raises_filtered() -> None:
    items = {800: {"id": 800, "type": "comment", "deleted": True, "time": 1713801600, "parent": 700}}
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler(items)),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(FilteredError) as exc_info:
            await fetch_item_cmd(client=c, item_id=800, include_deleted=False)

    assert exc_info.value.details == {"deleted": True, "dead": False}


@pytest.mark.asyncio
async def test_fetch_item_cmd_dead_without_flag_raises_filtered() -> None:
    items = {801: {"id": 801, "type": "comment", "dead": True, "time": 1713801600, "parent": 700, "by": "x"}}
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler(items)),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(FilteredError) as exc_info:
            await fetch_item_cmd(client=c, item_id=801, include_deleted=False)

    assert exc_info.value.details == {"deleted": False, "dead": True}


@pytest.mark.asyncio
async def test_fetch_item_cmd_deleted_with_flag_returns_tombstone() -> None:
    items = {802: {"id": 802, "type": "comment", "deleted": True, "time": 1713801600, "parent": 700}}
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler(items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_item_cmd(client=c, item_id=802, include_deleted=True)

    dumped = env.model_dump()
    assert dumped["ok"] is True
    assert dumped["data"]["type"] == "tombstone"
    assert dumped["data"]["deleted"] is True
    assert dumped["data"]["original_type"] == "comment"
    assert dumped["meta"]["type"] == "tombstone"


@pytest.mark.asyncio
async def test_fetch_item_cmd_comment() -> None:
    items = {
        900: {
            "id": 900,
            "type": "comment",
            "by": "bob",
            "parent": 1,
            "text": "<p>hi</p>",
            "time": 1713801600,
            "kids": [],
        },
    }
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=1,
        transport=httpx.MockTransport(_item_handler(items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_item_cmd(client=c, item_id=900, include_deleted=False)

    dumped = env.model_dump()
    assert dumped["data"]["type"] == "comment"
    assert dumped["data"]["parent"] == 1
