# hnx thread — Design Document

**Date**: 2026-04-23
**Status**: Approved after review
**Approach**: A — Independent AlgoliaClient + normalized ThreadedComment model

## Background

`hnx` is a JSON-first CLI wrapping the HackerNews Firebase API. Current commands (`top`, `new`, `best`, `item`) only support fetching story lists and individual items. There is no way to fetch a story's complete comment thread — the most valuable data for agent workflows (LLM summarization, sentiment analysis, trend detection).

Research confirms strong demand: every HN digest tool includes comments, LangChain has built-in `HNLoader.load_comments()`, Simon Willison maintains `llm-hacker-news`, and multiple commercial Apify scrapers exist for HN comments.

## Decision: Algolia API as thread backend

The Firebase API requires N+1 HTTP requests for a comment tree (one per item), making a 500-comment thread take 20-40s. The Algolia HN API returns a fully nested tree in a **single request** via `/api/v1/items/{id}`.

**Firebase remains the backend for existing commands** (`top`/`new`/`best`/`item`). Algolia is used exclusively for the `thread` command. Reasons not to fully migrate:

- No equivalent for Firebase's `/beststories.json` (proprietary ranking algorithm)
- Algolia's `front_page` tag has known staleness bug (issue #224)
- Firebase is near real-time; Algolia has 2-min to hourly delays
- Firebase returns deleted/dead items; Algolia excludes them

## Architecture

### New files

```
hnx/
├── algolia_client.py   # AlgoliaClient — async httpx wrapper for hn.algolia.com
├── commands/
│   └── thread.py       # fetch_thread() — orchestration
```

### Modified files

- `hnx/cli.py` — register `thread` command
- `hnx/config.py` — add `algolia_base_url`
- `hnx/models.py` — add `ThreadedComment`, `ThreadRoot`
- `hnx/transform.py` — add Algolia thread normalization helpers

### Unchanged files

- `hnx/client.py` — HNClient (Firebase) untouched
- `hnx/errors.py` — reuse existing error types
- `hnx/commands/item.py`, `hnx/commands/stories.py` — untouched

## Design details

### AlgoliaClient

```python
class AlgoliaClient:
    def __init__(
        self,
        *,
        base_url="https://hn.algolia.com/api/v1",
        timeout=10.0,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
    ):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)

    async def fetch_thread(self, story_id: int) -> dict | None:
        """Single HTTP request to /items/{story_id}."""
        path = f"/items/{story_id}"
        try:
            resp = await self._client.get(path)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"HTTP request failed for {path}: {exc}") from exc

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise UpstreamError(f"upstream status {resp.status_code} for {path}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise UpstreamError(f"invalid JSON from {path}") from exc
        if not isinstance(data, dict):
            raise UpstreamError(f"expected dict from {path}, got {type(data).__name__}")
        return data

    async def aclose(self) -> None: ...
    async def __aenter__(self) -> AlgoliaClient: ...
    async def __aexit__(self, *args): ...
```

Simpler than `HNClient` — single request, no semaphore needed. It still must translate all `httpx` and payload-shape failures into `UpstreamError` so the CLI preserves structured JSON errors on stderr.

### Data models

**Representative Algolia API response shape**:

```json
{
  "id": 8863,
  "author": "dhouston",
  "title": "My YC app: Dropbox",
  "url": "http://www.getdropbox.com/...",
  "type": "story",
  "points": 117,
  "created_at": "2007-04-04T19:16:40.000Z",
  "children": [
    {
      "id": 8865,
      "type": "comment",
      "author": "dhouston",
      "text": "...",
      "parent_id": 8863,
      "story_id": 8863,
      "points": null,
      "created_at": "2007-04-04T19:22:55.000Z",
      "children": [...]
    }
  ]
}
```

**New models**:

```python
class ThreadedComment(BaseModel):
    type: Literal["comment"] = "comment"
    id: int
    author: str | None
    created_at: str           # ISO 8601 from Algolia
    hn_url: str
    parent: int               # normalized from Algolia parent_id
    story_id: int             # useful thread context from Algolia
    text: str | None
    score: int | None = None  # normalized from Algolia points
    children: list[ThreadedComment] = Field(default_factory=list)

class ThreadRoot(BaseModel):
    type: Literal["story"] = "story"
    id: int
    title: str
    url: str | None
    author: str
    score: int                # normalized from Algolia points
    created_at: str
    hn_url: str
    text: str | None
    comment_count: int = 0    # count of comments present in children after pruning
    children: list[ThreadedComment] = Field(default_factory=list)
```

Field naming choices:
- `parent` — matches existing `NormalizedComment`; source `parent_id` is mapped during normalization
- `score` — matches existing normalized story/job/poll fields; source `points` is mapped during normalization
- `children` (not `kids`) — represents full objects, not just IDs
- `story_id` — retained because Algolia supplies it for every nested comment and it is useful for thread consumers
- `created_at` — already ISO 8601 from Algolia, no conversion needed

### Transform

```python
@dataclass
class ThreadBudget:
    max_comments: int | None
    returned_comments: int = 0
    truncated: bool = False

def count_algolia_comments(children: list[dict]) -> int:
    """Count all source comments before any pruning."""
    return sum(1 + count_algolia_comments(c.get("children", [])) for c in children)

def normalize_algolia_children(
    children: list[dict],
    *,
    depth: int,
    max_depth: int | None,
    budget: ThreadBudget,
) -> list[ThreadedComment]:
    normalized = []
    for raw_child in children:
        child = normalize_algolia_comment(raw_child, depth=depth, max_depth=max_depth, budget=budget)
        if child is not None:
            normalized.append(child)
    return normalized

def normalize_algolia_comment(
    raw: dict,
    *,
    depth: int,
    max_depth: int | None,
    budget: ThreadBudget,
) -> ThreadedComment | None:
    if max_depth is not None and depth > max_depth:
        budget.truncated = True
        return None
    if budget.max_comments is not None and budget.returned_comments >= budget.max_comments:
        budget.truncated = True
        return None

    budget.returned_comments += 1
    return ThreadedComment(
        id=raw["id"],
        author=raw.get("author"),
        created_at=raw.get("created_at", ""),
        hn_url=hn_url_for(raw["id"]),
        parent=raw.get("parent_id", 0),
        story_id=raw.get("story_id", 0),
        text=raw.get("text"),
        score=raw.get("points"),
        children=normalize_algolia_children(
            raw.get("children", []),
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
    item_id = raw["id"]
    budget = ThreadBudget(max_comments=max_comments)
    children = normalize_algolia_children(raw.get("children", []), depth=1, max_depth=max_depth, budget=budget)
    total_comment_count = count_algolia_comments(raw.get("children", []))
    return ThreadRoot(
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
    ), {
        "total_comment_count": total_comment_count,
        "returned_comment_count": budget.returned_comments,
        "truncated": budget.truncated,
        "max_depth": max_depth,
        "max_comments": max_comments,
    }
```

`ThreadBudget`/`normalize_algolia_children()` are small implementation helpers. They normalize in pre-order, preserve source order, and apply the `max_comments` budget globally across the whole tree. Depth is comment depth where top-level comments are depth `1`.

`normalize_algolia_thread()` only accepts story roots. `fetch_thread()` checks `raw.get("type") == "story"` first and raises `InvalidInputError` if a caller passes a comment/job/poll id.

```python
if raw.get("type") != "story":
    raise InvalidInputError(
        f"item {story_id} is {raw.get('type')!r}, expected story",
        details={"id": story_id, "type": raw.get("type"), "story_id": raw.get("story_id")},
    )
```

### Command

```python
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
        raise NotFoundError(f"story {story_id} not found")
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

### CLI

```bash
hnx thread 8863              # Full thread as nested JSON
hnx thread 8863 --max-depth 2
hnx thread 8863 --max-comments 200
hnx thread 8863 --raw        # Include raw Algolia payload
```

Output follows existing `SuccessEnvelope` keys. `data` is a `ThreadRoot` with nested `children`. Because raw thread payloads can be large, `raw` defaults to `null` for this command and `--raw` opts into including the raw Algolia payload.

### Config

```python
# Added to Settings.__init__
self.algolia_base_url: str = os.environ.get(
    "HNX_ALGOLIA_BASE_URL", "https://hn.algolia.com/api/v1"
)
```

### Error handling

Reuses existing error types — no new error classes:
- `NotFoundError` (exit 5) — story_id returns null/404
- `UpstreamError` (exit 3) — Algolia HTTP failure
- `InvalidInputError` (exit 6) — id exists but is not a story root
- `TransformError` (exit 4) — unexpected response structure

### Safety

Full tree output is the default, but the CLI provides two optional controls for large threads:

- `--max-depth N` — include comments through depth `N` where top-level comments are depth `1`
- `--max-comments N` — include at most `N` comments in pre-order traversal

Pruning affects `data.children`; the raw Algolia payload is only present when `--raw` is passed and remains unpruned. `meta.truncated`, `meta.total_comment_count`, and `meta.returned_comment_count` let callers detect whether the normalized tree was shortened.

## Output contract

```json
{
  "ok": true,
  "data": {
    "type": "story",
    "id": 8863,
    "title": "My YC app: Dropbox",
    "url": "http://www.getdropbox.com/u/2/screencast.html",
    "author": "dhouston",
    "score": 117,
    "created_at": "2007-04-04T19:16:40.000Z",
    "hn_url": "https://news.ycombinator.com/item?id=8863",
    "text": null,
    "comment_count": 71,
    "children": [
      {
        "type": "comment",
        "id": 8865,
        "author": "dhouston",
        "created_at": "2007-04-04T19:22:55.000Z",
        "hn_url": "https://news.ycombinator.com/item?id=8865",
        "parent": 8863,
        "story_id": 8863,
        "text": "oh, and a mac port is coming :)",
        "score": null,
        "children": [...]
      }
    ]
  },
  "query": {"command": "thread", "story_id": 8863, "max_depth": null, "max_comments": null, "raw": false},
  "meta": {
    "type": "story",
    "total_comment_count": 71,
    "returned_comment_count": 71,
    "truncated": false,
    "max_depth": null,
    "max_comments": null
  },
  "raw": null
}
```

## Testing plan

- `tests/hnx/test_algolia_client.py` — use `httpx.MockTransport`, verify:
  - `GET /items/{id}` path construction
  - 200 dict response returns dict
  - 404 returns `None`
  - 4xx/5xx except 404 raise `UpstreamError`
  - `httpx.HTTPError` raises `UpstreamError`
  - invalid JSON and non-dict JSON raise `UpstreamError`
- `tests/hnx/test_thread_command.py` — mock `AlgoliaClient.fetch_thread()`, verify:
  - Successful thread envelope structure
  - Nested children correctly normalized
  - `comment_count` matches actual returned children
  - `meta.total_comment_count`, `meta.returned_comment_count`, and `meta.truncated`
  - `hn_url` format correct for all items
  - `NotFoundError` for missing story_id
  - `UpstreamError` for HTTP failures
  - `InvalidInputError` for non-story ids
  - raw payload is `null` by default and included with `--raw`
- `tests/hnx/test_transform.py` — add tests for `normalize_algolia_comment()` and `normalize_algolia_thread()`
- `tests/hnx/test_transform.py` — add pruning tests for `max_depth` and `max_comments`
- `tests/hnx/test_models.py` — add round-trip serialization tests for `ThreadedComment` and `ThreadRoot`
- `tests/hnx/test_config.py` — verify `HNX_ALGOLIA_BASE_URL`
- `tests/hnx/test_cli.py` — verify command registration, pruning flags, and JSON stderr mapping

## Estimated effort

| Component | Lines | Effort |
|-----------|-------|--------|
| `algolia_client.py` | ~40 | Low |
| `models.py` additions | ~30 | Low |
| `transform.py` additions | ~40 | Low |
| `commands/thread.py` | ~30 | Low |
| `cli.py` registration | ~35 | Low |
| `config.py` addition | ~1 | Trivial |
| Tests | ~240 | Medium |
| Docs | ~60 | Low |
| **Total** | **~480** | **Medium** |
