"""Tests for hnx.transform.normalize_item."""

from __future__ import annotations

import pytest

from hnx.errors import TransformError
from hnx.models import (
    NormalizedComment,
    NormalizedJob,
    NormalizedPoll,
    NormalizedPollOpt,
    NormalizedStory,
    NormalizedTombstone,
)
from hnx.transform import (
    hn_url_for,
    normalize_algolia_comment,
    normalize_algolia_thread,
    normalize_item,
    normalize_tombstone,
    parse_created_at,
)


def test_hn_url_for() -> None:
    assert hn_url_for(39000000) == "https://news.ycombinator.com/item?id=39000000"


def test_parse_created_at_from_unix_seconds() -> None:
    # 1713801600 = 2024-04-22T16:00:00+00:00
    assert parse_created_at(1713801600) == "2024-04-22T16:00:00+00:00"


def test_normalize_story(load_fixture) -> None:
    item = normalize_item(load_fixture("story.json"))
    assert isinstance(item, NormalizedStory)
    assert item.id == 39000000
    assert item.title == "Sample Story"
    assert item.url == "https://example.com/a"
    assert item.author == "dang"
    assert item.score == 150
    assert item.comment_count == 42
    assert item.kids == [39000001, 39000002]
    assert item.text is None
    assert item.hn_url == "https://news.ycombinator.com/item?id=39000000"
    assert item.created_at == "2024-04-22T16:00:00+00:00"


def test_normalize_comment_preserves_html(load_fixture) -> None:
    item = normalize_item(load_fixture("comment.json"))
    assert isinstance(item, NormalizedComment)
    assert item.parent == 39000000
    assert item.text == "<p>First.</p>"
    assert item.kids == [39000003]


def test_normalize_job(load_fixture) -> None:
    item = normalize_item(load_fixture("job.json"))
    assert isinstance(item, NormalizedJob)
    assert item.title == "Acme is hiring"
    assert item.score == 1
    assert item.url == "https://acme.example/jobs"


def test_normalize_poll(load_fixture) -> None:
    item = normalize_item(load_fixture("poll.json"))
    assert isinstance(item, NormalizedPoll)
    assert item.parts == [39000201, 39000202]
    assert item.comment_count == 5
    assert item.text == "Which one?"


def test_normalize_pollopt(load_fixture) -> None:
    item = normalize_item(load_fixture("pollopt.json"))
    assert isinstance(item, NormalizedPollOpt)
    assert item.parent == 39000200
    assert item.score == 3


def test_normalize_unknown_type_raises() -> None:
    with pytest.raises(TransformError, match="unknown"):
        normalize_item({"id": 1, "type": "mystery", "time": 1713801600})


def test_normalize_missing_id_raises() -> None:
    with pytest.raises(TransformError):
        normalize_item({"type": "story", "time": 1713801600})


def test_normalize_tombstone_deleted(load_fixture) -> None:
    t = normalize_tombstone(load_fixture("tombstone-deleted.json"))
    assert isinstance(t, NormalizedTombstone)
    assert t.id == 39000500
    assert t.deleted is True
    assert t.dead is False
    assert t.original_type == "comment"
    assert t.parent == 39000000
    assert t.author is None
    assert t.created_at == "2024-04-22T18:20:00+00:00"


def test_normalize_tombstone_dead_preserves_author(load_fixture) -> None:
    t = normalize_tombstone(load_fixture("tombstone-dead.json"))
    assert t.dead is True
    assert t.deleted is False
    assert t.author == "banned"


def test_normalize_item_rejects_deleted() -> None:
    with pytest.raises(TransformError, match="deleted/dead"):
        normalize_item({"id": 1, "type": "comment", "deleted": True})


# ---------------------------------------------------------------------------
# Algolia thread normalization tests
# ---------------------------------------------------------------------------


def _algolia_story_raw():
    return {
        "id": 8863,
        "author": "dhouston",
        "title": "My YC app: Dropbox",
        "url": "http://example.com",
        "type": "story",
        "points": 117,
        "created_at": "2007-04-04T19:16:40.000Z",
        "created_at_i": 1175714200,
        "children": [
            {
                "id": 8865,
                "author": "dhouston",
                "text": "oh, and a mac port is coming :)",
                "parent_id": 8863,
                "story_id": 8863,
                "type": "comment",
                "points": None,
                "created_at": "2007-04-04T19:22:55.000Z",
                "created_at_i": 1175714575,
                "options": [],
                "children": [
                    {
                        "id": 9007,
                        "author": "vlad",
                        "text": "Drew, this is awesome!",
                        "parent_id": 8865,
                        "story_id": 8863,
                        "type": "comment",
                        "points": None,
                        "created_at": "2007-04-05T01:48:11.000Z",
                        "created_at_i": 1175737691,
                        "options": [],
                        "children": [],
                    },
                ],
            },
            {
                "id": 8870,
                "author": "Readmore",
                "text": "That's hot!",
                "parent_id": 8863,
                "story_id": 8863,
                "type": "comment",
                "points": None,
                "created_at": "2007-04-04T19:38:05.000Z",
                "created_at_i": 1175715485,
                "options": [],
                "children": [],
            },
        ],
    }


def test_algolia_thread_root_fields():
    thread, stats = normalize_algolia_thread(_algolia_story_raw())
    assert thread.type == "story"
    assert thread.id == 8863
    assert thread.title == "My YC app: Dropbox"
    assert thread.author == "dhouston"
    assert thread.score == 117
    assert thread.hn_url == "https://news.ycombinator.com/item?id=8863"


def test_algolia_thread_children_count():
    thread, stats = normalize_algolia_thread(_algolia_story_raw())
    assert stats["total_comment_count"] == 3
    assert thread.comment_count == 3
    assert len(thread.children) == 2


def test_algolia_thread_nested_children():
    thread, stats = normalize_algolia_thread(_algolia_story_raw())
    child_8865 = thread.children[0]
    assert child_8865.id == 8865
    assert child_8865.parent == 8863
    assert len(child_8865.children) == 1
    assert child_8865.children[0].id == 9007
    assert child_8865.children[0].parent == 8865


def test_algolia_comment_minimal():
    raw = {
        "id": 100,
        "author": "alice",
        "text": "hello",
        "parent_id": 8863,
        "story_id": 8863,
        "type": "comment",
        "points": 5,
        "created_at": "2007-04-04T20:00:00.000Z",
        "options": [],
        "children": [],
    }
    result = normalize_algolia_comment(raw)
    assert result.id == 100
    assert result.author == "alice"
    assert result.parent == 8863
    assert result.story_id == 8863
    assert result.score == 5
    assert result.hn_url == "https://news.ycombinator.com/item?id=100"
    assert result.children == []


def test_algolia_thread_story_text():
    raw = {
        "id": 42,
        "author": "bob",
        "title": "Ask HN",
        "url": None,
        "type": "story",
        "points": 10,
        "created_at": "2007-04-04T19:16:40.000Z",
        "story_text": "<p>This is an Ask HN post</p>",
        "children": [],
    }
    thread, _ = normalize_algolia_thread(raw)
    assert thread.text == "<p>This is an Ask HN post</p>"


def test_algolia_thread_max_depth_prunes():
    thread, stats = normalize_algolia_thread(_algolia_story_raw(), max_depth=1)
    assert len(thread.children) == 2
    assert thread.children[0].children == []
    assert stats["truncated"] is True
    assert stats["total_comment_count"] == 3
    assert thread.comment_count == 2


def test_algolia_thread_max_comments_prunes():
    thread, stats = normalize_algolia_thread(_algolia_story_raw(), max_comments=1)
    assert thread.comment_count == 1
    assert stats["truncated"] is True
    assert stats["total_comment_count"] == 3


def test_algolia_thread_non_story_raises():
    raw = {"id": 1, "type": "comment", "author": "x", "parent_id": 0, "story_id": 0, "children": []}
    with pytest.raises(TransformError, match="expected story root"):
        normalize_algolia_thread(raw)


def test_algolia_comment_missing_id_raises():
    with pytest.raises(TransformError, match="missing required field"):
        normalize_algolia_comment({"parent_id": 1, "story_id": 1})


def test_algolia_comment_missing_parent_id_raises():
    with pytest.raises(TransformError, match="missing required field"):
        normalize_algolia_comment({"id": 1, "story_id": 1})


def test_algolia_thread_no_truncation_by_default():
    thread, stats = normalize_algolia_thread(_algolia_story_raw())
    assert stats["truncated"] is False
    assert stats["max_depth"] is None
    assert stats["max_comments"] is None
