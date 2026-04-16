# twx

JSON-first Twitter/X CLI wrapping the [twitterapi.io](https://twitterapi.io) read APIs. Designed for agent workflows and pipe-friendly output.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
export TWITTER_API_KEY=your_key_here

# Fetch recent tweets from a user
twx user --username karpathy --limit 10

# Search tweets
twx search --query "AI agents" --mode top --limit 5

# Get trending tweets ranked by engagement
twx trending --ranking engagement --limit 20
```

## Commands

### `twx user`

Fetch tweets from a user timeline.

```bash
twx user --username karpathy --limit 20
twx user --username karpathy --since 2026-04-15T00:00:00Z --until 2026-04-16T00:00:00Z
twx user --username karpathy --include-replies --raw
```

Options:
- `--username` (required): Twitter username
- `--limit`: Max tweets to return (default: 20)
- `--since`: Only tweets after this ISO timestamp
- `--until`: Only tweets before this ISO timestamp
- `--include-replies`: Include reply tweets
- `--state-file`: Checkpoint file for incremental reads
- `--raw`: Include raw upstream payload

### `twx search`

Search tweets by query.

```bash
twx search --query "AI agents" --mode top --limit 10
```

Options:
- `--query` (required): Search query string
- `--mode`: `latest` or `top` (default: `latest`)
- `--limit`: Max tweets to return (default: 20)
- `--state-file`: Checkpoint file for incremental reads
- `--raw`: Include raw upstream payload

### `twx trending`

Fetch trending tweets with ranking options.

```bash
twx trending --ranking engagement --limit 20
```

Options:
- `--ranking`: `upstream` or `engagement` (default: `upstream`)
- `--limit`: Max tweets to return (default: 20)
- `--state-file`: Checkpoint file for incremental reads
- `--raw`: Include raw upstream payload

## Output Format

All commands output a JSON envelope to stdout:

```json
{
  "ok": true,
  "data": { "tweets": [] },
  "paging": { "next_cursor": null, "has_more": false },
  "query": { "command": "user", "username": "karpathy" },
  "meta": { "count": 10 },
  "raw": null
}
```

Errors go to stderr with structured JSON:

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

The success envelope is represented by the `SuccessEnvelope` model in `twx.models`, with stable top-level keys: `ok`, `data`, `paging`, `query`, `meta`, and `raw`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWITTER_API_KEY` | Yes | API key from twitterapi.io |
| `TWX_API_BASE_URL` | No | Override base URL (default: `https://api.twitterapi.io`) |
| `TWX_DEFAULT_LIMIT` | No | Default tweet limit (default: `20`) |

## Checkpoint State

Use `--state-file` to enable incremental reads:

```bash
twx user --username karpathy --state-file checkpoint.json
```

After a successful run, the state file is updated with checkpoint data (for example `since_id`). On the next run, the command reads the checkpoint to resume from where it left off.

## Development

```bash
pip install -r requirements.txt
pytest tests/twx -v
ruff check twx tests/twx
ruff format --check twx tests/twx
```

## License

MIT
