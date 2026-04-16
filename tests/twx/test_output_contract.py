"""Tests for twx output and error contracts."""

from click.testing import CliRunner

from twx.cli import cli
from twx.errors import ConfigError, TWXError, UpstreamError
from twx.models import ErrorEnvelope, SuccessEnvelope


def test_missing_api_key_returns_structured_error(cli_runner: CliRunner):
    error = ConfigError("TWITTER_API_KEY environment variable is required")
    payload = error.to_dict()
    assert payload["ok"] is False
    assert payload["error"]["type"] == "config_error"
    assert payload["error"]["message"] == "TWITTER_API_KEY environment variable is required"


def test_success_envelope_shape():
    envelope = SuccessEnvelope(data={"tweets": [], "users": []})
    assert envelope.ok is True
    assert envelope.paging["has_more"] is False
    assert envelope.paging["next_cursor"] is None
    assert envelope.data == {"tweets": [], "users": []}
    assert envelope.raw is None


def test_success_envelope_with_raw():
    envelope = SuccessEnvelope(data={"tweets": []}, raw={"original": "payload"})
    assert envelope.ok is True
    assert envelope.raw == {"original": "payload"}


def test_error_envelope_from_twx_error():
    error = UpstreamError("Rate limited", retryable=True)
    payload = error.to_dict()
    envelope = ErrorEnvelope(**payload)
    assert envelope.ok is False
    assert envelope.error["type"] == "upstream_error"
    assert envelope.error["retryable"] is True


def test_twx_error_defaults():
    error = TWXError("something went wrong")
    assert error.exit_code == 1
    assert error.error_type == "internal_error"
    assert error.retryable is False


def test_twx_error_override():
    error = TWXError("custom", exit_code=99, error_type="custom_type", retryable=True)
    assert error.exit_code == 99
    assert error.error_type == "custom_type"
    assert error.retryable is True


def test_help_still_works(cli_runner: CliRunner):
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "user" in result.output
    assert "search" in result.output
    assert "trending" in result.output
