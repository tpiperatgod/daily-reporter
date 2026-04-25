"""Tests for hnx.commands.thread.fetch_thread."""

from __future__ import annotations

import pytest

from hnx.commands.thread import fetch_thread
from hnx.errors import InvalidInputError, NotFoundError, UpstreamError


def _story_raw():
    return {
        "id": 8863,
        "author": "dhouston",
        "title": "My YC app: Dropbox",
        "url": "http://example.com",
        "type": "story",
        "points": 117,
        "created_at": "2007-04-04T19:16:40.000Z",
        "children": [
            {
                "id": 8865,
                "author": "dhouston",
                "text": "mac port coming",
                "parent_id": 8863,
                "story_id": 8863,
                "type": "comment",
                "points": None,
                "created_at": "2007-04-04T19:22:55.000Z",
                "options": [],
                "children": [],
            },
        ],
    }


class FakeAlgoliaClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def fetch_thread(self, story_id: int):
        if self._exc:
            raise self._exc
        return self._response

    async def aclose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_fetch_thread_success():
    client = FakeAlgoliaClient(response=_story_raw())
    envelope = await fetch_thread(client=client, story_id=8863)
    assert envelope.ok is True
    assert envelope.data["type"] == "story"
    assert envelope.data["id"] == 8863
    assert len(envelope.data["children"]) == 1
    assert envelope.data["children"][0]["id"] == 8865
    assert envelope.query["command"] == "thread"
    assert envelope.query["story_id"] == 8863
    assert envelope.meta["type"] == "story"
    assert "total_comment_count" in envelope.meta
    assert envelope.raw is None


@pytest.mark.asyncio
async def test_fetch_thread_include_raw():
    raw = _story_raw()
    client = FakeAlgoliaClient(response=raw)
    envelope = await fetch_thread(client=client, story_id=8863, include_raw=True)
    assert envelope.raw == raw


@pytest.mark.asyncio
async def test_fetch_thread_raw_default_none():
    client = FakeAlgoliaClient(response=_story_raw())
    envelope = await fetch_thread(client=client, story_id=8863)
    assert envelope.raw is None


@pytest.mark.asyncio
async def test_fetch_thread_query_echoes_params():
    client = FakeAlgoliaClient(response=_story_raw())
    envelope = await fetch_thread(client=client, story_id=8863, max_depth=3, max_comments=50)
    assert envelope.query["max_depth"] == 3
    assert envelope.query["max_comments"] == 50


@pytest.mark.asyncio
async def test_fetch_thread_meta_has_stats():
    client = FakeAlgoliaClient(response=_story_raw())
    envelope = await fetch_thread(client=client, story_id=8863)
    assert "total_comment_count" in envelope.meta
    assert "returned_comment_count" in envelope.meta
    assert "truncated" in envelope.meta


@pytest.mark.asyncio
async def test_fetch_thread_not_found():
    client = FakeAlgoliaClient(response=None)
    with pytest.raises(NotFoundError, match="8863"):
        await fetch_thread(client=client, story_id=8863)


@pytest.mark.asyncio
async def test_fetch_thread_upstream_error():
    client = FakeAlgoliaClient(exc=UpstreamError("502 from Algolia"))
    with pytest.raises(UpstreamError, match="502"):
        await fetch_thread(client=client, story_id=8863)


@pytest.mark.asyncio
async def test_fetch_thread_non_story_raises_invalid_input():
    raw = {
        "id": 9007,
        "type": "comment",
        "author": "vlad",
        "parent_id": 8865,
        "story_id": 8863,
        "children": [],
    }
    client = FakeAlgoliaClient(response=raw)
    with pytest.raises(InvalidInputError, match="comment"):
        await fetch_thread(client=client, story_id=9007)
