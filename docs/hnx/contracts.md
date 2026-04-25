# hnx Output Contracts

## Success envelope (stdout, exit 0)

```python
{
  "ok": true,
  "data": <NormalizedItem | list[NormalizedItem] | list[int]>,
  "query": <dict>,      # echo of command args
  "meta": <dict>,       # execution metadata
  "raw": <ListRaw | dict | null>,
}
```

Shape rules:

- `hnx top/new/best` → `data` is `list[NormalizedItem]`, or `list[int]` when `--ids-only`. `raw` is `ListRaw`.
- `hnx item <id>` → `data` is a **single** `NormalizedItem`. `raw` is the HN item response.
- `hnx thread <id>` → `data` is a **single** `ThreadRoot` with nested `ThreadedComment.children`. `raw` is the Algolia search payload (defaults to `null`, included only with `--raw`).
- There is **no `paging` key** — HN has no cursor pagination.

### `ListRaw`

```python
{
  "ids": list[int],                    # full id list returned by HN (up to 500), pre-limit
  "items": list[dict | None] | null,   # same order and length as ids[:limit]; null entries if HN returned null; whole field is null when --ids-only
}
```

## Normalized item types

All share `type`, `id`, `hn_url`. See [`hnx/models.py`](../../hnx/models.py) for the definitive Pydantic definitions.

- `story` — title, url, author, score, comment_count, created_at, text, kids
- `comment` — author, created_at, parent, text, kids
- `job` — title, url, author, score, created_at, text
- `poll` — title, author, score, comment_count, created_at, text, parts
- `pollopt` — author, parent, score, created_at, text
- `tombstone` — `original_type`, `deleted`, `dead`, and best-effort id/created_at/parent/author. Only surfaced when `--include-deleted` is set.

## Thread output types (from `hnx thread`)

### `ThreadRoot`

Returned by `hnx thread <story_id>`. Represents a story with its full comment tree.

- `type` — `"thread_root"`
- `id` — story id (int)
- `title` — story title (str)
- `url` — external URL or `null` (str | null)
- `author` — username (str)
- `score` — upvote count (int)
- `comment_count` — total comment count (int)
- `created_at` — ISO 8601 timestamp (str)
- `hn_url` — permalink to HN discussion (str)
- `text` — story text or `null` (str | null)
- `children` — list of `ThreadedComment` (nested recursively)

### `ThreadedComment`

Nested comment in a thread tree.

- `type` — `"threaded_comment"`
- `id` — comment id (int)
- `author` — username (str)
- `created_at` — ISO 8601 timestamp (str)
- `hn_url` — permalink to comment (str)
- `parent` — parent comment id or story id (int)
- `story_id` — root story id (int)
- `text` — comment text (str)
- `score` — upvote count (int)
- `children` — list of `ThreadedComment` (nested recursively)

## Error envelope (stderr, non-zero exit)

```python
{
  "ok": false,
  "error": {
    "type": "upstream_error" | "transform_error" | "not_found" | "filtered_out" | "invalid_input",
    "message": <str>,
    "details": <dict>,
  }
}
```

## Exit codes

| Code | `error.type` | Meaning |
|---|---|---|
| 0 | — | success |
| 3 | `upstream_error` | HTTP failure after retries |
| 4 | `transform_error` | upstream payload could not be normalized |
| 5 | `not_found` | `hnx item <id>` and HN returned `null`, or `hnx thread <id>` and the story does not exist |
| 6 | `invalid_input` | bad flag value, disallowed flag combination, or `hnx thread <id>` given a non-story ID |
| 7 | `filtered_out` | `hnx item <id>` and the item is deleted/dead without `--include-deleted` |
