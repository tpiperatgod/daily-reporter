"""phx launches command orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from phx.client import ProductHuntClient
from phx.errors import InvalidInputError, TransformError, UpstreamError
from phx.models import SuccessEnvelope
from phx.transform import normalize_launch

PH_TIMEZONE = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class LaunchWindow:
    date: str
    date_source: str
    after: str
    before: str


def _iso(dt: datetime) -> str:
    value = dt.isoformat()
    if value.endswith("+00:00"):
        return value[:-6] + "Z"
    return value


def _parse_aware_datetime(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidInputError(f"invalid datetime: {value!r}") from exc
    if dt.tzinfo is None:
        raise InvalidInputError(f"datetime must be timezone-aware: {value!r}")
    return dt


def build_launch_window(
    *,
    date: str | None,
    after: str | None,
    before: str | None,
    now: datetime | None = None,
) -> LaunchWindow:
    if date is not None and (after is not None or before is not None):
        raise InvalidInputError("--date cannot be combined with --after/--before")
    if (after is None) != (before is None):
        raise InvalidInputError("--after and --before must be provided together")

    if after is not None and before is not None:
        after_dt = _parse_aware_datetime(after)
        before_dt = _parse_aware_datetime(before)
        if not (after_dt < before_dt):
            raise InvalidInputError("--after must be strictly less than --before")
        local_date = after_dt.astimezone(PH_TIMEZONE).date().isoformat()
        return LaunchWindow(
            date=local_date,
            date_source="explicit",
            after=_iso(after_dt),
            before=_iso(before_dt),
        )

    if date is not None:
        try:
            parsed = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise InvalidInputError(f"--date must be YYYY-MM-DD: {date!r}") from exc
        source = "explicit"
        day = parsed
    else:
        reference = now or datetime.now(PH_TIMEZONE)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=PH_TIMEZONE)
        else:
            reference = reference.astimezone(PH_TIMEZONE)
        day = reference.date()
        source = "default"

    start = datetime(day.year, day.month, day.day, tzinfo=PH_TIMEZONE)
    end = start + timedelta(days=1)
    return LaunchWindow(
        date=day.isoformat(),
        date_source=source,
        after=_iso(start),
        before=_iso(end),
    )


async def fetch_launches(
    *,
    client: ProductHuntClient,
    date: str | None = None,
    after: str | None = None,
    before: str | None = None,
    limit: int = 20,
    include_raw: bool = False,
    now: datetime | None = None,
) -> SuccessEnvelope:
    if limit < 1:
        raise InvalidInputError("--limit must be >= 1")
    window = build_launch_window(date=date, after=after, before=before, now=now)
    data, raw = await client.fetch_launches(
        posted_after=window.after,
        posted_before=window.before,
        limit=limit,
        include_raw=include_raw,
    )
    posts = data.get("posts")
    if not isinstance(posts, dict):
        raise UpstreamError("GraphQL response missing posts object")
    nodes = posts.get("nodes") or []
    if not isinstance(nodes, list):
        raise UpstreamError("GraphQL posts.nodes must be a list")

    normalized = []
    transform_errors = 0
    for node in nodes:
        try:
            normalized.append(normalize_launch(node).model_dump())
        except TransformError:
            transform_errors += 1

    page_info = posts.get("pageInfo") if isinstance(posts.get("pageInfo"), dict) else {}
    return SuccessEnvelope(
        data=normalized,
        query={
            "command": "launches",
            "date": window.date,
            "date_source": window.date_source,
            "after": window.after,
            "before": window.before,
            "timezone": "America/Los_Angeles",
            "limit": limit,
            "featured": True,
            "order": "RANKING",
            "raw": include_raw,
        },
        meta={
            "source": "producthunt_graphql",
            "returned": len(normalized),
            "limit": limit,
            "transform_errors": transform_errors,
            "total_count": posts.get("totalCount"),
            "page_info": {
                "has_next_page": page_info.get("hasNextPage"),
                "end_cursor": page_info.get("endCursor"),
            },
            "window": {"after": window.after, "before": window.before},
        },
        raw=raw,
    )
