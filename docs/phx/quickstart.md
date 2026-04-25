# phx quickstart

`phx` is a JSON-first CLI that wraps the official [Product Hunt GraphQL API](https://api.producthunt.com/v2/docs) for agent workflows. It ships alongside `twx` and `hnx` in this repo.

## Install

```bash
git clone https://github.com/tpiperatgod/twx.git
cd twx

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

## Environment

| Variable | Required | Default |
|----------|----------|---------|
| `PRODUCTHUNT_TOKEN` | Yes | — |
| `PHX_API_BASE_URL` | No | `https://api.producthunt.com/v2/api/graphql` |
| `PHX_DEFAULT_LIMIT` | No | `20` |

Get a developer token from the [Product Hunt API dashboard](https://api.producthunt.com/v2/oauth/applications).

```bash
export PRODUCTHUNT_TOKEN="your-token"
```

## Examples

Fetch today's Product Hunt launches (current Product Hunt day in `America/Los_Angeles`):

```bash
phx launches --limit 20
```

Fetch launches for a specific Product Hunt day:

```bash
phx launches --date 2026-04-24 --raw
```

Fetch one product by slug:

```bash
phx product cursor
```

Fetch one product by opaque GraphQL id:

```bash
phx product "post-abc123" --id
```

## Defaults

- When no `--date`, `--after`, or `--before` flag is supplied, `phx launches` defaults to the current Product Hunt day, which starts and ends at local midnight in `America/Los_Angeles`.
- v1 uses only the official Product Hunt GraphQL API and does not auto-paginate. Pagination metadata is exposed under `meta.page_info` for consumers that want to implement their own pagination.

See [`commands.md`](commands.md) for the full flag reference and [`contracts.md`](contracts.md) for the output envelope.
