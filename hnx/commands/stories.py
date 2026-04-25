"""Fetch and hydrate HackerNews story lists (top / new / best)."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Literal

from hnx.client import HNClient
from hnx.errors import InvalidInputError, TransformError
from hnx.models import SuccessEnvelope
from hnx.transform import normalize_item, normalize_tombstone

Source = Literal["top", "new", "best"]


async def fetch_stories(
    *,
    client: HNClient,
    source: Source,
    limit: int,
    concurrency: int,
    ids_only: bool = False,
    include_deleted: bool = False,
) -> SuccessEnvelope:
    """Fetch a story id list and hydrate the first `limit` items.

    Returns a SuccessEnvelope whose shape follows spec section 6:
    - data: list[NormalizedItem] or list[int] when ids_only
    - raw: {"ids": list[int], "items": list[dict|None] | None}
    """
    if limit < 1:
        raise InvalidInputError(f"--limit must be >= 1, got {limit}")
    if concurrency < 1:
        raise InvalidInputError(f"--concurrency must be >= 1, got {concurrency}")
    if ids_only and include_deleted:
        raise InvalidInputError(
            "--ids-only cannot be combined with --include-deleted "
            "(deleted/dead status is only knowable after hydration)"
        )

    all_ids = await client.fetch_story_ids(source)
    total = len(all_ids)
    limit_capped = limit > total
    effective_limit = min(limit, total)
    selected_ids = all_ids[:effective_limit]

    query = {
        "command": source,
        "source": source,
        "limit": limit,
        "concurrency": concurrency,
        "ids_only": ids_only,
        "include_deleted": include_deleted,
    }

    if ids_only:
        meta = {
            "source": source,
            "limit": limit,
            "fetched": len(selected_ids),
            "returned": len(selected_ids),
            "filtered_deleted": 0,
            "missing": 0,
            "transform_errors": 0,
            "types": {},
            "concurrency": concurrency,
            "limit_capped": limit_capped,
        }
        return SuccessEnvelope(
            data=selected_ids,
            query=query,
            meta=meta,
            raw={"ids": all_ids, "items": None},
        )

    raws: list[dict | None] = await asyncio.gather(*[client.fetch_item(i) for i in selected_ids])

    data = []
    missing = 0
    filtered_deleted = 0
    transform_errors = 0
    for raw in raws:
        if raw is None:
            missing += 1
            continue
        is_deleted = bool(raw.get("deleted") or raw.get("dead"))
        if is_deleted and not include_deleted:
            filtered_deleted += 1
            continue
        if is_deleted and include_deleted:
            data.append(normalize_tombstone(raw))
            continue
        try:
            data.append(normalize_item(raw))
        except TransformError:
            # Unknown upstream type or malformed payload. Don't fail the whole
            # batch; record it under meta.transform_errors so callers can tell
            # this apart from a simple `null` response (meta.missing).
            transform_errors += 1

    types = dict(Counter(item.type for item in data))

    meta = {
        "source": source,
        "limit": limit,
        "fetched": len(selected_ids),
        "returned": len(data),
        "filtered_deleted": filtered_deleted,
        "missing": missing,
        "transform_errors": transform_errors,
        "types": types,
        "concurrency": concurrency,
        "limit_capped": limit_capped,
    }

    return SuccessEnvelope(
        data=[d.model_dump() for d in data],
        query=query,
        meta=meta,
        raw={"ids": all_ids, "items": list(raws)},
    )
