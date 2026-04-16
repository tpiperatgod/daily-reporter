# Commands

`twx` currently exposes three read-oriented commands: `user`, `search`, and `trending`.

## Cheat Sheet

| Command | Purpose | Required flags | Useful optional flags |
| --- | --- | --- | --- |
| `twx user` | Fetch a user's recent tweets | `--username` | `--limit`, `--since`, `--until`, `--include-replies`, `--state-file`, `--raw` |
| `twx search` | Search tweets by query | `--query` | `--mode latest|top`, `--limit`, `--state-file`, `--raw` |
| `twx trending` | Return trending tweets | none | `--ranking upstream|engagement`, `--limit`, `--state-file`, `--raw` |

## twx user

Fetch tweets from a user timeline.

Examples:

```bash
twx user --username karpathy --limit 20
twx user --username karpathy --since 2026-04-15T00:00:00Z --until 2026-04-16T00:00:00Z
twx user --username karpathy --include-replies --raw
```

Flags:

- `--username`: required username to fetch
- `--limit`: maximum tweets to return
- `--since`: only include tweets on or after this ISO timestamp
- `--until`: only include tweets on or before this ISO timestamp
- `--include-replies`: include replies in the upstream request
- `--state-file`: persist checkpoint metadata to a local JSON file
- `--raw`: include the original upstream payload in the success envelope

## twx search

Search tweets by query.

Examples:

```bash
twx search --query "AI agents" --mode latest --limit 10
twx search --query "open source" --mode top --raw
```

Flags:

- `--query`: required search string
- `--mode`: `latest` or `top`
- `--limit`: maximum tweets to return
- `--state-file`: persist checkpoint metadata to a local JSON file
- `--raw`: include the original upstream payload in the success envelope

## twx trending

Fetch trending tweets.

Examples:

```bash
twx trending --limit 20
twx trending --ranking engagement --limit 20
```

Flags:

- `--ranking`: `upstream` or `engagement`
- `--limit`: maximum tweets to return
- `--state-file`: persist checkpoint metadata to a local JSON file
- `--raw`: include the original upstream payload in the success envelope

## Related Docs

- [Quickstart](quickstart.md)
- [Contracts](contracts.md)
- [Limitations](limitations.md)
