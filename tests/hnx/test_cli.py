"""Tests for the hnx Click CLI."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from hnx.cli import cli
from hnx.errors import FilteredError, InvalidInputError, NotFoundError
from hnx.models import SuccessEnvelope


def test_cli_help_exits_zero() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "JSON-first HackerNews CLI" in result.output


def test_top_emits_success_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_stories(**kwargs):
        return SuccessEnvelope(data=[], query={"command": "top"}, meta={"source": "top"}, raw={"ids": [], "items": []})

    monkeypatch.setattr("hnx.cli.fetch_stories", fake_fetch_stories)

    result = CliRunner().invoke(cli, ["top", "--limit", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["query"]["command"] == "top"
    assert result.stderr == ""


def test_top_reports_upstream_error_on_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    from hnx.errors import UpstreamError

    async def boom(**kwargs):
        raise UpstreamError("500 from upstream")

    monkeypatch.setattr("hnx.cli.fetch_stories", boom)

    result = CliRunner().invoke(cli, ["top"])

    assert result.exit_code == 3
    payload = json.loads(result.stderr)
    assert payload == {
        "ok": False,
        "error": {"type": "upstream_error", "message": "500 from upstream", "details": {}},
    }
    assert result.stdout == ""


def test_top_invalid_ids_only_with_include_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raising(**kwargs):
        raise InvalidInputError("--ids-only cannot be combined with --include-deleted")

    monkeypatch.setattr("hnx.cli.fetch_stories", raising)

    result = CliRunner().invoke(cli, ["top", "--ids-only", "--include-deleted"])

    assert result.exit_code == 6
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "invalid_input"


def test_top_limit_zero_rejected_by_click() -> None:
    # Click IntRange rejects this before the command body runs, so the
    # error travels through Click, not our handler. Exit code 2 is Click's
    # standard for usage errors; stderr is Click's usage text, not JSON.
    result = CliRunner().invoke(cli, ["top", "--limit", "0"])
    assert result.exit_code == 2
    assert "Invalid value" in result.stderr


def test_item_not_found_maps_to_exit_5(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(**kwargs):
        raise NotFoundError("item 999 does not exist upstream")

    monkeypatch.setattr("hnx.cli.fetch_item_cmd", boom)

    result = CliRunner().invoke(cli, ["item", "999"])

    assert result.exit_code == 5
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "not_found"


def test_item_filtered_maps_to_exit_7(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(**kwargs):
        raise FilteredError("deleted", details={"deleted": True, "dead": False})

    monkeypatch.setattr("hnx.cli.fetch_item_cmd", boom)

    result = CliRunner().invoke(cli, ["item", "800"])

    assert result.exit_code == 7
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "filtered_out"
    assert payload["error"]["details"] == {"deleted": True, "dead": False}


def test_item_id_must_be_int() -> None:
    result = CliRunner().invoke(cli, ["item", "not-a-number"])
    assert result.exit_code == 2  # Click usage error


def test_new_and_best_commands_registered() -> None:
    help_result = CliRunner().invoke(cli, ["--help"])
    assert "top" in help_result.output
    assert "new" in help_result.output
    assert "best" in help_result.output
    assert "item" in help_result.output


def test_thread_emits_success_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch_thread(**kwargs):
        return SuccessEnvelope(
            data={"type": "story", "id": 8863, "title": "Dropbox", "children": []},
            query={"command": "thread", "story_id": 8863},
            meta={"type": "story", "total_comment_count": 0, "returned_comment_count": 0, "truncated": False},
            raw=None,
        )

    monkeypatch.setattr("hnx.cli.fetch_thread", fake_fetch_thread)

    result = CliRunner().invoke(cli, ["thread", "8863"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["id"] == 8863
    assert result.stderr == ""


def test_thread_not_found_exit_5(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(**kwargs):
        raise NotFoundError("story 999 not found")

    monkeypatch.setattr("hnx.cli.fetch_thread", boom)

    result = CliRunner().invoke(cli, ["thread", "999"])
    assert result.exit_code == 5
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "not_found"


def test_thread_upstream_error_exit_3(monkeypatch: pytest.MonkeyPatch) -> None:
    from hnx.errors import UpstreamError

    async def boom(**kwargs):
        raise UpstreamError("Algolia 500")

    monkeypatch.setattr("hnx.cli.fetch_thread", boom)

    result = CliRunner().invoke(cli, ["thread", "8863"])
    assert result.exit_code == 3
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "upstream_error"


def test_thread_invalid_input_exit_6(monkeypatch: pytest.MonkeyPatch) -> None:
    from hnx.errors import InvalidInputError

    async def boom(**kwargs):
        raise InvalidInputError("item 42 is comment, expected story")

    monkeypatch.setattr("hnx.cli.fetch_thread", boom)

    result = CliRunner().invoke(cli, ["thread", "42"])
    assert result.exit_code == 6
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "invalid_input"


def test_thread_command_registered_in_help() -> None:
    help_result = CliRunner().invoke(cli, ["--help"])
    assert "thread" in help_result.output


def test_thread_requires_story_id() -> None:
    result = CliRunner().invoke(cli, ["thread"])
    assert result.exit_code == 2  # Click usage error — missing argument


def test_thread_story_id_must_be_int() -> None:
    result = CliRunner().invoke(cli, ["thread", "not-a-number"])
    assert result.exit_code == 2  # Click usage error
