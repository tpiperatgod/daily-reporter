"""Tests for hnx.models — round-trip serialization."""

from __future__ import annotations

from hnx.models import (
    ErrorDetail,
    ErrorEnvelope,
    NormalizedComment,
    NormalizedJob,
    NormalizedPoll,
    NormalizedPollOpt,
    NormalizedStory,
    NormalizedTombstone,
    SuccessEnvelope,
    ThreadRoot,
    ThreadedComment,
)


def test_normalized_story_minimal() -> None:
    s = NormalizedStory(
        type="story",
        id=1,
        title="hello",
        url=None,
        author="bob",
        score=10,
        comment_count=3,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=1",
        text=None,
        kids=[],
    )
    assert s.type == "story"
    assert s.model_dump()["type"] == "story"


def test_normalized_comment_optional_author() -> None:
    c = NormalizedComment(
        type="comment",
        id=2,
        author=None,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=2",
        parent=1,
        text="<p>hi</p>",
        kids=[3],
    )
    assert c.author is None
    assert c.kids == [3]


def test_normalized_job_minimal() -> None:
    j = NormalizedJob(
        type="job",
        id=4,
        title="Hiring",
        url="https://example.com",
        author="acme",
        score=1,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=4",
        text=None,
    )
    assert j.type == "job"


def test_normalized_poll_with_parts() -> None:
    p = NormalizedPoll(
        type="poll",
        id=5,
        title="Q",
        author="bob",
        score=2,
        comment_count=0,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=5",
        text="?",
        parts=[6, 7],
    )
    assert p.parts == [6, 7]


def test_normalized_pollopt() -> None:
    o = NormalizedPollOpt(
        type="pollopt",
        id=6,
        author="bob",
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=6",
        parent=5,
        score=1,
        text="A",
    )
    assert o.parent == 5


def test_normalized_tombstone_all_optional_populated() -> None:
    t = NormalizedTombstone(
        type="tombstone",
        id=7,
        original_type="comment",
        deleted=True,
        dead=False,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=7",
        parent=1,
        author=None,
    )
    assert t.deleted is True
    assert t.dead is False


def test_normalized_tombstone_minimal() -> None:
    t = NormalizedTombstone(
        type="tombstone",
        id=8,
        original_type=None,
        created_at=None,
        hn_url="https://news.ycombinator.com/item?id=8",
        parent=None,
        author=None,
    )
    assert t.deleted is False
    assert t.dead is False


def test_success_envelope_with_single_item() -> None:
    s = NormalizedStory(
        type="story",
        id=1,
        title="hi",
        url=None,
        author="bob",
        score=1,
        comment_count=0,
        created_at="2026-04-22T00:00:00+00:00",
        hn_url="https://news.ycombinator.com/item?id=1",
        text=None,
        kids=[],
    )
    env = SuccessEnvelope(data=s, query={"id": 1}, meta={}, raw={"id": 1})
    dumped = env.model_dump()
    assert dumped["ok"] is True
    assert dumped["data"]["type"] == "story"


def test_success_envelope_with_list() -> None:
    env = SuccessEnvelope(data=[], query={"source": "top"}, meta={"returned": 0}, raw=None)
    assert env.ok is True
    assert env.data == []


def test_success_envelope_with_ids_only() -> None:
    env = SuccessEnvelope(data=[1, 2, 3], query={}, meta={}, raw=None)
    assert env.data == [1, 2, 3]


def test_error_envelope() -> None:
    env = ErrorEnvelope(error=ErrorDetail(type="not_found", message="gone", details={}))
    dumped = env.model_dump()
    assert dumped == {
        "ok": False,
        "error": {"type": "not_found", "message": "gone", "details": {}},
    }


def test_threaded_comment_minimal() -> None:
    c = ThreadedComment(
        id=100,
        author="alice",
        created_at="2007-04-04T19:22:55.000Z",
        hn_url="https://news.ycombinator.com/item?id=100",
        parent=8863,
        story_id=8863,
        text="<p>nice</p>",
    )
    assert c.type == "comment"
    assert c.children == []
    assert c.score is None
    dumped = c.model_dump()
    assert dumped["parent"] == 8863
    assert dumped["story_id"] == 8863


def test_threaded_comment_nested() -> None:
    inner = ThreadedComment(
        id=101,
        author="bob",
        created_at="2007-04-04T20:00:00.000Z",
        hn_url="https://news.ycombinator.com/item?id=101",
        parent=100,
        story_id=8863,
        text="reply",
    )
    outer = ThreadedComment(
        id=100,
        author="alice",
        created_at="2007-04-04T19:22:55.000Z",
        hn_url="https://news.ycombinator.com/item?id=100",
        parent=8863,
        story_id=8863,
        text="original",
        children=[inner],
    )
    assert len(outer.children) == 1
    assert outer.children[0].id == 101


def test_thread_root_minimal() -> None:
    r = ThreadRoot(
        id=8863,
        title="My YC app: Dropbox",
        url="http://example.com",
        author="dhouston",
        score=117,
        created_at="2007-04-04T19:16:40.000Z",
        hn_url="https://news.ycombinator.com/item?id=8863",
    )
    assert r.type == "story"
    assert r.children == []
    assert r.comment_count == 0
    dumped = r.model_dump()
    assert dumped["score"] == 117


def test_thread_root_with_children() -> None:
    child = ThreadedComment(
        id=100,
        author="alice",
        created_at="2007-04-04T19:22:55.000Z",
        hn_url="https://news.ycombinator.com/item?id=100",
        parent=8863,
        story_id=8863,
        text="hello",
    )
    r = ThreadRoot(
        id=8863,
        title="Story",
        url=None,
        author="bob",
        score=10,
        created_at="2007-04-04T19:16:40.000Z",
        hn_url="https://news.ycombinator.com/item?id=8863",
        comment_count=1,
        children=[child],
    )
    dumped = r.model_dump()
    assert dumped["children"][0]["type"] == "comment"


def test_threaded_comment_roundtrip_json() -> None:
    c = ThreadedComment(
        id=100,
        author="alice",
        created_at="2007-04-04T19:22:55.000Z",
        hn_url="https://news.ycombinator.com/item?id=100",
        parent=8863,
        story_id=8863,
        text="<p>test</p>",
        score=5,
    )
    json_str = c.model_dump_json()
    restored = ThreadedComment.model_validate_json(json_str)
    assert restored.id == 100
    assert restored.score == 5


def test_thread_root_roundtrip_json() -> None:
    r = ThreadRoot(
        id=8863,
        title="T",
        url=None,
        author="a",
        score=1,
        created_at="2007-04-04T19:16:40.000Z",
        hn_url="https://news.ycombinator.com/item?id=8863",
    )
    json_str = r.model_dump_json()
    restored = ThreadRoot.model_validate_json(json_str)
    assert restored.title == "T"
