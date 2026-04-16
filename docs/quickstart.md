# Quickstart

This guide is for users and harness agents that want to install `twx` and start calling it immediately.

## Prerequisites

- Python 3.10+
- A [twitterapi.io](https://twitterapi.io) API key

## Install From Source

```bash
git clone https://github.com/tpiperatgod/x-news-digest.git
cd x-news-digest

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

After installation, the `twx` command is available in the active environment.

## Install With Dev Dependencies

```bash
python -m pip install -e '.[dev]'
```

This installs `pytest` and `ruff` in addition to the CLI runtime dependencies.

## Environment Variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `TWITTER_API_KEY` | Yes | none | API key for twitterapi.io |
| `TWX_API_BASE_URL` | No | `https://api.twitterapi.io` | Override the upstream base URL |
| `TWX_DEFAULT_LIMIT` | No | `20` | Parsed by config, but current subcommand defaults are still hard-coded to `20` unless `--limit` is passed |

Export the required key before running commands:

```bash
export TWITTER_API_KEY=your_twitterapi_io_key
```

## 60-Second Examples

Fetch a user timeline:

```bash
twx user --username karpathy --limit 10
```

Search tweets:

```bash
twx search --query "AI agents" --mode top --limit 5
```

Fetch trending tweets:

```bash
twx trending --ranking engagement --limit 20
```

Show CLI help:

```bash
twx --help
twx user --help
twx search --help
twx trending --help
```

## Common Harness Patterns

Write the success payload to a file:

```bash
twx user --username karpathy --limit 20 > tweets.json
```

Capture stdout and stderr separately:

```bash
twx search --query "open source agents" --limit 10 \
  1>result.json \
  2>error.json
```

Include the upstream payload for debugging:

```bash
twx search --query "AI agents" --mode latest --raw > result-with-raw.json
```

Persist checkpoint state:

```bash
twx user --username karpathy --state-file .twx-state.json > tweets.json
```

## Next Reading

- [Commands](commands.md)
- [Contracts](contracts.md)
- [Limitations](limitations.md)
- [中文首页](../README.md)
- [English Home](../README.en.md)
