[简体中文](README.md) | **English**

# twx

`twx` is a JSON-first Twitter/X CLI for harness agents and automation workflows. It wraps the
[twitterapi.io](https://twitterapi.io) read APIs and writes stable, machine-readable JSON to stdout.

The project is intentionally small:

- No database
- No web server
- No task queue
- No interactive prompts
- No human-only rich output

If you need a CLI that agents can install quickly, call repeatedly, and parse reliably, `twx` is built for that shape.

## Quick Start

Prerequisites:

- Python 3.10+
- A [twitterapi.io](https://twitterapi.io) API key

Install:

```bash
git clone https://github.com/tpiperatgod/twx.git
cd twx

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

Set the API key and run a few commands:

```bash
export TWITTER_API_KEY=your_twitterapi_io_key

twx user --username karpathy --limit 10
twx search --query "AI agents" --mode top --limit 5
twx trending --ranking engagement --limit 20
```

For full setup, environment variables, and more examples, see [Quickstart](docs/quickstart.md).

## Why It Works Well For Harnesses

- Successful runs always emit a single JSON object on stdout.
- Failures emit structured JSON on stderr.
- Exit codes are stable and easy to automate against.
- Tweets are normalized into a predictable schema.
- `--raw` can include the upstream payload for debugging and migrations.

See [Contracts](docs/contracts.md) for the exact integration contract.

## Documentation

- [Documentation Index](docs/README.md)
- [Quickstart](docs/quickstart.md)
- [Commands](docs/commands.md)
- [Contracts](docs/contracts.md)
- [Limitations](docs/limitations.md)
- [Development](docs/development.md)

## At A Glance

- `twx user`: fetch a user's timeline
- `twx search`: search tweets by query
- `twx trending`: return the current `"trending"` search results, optionally re-ranked by engagement

See [Commands](docs/commands.md) for command examples and flags.

## Claude Code Skill

The repo ships with a Claude Code skill at [`.claude/skills/twitter-daily-report/`](.claude/skills/twitter-daily-report/SKILL.md) that turns `twx` into an automated daily Tech Twitter digest.

Ask Claude Code for "today's report" / "技术推特日报" and it runs the full pipeline:

1. Fetch a curated set of tech Twitter accounts in parallel (`twx user` × N).
2. Score each tweet with `♥ + 2×🔁 + 3×💬` and pick headlines.
3. Render a markdown report at `docs/reports/daily-YYYY-MM-DD.md`.

The account list is encoded in `scripts/fetch_tweets.sh` (`ACCOUNTS`) and `scripts/analyze.py` (`ROLES`, `DISPLAY_NAMES`) — edit both to customize. Personal watchlists under `watchlists/` are gitignored.

## License

MIT
