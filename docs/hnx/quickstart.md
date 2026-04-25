# hnx Quickstart

`hnx` is a JSON-first CLI that wraps the public [HackerNews API](https://github.com/HackerNews/API). It ships alongside `twx` in the same repo and is installed by the same `pip install`.

## Install

```bash
pip install -e .
hnx --help
```

No API key is required — HN's API is unauthenticated.

## First invocation

```bash
# Top 5 stories, fully hydrated
hnx top --limit 5

# Pipe to jq for titles + urls
hnx top --limit 10 | jq '.data[] | {title, url, score}'

# Just the ids (no N+1 hydrate requests)
hnx top --limit 30 --ids-only

# Single item
hnx item 39000000

# Fetch full comment thread for a story
hnx thread 39000000

# With depth limit and raw payload
hnx thread 39000000 --max-depth 3 --raw
```

## Environment variables

| Variable | Default |
|---|---|
| `HNX_API_BASE_URL` | `https://hacker-news.firebaseio.com/v0` |
| `HNX_DEFAULT_LIMIT` | `30` |
| `HNX_CONCURRENCY` | `10` |

Set `HNX_API_BASE_URL` to point at a local mock / caching proxy during development.

## Exit codes

See [contracts.md](contracts.md) for the full list. Common:

- `0` — success
- `3` — upstream HTTP failure (after retries)
- `5` — `hnx item <id>` and the id does not exist
- `7` — `hnx item <id>` and the item is deleted/dead (pass `--include-deleted` to surface it as a tombstone)
