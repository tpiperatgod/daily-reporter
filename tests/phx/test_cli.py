"""Tests for the phx Click CLI."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from phx.cli import cli
from phx.errors import InvalidInputError, NotFoundError
from phx.models import SuccessEnvelope


def test_cli_help_exits_zero():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "JSON-first Product Hunt CLI" in result.output
    assert "launches" in result.output
    assert "product" in result.output


def test_launches_emits_success_envelope(monkeypatch: pytest.MonkeyPatch):
    async def fake_fetch_launches(**kwargs):
        return SuccessEnvelope(data=[], query={"command": "launches"}, meta={"returned": 0}, raw=None)

    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setattr("phx.cli.fetch_launches", fake_fetch_launches)

    result = CliRunner().invoke(cli, ["launches", "--date", "2026-04-24"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["query"]["command"] == "launches"
    assert result.stderr == ""


def test_product_emits_success_envelope(monkeypatch: pytest.MonkeyPatch):
    async def fake_fetch_product(**kwargs):
        return SuccessEnvelope(
            data={"type": "product", "id": "123"}, query={"command": "product"}, meta={"returned": 1}, raw=None
        )

    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setattr("phx.cli.fetch_product", fake_fetch_product)

    result = CliRunner().invoke(cli, ["product", "sample-launch"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["type"] == "product"
    assert result.stderr == ""


def test_missing_token_maps_to_config_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)

    result = CliRunner().invoke(cli, ["launches", "--date", "2026-04-24"])

    assert result.exit_code == 2
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "config_error"
    assert result.stdout == ""


def test_product_not_found_maps_to_exit_5(monkeypatch: pytest.MonkeyPatch):
    async def boom(**kwargs):
        raise NotFoundError("missing")

    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setattr("phx.cli.fetch_product", boom)

    result = CliRunner().invoke(cli, ["product", "missing"])

    assert result.exit_code == 5
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "not_found"


def test_invalid_product_flags_map_to_json_error(monkeypatch: pytest.MonkeyPatch):
    async def boom(**kwargs):
        raise InvalidInputError("--id and --slug are mutually exclusive")

    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setattr("phx.cli.fetch_product", boom)

    result = CliRunner().invoke(cli, ["product", "123", "--id", "--slug"])

    assert result.exit_code == 6
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "invalid_input"


def test_config_error_from_settings_uses_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "token-123")
    monkeypatch.setenv("PHX_DEFAULT_LIMIT", "bad")

    result = CliRunner().invoke(cli, ["launches"])

    assert result.exit_code == 2
    payload = json.loads(result.stderr)
    assert payload["error"]["type"] == "config_error"
