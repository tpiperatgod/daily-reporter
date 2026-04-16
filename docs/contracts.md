# Contracts

This page describes the stable machine-readable contract that harness agents should rely on.

## Success Contract

On success, `twx` writes a single JSON object to stdout with these top-level keys:

- `ok`
- `data`
- `paging`
- `query`
- `meta`
- `raw`

Example:

```json
{
  "ok": true,
  "data": {
    "tweets": [
      {
        "id": "1900000000000000000",
        "text": "Hello world! This is a test tweet.",
        "url": "https://x.com/karpathy/status/1900000000000000000",
        "author_username": "karpathy",
        "author_name": "Andrej Karpathy",
        "created_at": "2026-04-15T12:00:00+00:00",
        "metrics": {
          "like_count": 4200,
          "retweet_count": 800,
          "reply_count": 150,
          "view_count": 500000,
          "bookmark_count": 200
        },
        "media": [
          {
            "type": "photo",
            "url": "https://pbs.twimg.com/img/test.jpg",
            "alt_text": "A test image"
          }
        ],
        "is_retweet": false,
        "is_reply": false,
        "is_quote": false
      }
    ]
  },
  "paging": {
    "next_cursor": null,
    "has_more": false
  },
  "query": {
    "command": "user",
    "username": "karpathy",
    "since": null,
    "until": null,
    "limit": 10
  },
  "meta": {
    "count": 1
  },
  "raw": null
}
```

## Normalized Tweet Shape

Each element in `data.tweets[]` is normalized to this schema:

- `id`
- `text`
- `url`
- `author_username`
- `author_name`
- `created_at`
- `metrics.like_count`
- `metrics.retweet_count`
- `metrics.reply_count`
- `metrics.view_count`
- `metrics.bookmark_count`
- `media[]`
- `is_retweet`
- `is_reply`
- `is_quote`

## Error Contract

On failure, `twx` writes structured JSON to stderr and exits non-zero.

Example:

```json
{
  "ok": false,
  "error": {
    "type": "config_error",
    "message": "TWITTER_API_KEY environment variable is required",
    "retryable": false
  }
}
```

## Exit Codes

| Exit code | Error type | Meaning |
| --- | --- | --- |
| `1` | `internal_error` | Unexpected internal failure |
| `2` | `config_error` | Missing or invalid local configuration |
| `3` | `upstream_error` | twitterapi.io request failed or rate-limited |
| `4` | `transform_error` | Upstream data could not be normalized |

## Harness Integration Pattern

The intended control flow is:

1. Check the process exit code.
2. If exit code is `0`, parse stdout as success JSON.
3. If exit code is non-zero, parse stderr as error JSON.

This keeps success and failure handling clean and predictable in agent pipelines.

## Related Docs

- [Quickstart](quickstart.md)
- [Commands](commands.md)
- [Limitations](limitations.md)
