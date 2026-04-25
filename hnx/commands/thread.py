"""Fetch a full HN story thread via Algolia."""

from __future__ import annotations

from hnx.algolia_client import AlgoliaClient
from hnx.errors import InvalidInputError, NotFoundError
from hnx.models import SuccessEnvelope
from hnx.transform import normalize_algolia_thread


async def fetch_thread(
    *,
    client: AlgoliaClient,
    story_id: int,
    max_depth: int | None = None,
    max_comments: int | None = None,
    include_raw: bool = False,
) -> SuccessEnvelope:
    raw = await client.fetch_thread(story_id)
    if raw is None:
        raise NotFoundError(f"story {story_id} not found on Algolia")

    if raw.get("type") != "story":
        raise InvalidInputError(
            f"item {story_id} is {raw.get('type')!r}, expected story",
            details={"id": story_id, "type": raw.get("type"), "story_id": raw.get("story_id")},
        )

    thread, stats = normalize_algolia_thread(raw, max_depth=max_depth, max_comments=max_comments)
    return SuccessEnvelope(
        data=thread.model_dump(),
        query={
            "command": "thread",
            "story_id": story_id,
            "max_depth": max_depth,
            "max_comments": max_comments,
            "raw": include_raw,
        },
        meta={"type": thread.type, **stats},
        raw=raw if include_raw else None,
    )
