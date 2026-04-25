"""Normalize raw HackerNews item payloads into typed records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hnx.errors import TransformError
from hnx.models import (
    NormalizedComment,
    NormalizedItem,
    NormalizedJob,
    NormalizedPoll,
    NormalizedPollOpt,
    NormalizedStory,
    NormalizedTombstone,
    ThreadedComment,
    ThreadRoot,
)


def hn_url_for(item_id: int) -> str:
    return f"https://news.ycombinator.com/item?id={item_id}"


def parse_created_at(unix_seconds: int | None) -> str | None:
    if unix_seconds is None:
        return None
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()


def _require(raw: dict, key: str) -> Any:
    if key not in raw:
        raise TransformError(f"missing required field: {key}")
    return raw[key]


def normalize_item(raw: dict) -> NormalizedItem:
    """Dispatch a raw HN item payload into the matching NormalizedItem variant.

    Tombstone handling lives in normalize_tombstone(); callers should invoke
    that directly when deleted/dead is set. This function rejects those inputs
    so that ordinary normalization never silently loses data.
    """
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")

    if raw.get("deleted") or raw.get("dead"):
        raise TransformError(
            f"use normalize_tombstone for deleted/dead items; got deleted={raw.get('deleted')} dead={raw.get('dead')}"
        )

    item_type = raw.get("type")
    try:
        if item_type == "story":
            return _normalize_story(raw)
        if item_type == "comment":
            return _normalize_comment(raw)
        if item_type == "job":
            return _normalize_job(raw)
        if item_type == "poll":
            return _normalize_poll(raw)
        if item_type == "pollopt":
            return _normalize_pollopt(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise TransformError(f"failed to normalize {item_type}: {exc}") from exc

    raise TransformError(f"unknown item type: {item_type!r}")


def _normalize_story(raw: dict) -> NormalizedStory:
    item_id = _require(raw, "id")
    return NormalizedStory(
        type="story",
        id=item_id,
        title=raw.get("title", ""),
        url=raw.get("url"),
        author=raw.get("by", ""),
        score=int(raw.get("score", 0)),
        comment_count=int(raw.get("descendants", 0)),
        created_at=parse_created_at(raw.get("time")) or "",
        hn_url=hn_url_for(item_id),
        text=raw.get("text"),
        kids=list(raw.get("kids", []) or []),
    )


def _normalize_comment(raw: dict) -> NormalizedComment:
    item_id = _require(raw, "id")
    return NormalizedComment(
        type="comment",
        id=item_id,
        author=raw.get("by"),
        created_at=parse_created_at(raw.get("time")) or "",
        hn_url=hn_url_for(item_id),
        parent=int(_require(raw, "parent")),
        text=raw.get("text"),
        kids=list(raw.get("kids", []) or []),
    )


def _normalize_job(raw: dict) -> NormalizedJob:
    item_id = _require(raw, "id")
    return NormalizedJob(
        type="job",
        id=item_id,
        title=raw.get("title", ""),
        url=raw.get("url"),
        author=raw.get("by", ""),
        score=int(raw.get("score", 0)),
        created_at=parse_created_at(raw.get("time")) or "",
        hn_url=hn_url_for(item_id),
        text=raw.get("text"),
    )


def _normalize_poll(raw: dict) -> NormalizedPoll:
    item_id = _require(raw, "id")
    return NormalizedPoll(
        type="poll",
        id=item_id,
        title=raw.get("title", ""),
        author=raw.get("by", ""),
        score=int(raw.get("score", 0)),
        comment_count=int(raw.get("descendants", 0)),
        created_at=parse_created_at(raw.get("time")) or "",
        hn_url=hn_url_for(item_id),
        text=raw.get("text"),
        parts=list(raw.get("parts", []) or []),
    )


def _normalize_pollopt(raw: dict) -> NormalizedPollOpt:
    item_id = _require(raw, "id")
    return NormalizedPollOpt(
        type="pollopt",
        id=item_id,
        author=raw.get("by", ""),
        created_at=parse_created_at(raw.get("time")) or "",
        hn_url=hn_url_for(item_id),
        parent=int(_require(raw, "parent")),
        score=int(raw.get("score", 0)),
        text=raw.get("text"),
    )


def normalize_tombstone(raw: dict) -> NormalizedTombstone:
    """Map a deleted/dead HN payload to a NormalizedTombstone."""
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")
    item_id = _require(raw, "id")
    return NormalizedTombstone(
        type="tombstone",
        id=item_id,
        original_type=raw.get("type"),
        deleted=bool(raw.get("deleted", False)),
        dead=bool(raw.get("dead", False)),
        created_at=parse_created_at(raw.get("time")),
        hn_url=hn_url_for(item_id),
        parent=raw.get("parent"),
        author=raw.get("by"),
    )


# ---------------------------------------------------------------------------
# Algolia thread normalization
# ---------------------------------------------------------------------------


@dataclass
class ThreadBudget:
    max_comments: int | None
    returned_comments: int = 0
    truncated: bool = False


def count_algolia_comments(children: list[dict]) -> int:
    return sum(1 + count_algolia_comments(child.get("children", []) or []) for child in children)


def _normalize_algolia_children(
    children: list[dict],
    *,
    depth: int,
    max_depth: int | None,
    budget: ThreadBudget,
) -> list[ThreadedComment]:
    normalized: list[ThreadedComment] = []
    for child in children:
        comment = normalize_algolia_comment(child, depth=depth, max_depth=max_depth, budget=budget)
        if comment is not None:
            normalized.append(comment)
    return normalized


def normalize_algolia_comment(
    raw: dict,
    *,
    depth: int = 1,
    max_depth: int | None = None,
    budget: ThreadBudget | None = None,
) -> ThreadedComment | None:
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")
    budget = budget or ThreadBudget(max_comments=None)

    if max_depth is not None and depth > max_depth:
        budget.truncated = True
        return None
    if budget.max_comments is not None and budget.returned_comments >= budget.max_comments:
        budget.truncated = True
        return None

    item_id = _require(raw, "id")
    budget.returned_comments += 1
    return ThreadedComment(
        id=item_id,
        author=raw.get("author"),
        created_at=raw.get("created_at", ""),
        hn_url=hn_url_for(item_id),
        parent=int(_require(raw, "parent_id")),
        story_id=int(_require(raw, "story_id")),
        text=raw.get("text"),
        score=raw.get("points"),
        children=_normalize_algolia_children(
            raw.get("children", []) or [],
            depth=depth + 1,
            max_depth=max_depth,
            budget=budget,
        ),
    )


def normalize_algolia_thread(
    raw: dict,
    *,
    max_depth: int | None = None,
    max_comments: int | None = None,
) -> tuple[ThreadRoot, dict]:
    if not isinstance(raw, dict):
        raise TransformError(f"expected dict, got {type(raw).__name__}")
    if raw.get("type") != "story":
        raise TransformError(f"expected story root, got {raw.get('type')!r}")

    item_id = _require(raw, "id")
    budget = ThreadBudget(max_comments=max_comments)
    children = _normalize_algolia_children(
        raw.get("children", []) or [],
        depth=1,
        max_depth=max_depth,
        budget=budget,
    )
    total_comment_count = count_algolia_comments(raw.get("children", []) or [])

    thread = ThreadRoot(
        id=item_id,
        title=raw.get("title", ""),
        url=raw.get("url"),
        author=raw.get("author", ""),
        score=int(raw.get("points", 0) or 0),
        created_at=raw.get("created_at", ""),
        hn_url=hn_url_for(item_id),
        text=raw.get("text") or raw.get("story_text"),
        comment_count=budget.returned_comments,
        children=children,
    )
    stats = {
        "total_comment_count": total_comment_count,
        "returned_comment_count": budget.returned_comments,
        "truncated": budget.truncated,
        "max_depth": max_depth,
        "max_comments": max_comments,
    }
    return thread, stats
