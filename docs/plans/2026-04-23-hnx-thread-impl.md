# hnx thread Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `hnx thread <story_id>` command that fetches a Hacker News story's nested comment tree through the Algolia HN API.

**Design doc:** `docs/plans/2026-04-23-hnx-thread-design.md`

**Contract decisions from review:**

- Algolia HTTP/network/JSON failures must become `UpstreamError`, not raw `httpx`/JSON exceptions.
- `raw` defaults to `null` for `hnx thread`; `--raw` opts into the full Algolia payload.
- Normalized thread output uses existing hnx field names: `score` and `parent`, not Algolia's `points` and `parent_id`.
- Non-story ids are rejected with `InvalidInputError`; `hnx thread` does not silently coerce comments into story roots.
- Full thread output remains default, with optional `--max-depth` and `--max-comments` pruning.

---

## Task 1: Add Thread Models

**Files:**

- Modify: `hnx/models.py`
- Test: `tests/hnx/test_models.py`

Add models after `NormalizedTombstone`:

```python
class ThreadedComment(BaseModel):
    """A comment with nested replies, used by hnx thread."""

    type: Literal["comment"] = "comment"
    id: int
    author: str | None
    created_at: str
    hn_url: str
    parent: int
    story_id: int
    text: str | None
    score: int | None = None
    children: list[ThreadedComment] = Field(default_factory=list)


class ThreadRoot(BaseModel):
    """Root story plus nested comments, used by hnx thread."""

    type: Literal["story"] = "story"
    id: int
    title: str
    url: str | None
    author: str
    score: int
    created_at: str
    hn_url: str
    text: str | None = None
    comment_count: int = 0
    children: list[ThreadedComment] = Field(default_factory=list)
```

Tests:

- `ThreadedComment` defaults `type`, `score`, and `children`.
- `ThreadedComment.model_dump()` includes `parent`, `story_id`, `score`, and nested `children`.
- `ThreadRoot` defaults `type`, `text`, `comment_count`, and `children`.
- Round-trip `model_dump_json()` / `model_validate_json()` for both models.

Verification:

```bash
pytest tests/hnx/test_models.py -v
```

---

## Task 2: Add AlgoliaClient

**Files:**

- Create: `hnx/algolia_client.py`
- Test: `tests/hnx/test_algolia_client.py`

Implementation:

```python
"""Async HTTP client for the Algolia Hacker News API."""

from __future__ import annotations

from typing import Any

import httpx

from hnx.errors import UpstreamError


class AlgoliaClient:
    """Thin async wrapper over the Algolia HN items endpoint."""

    def __init__(
        self,
        *,
        base_url: str = "https://hn.algolia.com/api/v1",
        timeout: float = 10.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)

    async def fetch_thread(self, story_id: int) -> dict | None:
        path = f"/items/{story_id}"
        try:
            response = await self._client.get(path)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"HTTP request failed for {path}: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise UpstreamError(f"upstream status {response.status_code} for {path}")

        try:
            data: Any = response.json()
        except ValueError as exc:
            raise UpstreamError(f"invalid JSON from {path}") from exc

        if not isinstance(data, dict):
            raise UpstreamError(f"expected dict from {path}, got {type(data).__name__}")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AlgoliaClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
```

Tests with `httpx.MockTransport`:

- Asserts path is `/api/v1/items/8863` when base URL is `https://hn.test/api/v1`.
- 200 + dict returns dict.
- 404 returns `None`.
- 403/500 raise `UpstreamError`.
- `httpx.TimeoutException` raises `UpstreamError`.
- Invalid JSON raises `UpstreamError`.
- JSON list/non-dict raises `UpstreamError`.

Verification:

```bash
pytest tests/hnx/test_algolia_client.py -v
```

---

## Task 3: Add Thread Normalization

**Files:**

- Modify: `hnx/transform.py`
- Test: `tests/hnx/test_transform.py`

Add imports:

```python
from dataclasses import dataclass

from hnx.models import ThreadedComment, ThreadRoot
```

Append helpers:

```python
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
```

Tests:

- Root maps Algolia `points` to `score`.
- Comment maps Algolia `parent_id` to `parent`.
- Nested children preserve source order.
- `comment_count` equals comments present in `ThreadRoot.children`.
- `stats.total_comment_count` counts all source comments before pruning.
- `max_depth` prunes deeper replies and sets `stats.truncated`.
- `max_comments` prunes in pre-order and sets `stats.truncated`.
- Non-story root raises `TransformError` when transform is called directly.
- Missing `id`, `parent_id`, or `story_id` raises `TransformError`.

Verification:

```bash
pytest tests/hnx/test_transform.py -k "algolia" -v
pytest tests/hnx/test_transform.py -v
```

---

## Task 4: Add Algolia Config

**Files:**

- Modify: `hnx/config.py`
- Test: `tests/hnx/test_config.py`

Add to `Settings.__init__`:

```python
self.algolia_base_url: str = os.environ.get("HNX_ALGOLIA_BASE_URL", "https://hn.algolia.com/api/v1")
```

Tests:

- Default is `https://hn.algolia.com/api/v1`.
- `HNX_ALGOLIA_BASE_URL` overrides the default.

Verification:

```bash
pytest tests/hnx/test_config.py -v
```

---

## Task 5: Add Thread Command Function

**Files:**

- Create: `hnx/commands/thread.py`
- Test: `tests/hnx/test_thread_command.py`

Implementation:

```python
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
```

Tests:

- Success envelope has `data.type == "story"`, nested `children`, and `raw is None` by default.
- `include_raw=True` includes the raw payload.
- Query echoes `command`, `story_id`, `max_depth`, `max_comments`, and `raw`.
- Meta includes `total_comment_count`, `returned_comment_count`, and `truncated`.
- `None` response raises `NotFoundError`.
- Upstream errors propagate as `UpstreamError`.
- Non-story response raises `InvalidInputError` with useful details.

Verification:

```bash
pytest tests/hnx/test_thread_command.py -v
```

---

## Task 6: Register CLI Command

**Files:**

- Modify: `hnx/cli.py`
- Test: `tests/hnx/test_cli.py`

Add imports:

```python
from hnx.algolia_client import AlgoliaClient
from hnx.commands.thread import fetch_thread
```

Add command:

```python
@cli.command()
@click.argument("story_id", type=int)
@click.option("--max-depth", type=click.IntRange(min=1), default=None)
@click.option("--max-comments", type=click.IntRange(min=1), default=None)
@click.option("--raw", "include_raw", is_flag=True, default=False, help="Include raw Algolia payload.")
def thread(story_id: int, max_depth: int | None, max_comments: int | None, include_raw: bool) -> None:
    """Fetch full comment thread for a story."""

    async def _run() -> None:
        settings = Settings()
        async with AlgoliaClient(base_url=settings.algolia_base_url) as client:
            envelope = await fetch_thread(
                client=client,
                story_id=story_id,
                max_depth=max_depth,
                max_comments=max_comments,
                include_raw=include_raw,
            )
        click.echo(envelope.model_dump_json())

    try:
        asyncio.run(_run())
    except HNXError as err:
        _handle_error(err)
```

Tests:

- `hnx --help` includes `thread`.
- `hnx thread 8863` emits success JSON on stdout and no stderr.
- `--max-depth`, `--max-comments`, and `--raw` are passed to `fetch_thread`.
- Missing or non-int story id is a Click usage error.
- `NotFoundError`, `InvalidInputError`, and `UpstreamError` map to JSON stderr and expected exit codes.

Verification:

```bash
pytest tests/hnx/test_cli.py -k "thread" -v
pytest tests/hnx/test_cli.py -v
```

---

## Task 7: Update User Docs

**Files:**

- Modify: `docs/hnx/commands.md`
- Modify: `docs/hnx/contracts.md`
- Optional: `docs/hnx/quickstart.md`

Document:

- `hnx thread <story_id>`
- `--max-depth`, `--max-comments`, and `--raw`
- Output shape: `ThreadRoot` with nested `ThreadedComment.children`
- Thread-specific raw behavior: `raw` defaults to `null`, `--raw` includes the raw Algolia payload
- Non-story id behavior: `invalid_input`

Verification:

```bash
rg -n "hnx thread|ThreadRoot|ThreadedComment|--max-depth|--max-comments|--raw" docs/hnx
```

---

## Task 8: Final Verification

Run:

```bash
pytest tests/hnx -v
pytest tests/twx tests/hnx -v
ruff check hnx tests/hnx
ruff format --check hnx tests/hnx
```

Expected:

- All hnx tests pass.
- Full project test suite passes.
- Ruff lint and format checks are clean.
