"""Tests for hnx.errors."""

from __future__ import annotations

from hnx.errors import (
    FilteredError,
    HNXError,
    InvalidInputError,
    NotFoundError,
    TransformError,
    UpstreamError,
)


def test_base_error_defaults() -> None:
    err = HNXError("boom")
    assert err.exit_code == 1
    assert err.error_type == "internal_error"
    assert str(err) == "boom"


def test_upstream_error() -> None:
    err = UpstreamError("rate limited")
    assert err.exit_code == 3
    assert err.error_type == "upstream_error"
    assert err.retryable is True


def test_transform_error() -> None:
    err = TransformError("bad payload")
    assert err.exit_code == 4
    assert err.error_type == "transform_error"


def test_not_found_error() -> None:
    err = NotFoundError("missing")
    assert err.exit_code == 5
    assert err.error_type == "not_found"


def test_invalid_input_error() -> None:
    err = InvalidInputError("bad flag combo")
    assert err.exit_code == 6
    assert err.error_type == "invalid_input"


def test_filtered_error_with_details() -> None:
    err = FilteredError("item deleted", details={"deleted": True, "dead": False})
    assert err.exit_code == 7
    assert err.error_type == "filtered_out"
    assert err.details == {"deleted": True, "dead": False}


def test_error_to_dict_shape() -> None:
    err = FilteredError("x", details={"deleted": True, "dead": False})
    payload = err.to_dict()
    assert payload == {
        "ok": False,
        "error": {
            "type": "filtered_out",
            "message": "x",
            "details": {"deleted": True, "dead": False},
        },
    }


def test_error_to_dict_without_details() -> None:
    err = UpstreamError("boom")
    payload = err.to_dict()
    assert payload == {
        "ok": False,
        "error": {
            "type": "upstream_error",
            "message": "boom",
            "details": {},
        },
    }
