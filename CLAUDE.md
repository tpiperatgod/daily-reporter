# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`twx` is a JSON-first CLI that wraps [twitterapi.io](https://twitterapi.io) read APIs for agent workflows. No database, no web server, no task queue — just a CLI that outputs stable JSON to stdout.

**Tech stack:** Python 3.10+, Click, httpx, Pydantic v2, pytest, Ruff

## Developer Commands

```bash
pip install -e .                              # Install CLI (provides `twx` command)
pip install -r requirements.txt               # Install all deps (includes pytest, ruff)

pytest tests/twx -v                           # Run all 72 tests
pytest tests/twx/test_transform.py -v         # Run single test file
pytest tests/twx -k "test_normalize" -v       # Run tests matching pattern

ruff check twx tests/twx                      # Lint
ruff format --check twx tests/twx             # Check formatting
ruff format twx tests/twx                     # Apply formatting
```

CI runs on Python 3.11: lint → format check → test. No services needed (no Postgres, Redis, Docker).

## Architecture

```
twx/
├── cli.py           # Click group entrypoint, registers user/search/trending commands
├── client.py        # TwitterApiClient — httpx wrapper for twitterapi.io
├── config.py        # Settings class (reads TWITTER_API_KEY, TWX_API_BASE_URL, TWX_DEFAULT_LIMIT)
├── errors.py        # TWXError hierarchy: ConfigError(2), UpstreamError(3), TransformError(4)
├── models.py        # Pydantic models: NormalizedTweet, SuccessEnvelope, ErrorEnvelope
├── state.py         # load_state/save_state for --state-file checkpoint JSON
├── transform.py     # normalize_tweet(), extract_metrics(), extract_media(), parse_created_at()
└── commands/
    ├── user.py      # fetch_user_tweets() — fetch, normalize, filter by since/until, limit
    ├── search.py    # fetch_search_tweets() — search, normalize, limit
    └── trending.py  # fetch_trending_tweets() + rank_by_engagement()
```

Tests mirror the package: `tests/twx/test_<module>.py`.

## Key Patterns

### Command execution flow

Every command follows the same pattern:
1. `Settings()` → `require_api_key()` → `TwitterApiClient(api_key=, base_url=)`
2. Client calls upstream API → returns raw dict
3. Command extracts tweets from response (with fallback — see below)
4. `normalize_tweet()` per tweet → `SuccessEnvelope` with `model_dump_json()` to stdout
5. Errors → `TWXError` subclass → `_handle_error()` writes JSON to stderr + exit code

### Upstream response structure varies by endpoint

The twitterapi.io API returns tweets in different locations depending on the endpoint:
- **User timeline**: `response.data.tweets` (dict containing a tweets array)
- **Search**: `response.tweets` at top level, OR `response.data.tweets`

All commands use a fallback chain: check `response.data.tweets`, then `response.data` if it's a list, then `response.tweets`.

### Upstream field names are camelCase

twitterapi.io uses camelCase: `likeCount`, `retweetCount`, `replyCount`, `viewCount`, `bookmarkCount`, `isReply`, `isQuoteStatus`, `createdAt`, `userName`.

`extract_metrics()` and `normalize_tweet()` have fallback lookups for snake_case variants but the canonical upstream names are camelCase.

### Error hierarchy

| Error | Exit code | `error_type` | When |
|-------|-----------|-------------|------|
| `ConfigError` | 2 | `config_error` | Missing `TWITTER_API_KEY` |
| `UpstreamError` | 3 | `upstream_error` | HTTP failures, rate limits (429/5xx retryable) |
| `TransformError` | 4 | `transform_error` | Failed to normalize upstream data |

### State/checkpoint

`--state-file path.json` enables incremental reads. The file stores `since_id` (highest tweet ID seen). On next run, the checkpoint is loaded but currently not used to filter (future enhancement).

## Conventions

- **Output contract is stable**: Success envelope keys (`ok`, `data`, `paging`, `query`, `meta`, `raw`) must not change. Breaking the envelope breaks downstream consumers.
- **Success → stdout, errors → stderr**: Never mix them.
- **No interactive prompts, no rich tables, no databases**: This is a pipe-friendly CLI for agents.
- **Ruff config**: line-length 120, double quotes, ignore E501/E402/E712.
- **Test paths**: `tests/twx/` only (configured in `pyproject.toml` `testpaths`).

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `TWITTER_API_KEY` | Yes | — |
| `TWX_API_BASE_URL` | No | `https://api.twitterapi.io` |
| `TWX_DEFAULT_LIMIT` | No | `20` |

## Adding a New Command

1. Add `fetch_xxx()` function in `twx/commands/xxx.py` — follow the same pattern as `user.py`
2. Import and call `TwitterApiClient` method; add the method to `twx/client.py` if needed
3. Normalize via `transform.normalize_tweet()`, wrap in `SuccessEnvelope`
4. Add Click command in `twx/cli.py` — same try/except pattern as existing commands
5. Add tests in `tests/twx/test_xxx_command.py` — mock the client, verify envelope structure
6. Add a `test_repo_cleanup` check if the command removes legacy artifacts

## Companion Skill

`.claude/skills/twitter-daily-report/` is a Claude Code skill that consumes `twx` to generate a daily Tech Twitter digest. It's a separate layer from the CLI: the CLI is the open-source library, the skill is the orchestration on top.

- `SKILL.md` + `scripts/fetch_tweets.sh` + `scripts/analyze.py` + `report-template.md` — tracked in git, part of the open-source release.
- `scripts/fetch_tweets.sh` holds the `ACCOUNTS` array; `scripts/analyze.py` holds `ROLES` and `DISPLAY_NAMES`. These are the canonical account list — drift between them is the top source of report bugs.
- `watchlists/*.md` and `docs/daily-report-sop.md` are gitignored personal curation / internal workflow notes. Don't duplicate their content into the skill or CLI docs.

When a user asks for "today's report", "技术推特日报", or similar, the skill is invoked — not the CLI directly. CLI changes that affect the output envelope will break the skill's `analyze.py` parser, so preserve the success-envelope keys religiously.

## Known Gaps

- `twx trending` searches for the literal query "trending" — it does not use the real `/twitter/trends` endpoint (WOEID-based). This is a candidate for a future `twx trends` command.
- `since_id` from state file is saved but not used to filter upstream requests yet.
- No pagination support — only the first page of results is fetched.
