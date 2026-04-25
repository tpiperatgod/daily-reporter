"""Tests for phx.errors."""

from __future__ import annotations

from phx.errors import ConfigError, InvalidInputError, NotFoundError, PHXError, TransformError, UpstreamError


def test_error_to_dict_includes_details():
    err = UpstreamError("rate limited", details={"status_code": 429, "retryable": True})

    assert err.to_dict() == {
        "ok": False,
        "error": {
            "type": "upstream_error",
            "message": "rate limited",
            "details": {"status_code": 429, "retryable": True},
        },
    }


def test_error_exit_codes_and_types():
    assert ConfigError("x").exit_code == 2
    assert ConfigError("x").error_type == "config_error"
    assert UpstreamError("x").exit_code == 3
    assert TransformError("x").exit_code == 4
    assert NotFoundError("x").exit_code == 5
    assert InvalidInputError("x").exit_code == 6
    assert PHXError("x").exit_code == 1
