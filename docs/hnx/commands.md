# hnx Commands

## `hnx top` / `hnx new` / `hnx best`

Fetch a hydrated story list. `top` / `new` / `best` are thin wrappers over the same underlying flow; they differ only in which HN list endpoint they hit (`/topstories.json`, `/newstories.json`, `/beststories.json`).

### Flags

| Flag | Default | Description |
|---|---|---|
| `--limit N` | `HNX_DEFAULT_LIMIT` (30) | Take first N ids from the list and hydrate. Caps silently at the list length (HN returns at most 500); caps are reported via `meta.limit_capped`. |
| `--concurrency N` | `HNX_CONCURRENCY` (10) | Concurrent item-hydration requests. |
| `--ids-only` | off | Skip hydration; `data` is a raw `[int, int, ...]`. Cannot be combined with `--include-deleted`. |
| `--include-deleted` | off | Include items with `deleted:true` or `dead:true`, surfaced as `NormalizedTombstone` in `data`. |

### Example envelope (`hnx top --limit 2`)

```json
{
  "ok": true,
  "data": [
    {
      "type": "story",
      "id": 100,
      "title": "Example",
      "url": "https://example.com",
      "author": "dang",
      "score": 42,
      "comment_count": 5,
      "created_at": "2026-04-22T12:00:00+00:00",
      "hn_url": "https://news.ycombinator.com/item?id=100",
      "text": null,
      "kids": [101, 102]
    }
  ],
  "query": {
    "command": "top",
    "source": "top",
    "limit": 2,
    "concurrency": 10,
    "ids_only": false,
    "include_deleted": false
  },
  "meta": {
    "source": "top",
    "limit": 2,
    "fetched": 2,
    "returned": 1,
    "filtered_deleted": 1,
    "missing": 0,
    "transform_errors": 0,
    "types": {"story": 1},
    "concurrency": 10,
    "limit_capped": false
  },
  "raw": {
    "ids": [100, 101, 102, "..."],
    "items": [{"id": 100, "...": "..."}, {"id": 101, "...": "..."}]
  }
}
```

## `hnx item <id>`

Fetch a single item. `data` is a **single** object (not a list). Works for any item type: story / comment / job / poll / pollopt / tombstone.

### Flags

| Flag | Default | Description |
|---|---|---|
| `--include-deleted` | off | If the item is `deleted:true` or `dead:true`, return it as a `NormalizedTombstone` instead of raising `filtered_out`. |

### Behavior table

| Upstream response | `--include-deleted` | Result |
|---|---|---|
| normal item | n/a | exit 0, `data` is the normalized item |
| `null` | n/a | exit 5, `error.type = "not_found"` |
| `deleted:true` or `dead:true` | off | exit 7, `error.type = "filtered_out"`, `error.details = {"deleted": bool, "dead": bool}` |
| `deleted:true` or `dead:true` | on | exit 0, `data` is a `NormalizedTombstone` |

## `hnx thread <story_id>`

Fetch a full comment tree for a story via the Algolia API. `data` is a single `ThreadRoot` object with nested `ThreadedComment` children.

### Flags

| Flag | Default | Description |
|---|---|---|
| `--max-depth N` | unlimited | Maximum nesting depth for comment threads. Truncates deeper branches and reports `meta.depth_capped`. |
| `--max-comments N` | unlimited | Maximum total comments to return. Cuts off at depth limit and reports `meta.comments_capped`. |
| `--raw` | off | Include the full Algolia search response in `raw`. Defaults to `null` without this flag. |

### Behavior table

| Upstream response | Result |
|---|---|
| story exists | exit 0, `data` is `ThreadRoot` with nested `ThreadedComment.children` |
| id is not a story (comment/job/etc.) | exit 6, `error.type = "invalid_input"`, `error.details = {"reason": "not_a_story"}` |
| story not found | exit 5, `error.type = "not_found"` |

### Example envelope (`hnx thread 39000000 --max-depth 2`)

```json
{
  "ok": true,
  "data": {
    "type": "thread_root",
    "id": 39000000,
    "title": "Example Story",
    "url": "https://example.com",
    "author": "dang",
    "score": 100,
    "comment_count": 42,
    "created_at": "2026-04-22T12:00:00+00:00",
    "hn_url": "https://news.ycombinator.com/item?id=39000000",
    "text": null,
    "children": [
      {
        "type": "threaded_comment",
        "id": 39000001,
        "author": "commenter1",
        "created_at": "2026-04-22T12:30:00+00:00",
        "hn_url": "https://news.ycombinator.com/item?id=39000001",
        "parent": 39000000,
        "story_id": 39000000,
        "text": "First comment",
        "score": 10,
        "children": [
          {
            "type": "threaded_comment",
            "id": 39000002,
            "author": "commenter2",
            "created_at": "2026-04-22T13:00:00+00:00",
            "hn_url": "https://news.ycombinator.com/item?id=39000002",
            "parent": 39000001,
            "story_id": 39000000,
            "text": "Reply to first comment",
            "score": 5,
            "children": []
          }
        ]
      }
    ]
  },
  "query": {
    "command": "thread",
    "story_id": 39000000,
    "max_depth": 2,
    "max_comments": null,
    "raw": false
  },
  "meta": {
    "total_comments": 42,
    "returned_comments": 2,
    "depth_capped": false,
    "comments_capped": false
  },
  "raw": null
}
```
