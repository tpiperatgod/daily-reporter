# Development

This page is for contributors working on the repository itself.

## Local Setup

Install the project with dev dependencies:

```bash
python -m pip install -e '.[dev]'
```

## Test Commands

Run the full test suite:

```bash
pytest tests/twx tests/hnx tests/phx -v
```

Run a single test file:

```bash
pytest tests/twx/test_transform.py -v
```

Run tests by keyword:

```bash
pytest tests/twx -k "test_normalize" -v
```

## Lint And Format

```bash
ruff check twx hnx phx tests/twx tests/hnx tests/phx
ruff format --check twx hnx phx tests/twx tests/hnx tests/phx
ruff format twx hnx phx tests/twx tests/hnx tests/phx
```

## Project Layout

```text
twx/
├── cli.py
├── client.py
├── config.py
├── errors.py
├── models.py
├── state.py
├── transform.py
└── commands/
    ├── user.py
    ├── search.py
    └── trending.py
```

Tests live in `tests/twx/`.

## Related Docs

- [Documentation Index](README.md)
- [中文首页](../README.md)
- [English Home](../README.en.md)
