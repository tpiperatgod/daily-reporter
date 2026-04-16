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

## License

MIT
