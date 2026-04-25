# phx output contracts

`phx` emits a stable JSON envelope on stdout for successes and a separate JSON envelope on stderr for failures. Consumers (agents, pipelines, shell scripts) should rely on these shapes.

## Success envelope

```json
{
  "ok": true,
  "data": ...,
  "query": { ... },
  "meta": { ... },
  "raw": null
}
```

| Key | Description |
|-----|-------------|
| `ok` | Always `true` on success. |
| `data` | For `launches`, a list of `NormalizedLaunch` objects. For `product`, a single `ProductDetail` object. |
| `query` | Echoes the resolved command input so downstream tools can audit what was actually fetched. |
| `meta` | Metadata about the request: counts, pagination info, transform errors. |
| `raw` | The verbatim Product Hunt GraphQL response when `--raw` is passed, otherwise `null`. |

There is no top-level `paging` key. Pagination details (cursor, has-next) are exposed under `meta.page_info`.

### `NormalizedLaunch`

Returned by `phx launches`.

| Field | Type | Notes |
|-------|------|-------|
| `type` | `"launch"` | Discriminator literal. |
| `id` | string | Product Hunt GraphQL id. |
| `slug` | string | Canonical slug. |
| `name` | string | Product name. |
| `tagline` | string \| null | Short tagline. |
| `description` | string \| null | Longer description. |
| `product_hunt_url` | string | Canonical Product Hunt URL. |
| `website_url` | string \| null | External site. |
| `thumbnail_url` | string \| null | Thumbnail image URL. |
| `votes_count` | integer | Upvotes. |
| `comments_count` | integer | Comments. |
| `topics` | string[] | Topic names. |
| `makers` | string[] | Maker usernames (falls back to name). |
| `created_at` | string \| null | ISO 8601 creation timestamp from upstream. |
| `featured_at` | string \| null | ISO 8601 featured timestamp from upstream. |
| `ranking` | integer \| null | Daily rank within the launch window. |
| `featured` | boolean | `true` when `featured_at` is set. |

### `ProductDetail`

Returned by `phx product`.

Includes every `NormalizedLaunch` field plus:

| Field | Type | Notes |
|-------|------|-------|
| `type` | `"product"` | Discriminator literal. |
| `reviews_count` | integer \| null | |
| `reviews_rating` | float \| null | |
| `topics` | `TopicRef[]` | Structured topic refs. |
| `makers` | `MakerRef[]` | Structured maker refs. |
| `media` | `MediaRef[]` | Media gallery entries. |
| `product_links` | `ProductLinkRef[]` | Outgoing links (App Store, website, etc.). |
| `weekly_rank` | integer \| null | |
| `monthly_rank` | integer \| null | |
| `yearly_rank` | integer \| null | |

### Reference shapes

#### `TopicRef`

| Field | Type |
|-------|------|
| `id` | string |
| `name` | string |
| `slug` | string |
| `url` | string \| null |

#### `MakerRef`

| Field | Type |
|-------|------|
| `id` | string |
| `name` | string |
| `username` | string |
| `url` | string \| null |
| `twitter_username` | string \| null |
| `headline` | string \| null |
| `website_url` | string \| null |

#### `MediaRef`

| Field | Type |
|-------|------|
| `type` | string |
| `url` | string |
| `video_url` | string \| null |

#### `ProductLinkRef`

| Field | Type |
|-------|------|
| `type` | string |
| `url` | string |

## `query` and `meta` examples

`phx launches`:

```json
{
  "query": {
    "command": "launches",
    "date": "2026-04-24",
    "date_source": "explicit",
    "after": "2026-04-24T00:00:00-07:00",
    "before": "2026-04-25T00:00:00-07:00",
    "timezone": "America/Los_Angeles",
    "limit": 20,
    "featured": true,
    "order": "RANKING",
    "raw": false
  },
  "meta": {
    "source": "producthunt_graphql",
    "returned": 20,
    "limit": 20,
    "transform_errors": 0,
    "total_count": 47,
    "page_info": { "has_next_page": true, "end_cursor": "..." },
    "window": { "after": "...", "before": "..." }
  }
}
```

`query.date_source` is one of:

- `explicit` — set from `--date` or a `--after`/`--before` window.
- `default` — derived from the current Product Hunt day.

The date window is always computed against `America/Los_Angeles`.

`phx product`:

```json
{
  "query": {
    "command": "product",
    "ref": "cursor",
    "ref_type": "slug",
    "ref_source": "auto",
    "raw": false
  },
  "meta": { "source": "producthunt_graphql", "returned": 1 }
}
```

## Error envelope

```json
{
  "ok": false,
  "error": {
    "type": "config_error",
    "message": "PRODUCTHUNT_TOKEN environment variable is required",
    "details": {}
  }
}
```

## Error types and exit codes

| `error.type` | Exit code | When |
|-------------|-----------|------|
| `config_error` | 2 | Missing `PRODUCTHUNT_TOKEN` or invalid env values. |
| `upstream_error` | 3 | HTTP, transport, JSON, or GraphQL failure from Product Hunt. |
| `transform_error` | 4 | Upstream payload cannot be normalized. |
| `not_found` | 5 | Requested Product Hunt post does not exist. |
| `invalid_input` | 6 | Invalid flag combinations or bad input (e.g. `--id` and `--slug` together). |

## `raw` is opt-in

`raw` is `null` unless you pass `--raw`. When included, it contains the verbatim Product Hunt GraphQL response object (including `data`, `errors`, and any other top-level fields). It is intended for debugging and advanced consumers; prefer `data` / `query` / `meta` for stable integration.
