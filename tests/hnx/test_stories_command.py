"""Tests for hnx.commands.stories.fetch_stories."""

from __future__ import annotations

import httpx
import pytest

from hnx.client import HNClient
from hnx.commands.stories import fetch_stories
from hnx.errors import InvalidInputError


def _ids_then_items_handler(ids: list[int], items: dict[int, dict | None]):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v0/topstories.json":
            return httpx.Response(200, json=ids)
        if path == "/v0/newstories.json":
            return httpx.Response(200, json=ids)
        if path == "/v0/beststories.json":
            return httpx.Response(200, json=ids)
        if path.startswith("/v0/item/"):
            item_id = int(path[len("/v0/item/") : -len(".json")])
            payload = items.get(item_id)
            return httpx.Response(
                200,
                content=b"null" if payload is None else None,
                json=payload if payload is not None else None,
            )
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_fetch_stories_happy_path() -> None:
    ids = [100, 101, 102]
    items = {
        100: {
            "id": 100,
            "type": "story",
            "by": "a",
            "score": 5,
            "time": 1713801600,
            "title": "A",
            "descendants": 0,
            "url": "https://a.test",
            "kids": [],
        },
        101: {
            "id": 101,
            "type": "story",
            "by": "b",
            "score": 3,
            "time": 1713801601,
            "title": "B",
            "descendants": 0,
            "url": "https://b.test",
            "kids": [],
        },
        102: {
            "id": 102,
            "type": "story",
            "by": "c",
            "score": 1,
            "time": 1713801602,
            "title": "C",
            "descendants": 0,
            "url": "https://c.test",
            "kids": [],
        },
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=2,
            concurrency=3,
            ids_only=False,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert dumped["ok"] is True
    assert [d["id"] for d in dumped["data"]] == [100, 101]
    assert dumped["query"] == {
        "command": "top",
        "source": "top",
        "limit": 2,
        "concurrency": 3,
        "ids_only": False,
        "include_deleted": False,
    }
    assert dumped["meta"]["source"] == "top"
    assert dumped["meta"]["fetched"] == 2
    assert dumped["meta"]["returned"] == 2
    assert dumped["meta"]["filtered_deleted"] == 0
    assert dumped["meta"]["missing"] == 0
    assert dumped["meta"]["types"] == {"story": 2}
    assert dumped["meta"]["concurrency"] == 3
    assert dumped["meta"]["limit_capped"] is False
    # raw is ListRaw shape
    assert dumped["raw"]["ids"] == [100, 101, 102]
    assert len(dumped["raw"]["items"]) == 2
    assert dumped["raw"]["items"][0]["id"] == 100


@pytest.mark.asyncio
async def test_fetch_stories_filters_deleted_by_default() -> None:
    ids = [200, 201, 202]
    items = {
        200: {
            "id": 200,
            "type": "story",
            "by": "a",
            "score": 1,
            "time": 1713801600,
            "title": "A",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
        201: {"id": 201, "type": "comment", "deleted": True, "time": 1713801601, "parent": 200},
        202: {
            "id": 202,
            "type": "story",
            "by": "c",
            "score": 2,
            "time": 1713801602,
            "title": "C",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=3,
            concurrency=3,
            ids_only=False,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert len(dumped["data"]) == 2
    assert [d["id"] for d in dumped["data"]] == [200, 202]
    assert dumped["meta"]["filtered_deleted"] == 1
    assert dumped["meta"]["returned"] == 2
    assert "tombstone" not in dumped["meta"]["types"]


@pytest.mark.asyncio
async def test_fetch_stories_include_deleted_surfaces_tombstones() -> None:
    ids = [300, 301]
    items = {
        300: {
            "id": 300,
            "type": "story",
            "by": "a",
            "score": 1,
            "time": 1713801600,
            "title": "A",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
        301: {"id": 301, "type": "comment", "dead": True, "time": 1713801601, "parent": 300, "by": "banned"},
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="new",
            limit=2,
            concurrency=3,
            ids_only=False,
            include_deleted=True,
        )

    dumped = env.model_dump()
    assert len(dumped["data"]) == 2
    assert dumped["data"][1]["type"] == "tombstone"
    assert dumped["data"][1]["dead"] is True
    assert dumped["data"][1]["author"] == "banned"
    assert dumped["meta"]["filtered_deleted"] == 0
    assert dumped["meta"]["types"] == {"story": 1, "tombstone": 1}


@pytest.mark.asyncio
async def test_fetch_stories_counts_missing_items() -> None:
    ids = [400, 401]
    items = {
        400: {
            "id": 400,
            "type": "story",
            "by": "a",
            "score": 1,
            "time": 1713801600,
            "title": "A",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
        401: None,  # HN returned null for this id
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=2,
            concurrency=3,
            ids_only=False,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert dumped["meta"]["missing"] == 1
    assert dumped["meta"]["returned"] == 1
    # raw.items preserves the None entry at the same index as the id
    assert dumped["raw"]["items"][1] is None


@pytest.mark.asyncio
async def test_fetch_stories_ids_only() -> None:
    ids = [500, 501, 502, 503]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v0/topstories.json":
            return httpx.Response(200, json=ids)
        # Should NOT be called with ids_only
        raise AssertionError(f"unexpected hydrate call: {request.url.path}")

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=3,
            concurrency=3,
            ids_only=True,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert dumped["data"] == [500, 501, 502]
    assert dumped["meta"]["returned"] == 3
    assert dumped["meta"]["types"] == {}
    assert dumped["raw"]["ids"] == [500, 501, 502, 503]
    assert dumped["raw"]["items"] is None


@pytest.mark.asyncio
async def test_fetch_stories_invalid_ids_only_with_include_deleted() -> None:
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(InvalidInputError, match="ids-only"):
            await fetch_stories(
                client=c,
                source="top",
                limit=3,
                concurrency=3,
                ids_only=True,
                include_deleted=True,
            )


@pytest.mark.asyncio
async def test_fetch_stories_limit_cap_when_limit_exceeds_list_size() -> None:
    ids = [600, 601]
    items = {
        600: {
            "id": 600,
            "type": "story",
            "by": "a",
            "score": 1,
            "time": 1713801600,
            "title": "A",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
        601: {
            "id": 601,
            "type": "story",
            "by": "b",
            "score": 2,
            "time": 1713801601,
            "title": "B",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=100,
            concurrency=3,
            ids_only=False,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert dumped["meta"]["limit_capped"] is True
    assert dumped["meta"]["fetched"] == 2
    assert dumped["meta"]["returned"] == 2


@pytest.mark.asyncio
async def test_fetch_stories_limit_zero_raises() -> None:
    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])),
        retry_backoff=0.0,
    ) as c:
        with pytest.raises(InvalidInputError, match="--limit"):
            await fetch_stories(
                client=c,
                source="top",
                limit=0,
                concurrency=3,
                ids_only=False,
                include_deleted=False,
            )


@pytest.mark.asyncio
async def test_fetch_stories_transform_error_counted_separately_from_missing() -> None:
    """Unknown upstream type must land in meta.transform_errors, not meta.missing."""
    ids = [600, 601, 602]
    items = {
        600: {
            "id": 600,
            "type": "story",
            "by": "a",
            "score": 1,
            "time": 1713801600,
            "title": "Good",
            "descendants": 0,
            "url": None,
            "kids": [],
        },
        601: None,  # counts as `missing`
        602: {"id": 602, "type": "mystery", "time": 1713801602},  # counts as `transform_errors`
    }

    async with HNClient(
        base_url="https://hn.test/v0",
        concurrency=3,
        transport=httpx.MockTransport(_ids_then_items_handler(ids, items)),
        retry_backoff=0.0,
    ) as c:
        env = await fetch_stories(
            client=c,
            source="top",
            limit=3,
            concurrency=3,
            ids_only=False,
            include_deleted=False,
        )

    dumped = env.model_dump()
    assert dumped["meta"]["returned"] == 1
    assert dumped["meta"]["missing"] == 1
    assert dumped["meta"]["transform_errors"] == 1
    assert dumped["meta"]["types"] == {"story": 1}
