"""Fetch a single HackerNews item by id."""

from __future__ import annotations

from hnx.client import HNClient
from hnx.errors import FilteredError, NotFoundError
from hnx.models import SuccessEnvelope
from hnx.transform import normalize_item, normalize_tombstone


async def fetch_item_cmd(
    *,
    client: HNClient,
    item_id: int,
    include_deleted: bool = False,
) -> SuccessEnvelope:
    """Fetch a single item by id and return a SuccessEnvelope.

    - HN returns null → NotFoundError (exit 5).
    - deleted:true or dead:true without include_deleted → FilteredError (exit 7).
    - deleted:true or dead:true with include_deleted → tombstone in data.
    - Otherwise → NormalizedItem in data (single object, not a list).
    """
    raw = await client.fetch_item(item_id)

    if raw is None:
        raise NotFoundError(f"item {item_id} does not exist upstream")

    is_deleted = bool(raw.get("deleted"))
    is_dead = bool(raw.get("dead"))

    query = {"command": "item", "id": item_id, "include_deleted": include_deleted}

    if (is_deleted or is_dead) and not include_deleted:
        raise FilteredError(
            f"item {item_id} is {'deleted' if is_deleted else 'dead'}; "
            "pass --include-deleted to surface it as a tombstone",
            details={"deleted": is_deleted, "dead": is_dead},
        )

    if is_deleted or is_dead:
        item = normalize_tombstone(raw)
    else:
        item = normalize_item(raw)

    return SuccessEnvelope(
        data=item.model_dump(),
        query=query,
        meta={"type": item.type},
        raw=raw,
    )
