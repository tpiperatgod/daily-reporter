# phx commands

All phx commands write a success envelope to stdout as a single line of JSON and exit `0`. On failure they write an error envelope to stderr and exit with a non-zero code (see [contracts.md](contracts.md)).

## `phx launches`

Fetch a page of Product Hunt launches for a day or explicit datetime window.

### Flags

| Flag | Type | Description |
|------|------|-------------|
| `--date` | `YYYY-MM-DD` | Product Hunt day, interpreted in `America/Los_Angeles`. |
| `--after` | ISO 8601 | Timezone-aware start datetime of a custom window. Must be paired with `--before`. |
| `--before` | ISO 8601 | Timezone-aware end datetime of a custom window. Must be paired with `--after`. |
| `--limit` | integer ≥ 1 | Number of launches to fetch. Defaults to `PHX_DEFAULT_LIMIT` (or `20`). |
| `--raw` | flag | Include the raw Product Hunt GraphQL response under `raw`. |

### Validation rules

- `--date` cannot be combined with `--after` / `--before`.
- `--after` and `--before` must be provided together; passing only one is an error.
- When `--after` / `--before` are supplied, both must be timezone-aware ISO 8601 datetimes and `--after` must be strictly less than `--before`.
- When neither `--date` nor `--after` / `--before` is provided, phx uses the current Product Hunt day from `America/Los_Angeles`.

Invalid flag combinations produce an `invalid_input` error envelope on stderr and exit `6`.

### Examples

```bash
phx launches                                   # today's Product Hunt day
phx launches --date 2026-04-24                 # specific Product Hunt day
phx launches --after 2026-04-24T00:00:00-07:00 \
             --before 2026-04-25T00:00:00-07:00
phx launches --limit 50 --raw
```

## `phx product <ref>`

Fetch one Product Hunt product by slug or GraphQL id.

### Arguments

| Argument | Description |
|----------|-------------|
| `REF` | Either the post slug (e.g. `cursor`) or the GraphQL id. |

### Flags

| Flag | Type | Description |
|------|------|-------------|
| `--id` | flag | Force `REF` to be treated as a GraphQL id. Mutually exclusive with `--slug`. |
| `--slug` | flag | Force `REF` to be treated as a slug. Mutually exclusive with `--id`. |
| `--raw` | flag | Include the raw Product Hunt GraphQL response under `raw`. |

### Ref classification

When neither `--id` nor `--slug` is supplied, phx classifies `REF` automatically:

- All-digit refs are treated as GraphQL ids.
- All other refs are treated as slugs.

The resolved classification is reflected in the success envelope:

| `query.ref_source` | Meaning |
|--------------------|---------|
| `auto` | classified heuristically from the ref |
| `explicit` | forced via `--id` or `--slug` |

Passing both `--id` and `--slug` produces an `invalid_input` error (exit `6`).

When the API returns a `null` post, phx emits a `not_found` error (exit `5`).

### Examples

```bash
phx product cursor                 # auto slug
phx product 123456                 # auto id
phx product cursor --slug          # explicit slug
phx product opaque-id --id         # force id for a non-digit ref
phx product cursor --raw           # include raw GraphQL payload
```

## stdout / stderr

- Success payloads go to **stdout** as a single JSON line and the process exits `0`.
- Failures write a JSON error envelope to **stderr** and exit with a non-zero code.
- stdout and stderr are never mixed, so shell redirection (`> out.json 2> err.json`) works cleanly.
