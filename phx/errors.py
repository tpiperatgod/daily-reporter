"""Structured error classes for phx."""

from __future__ import annotations


class PHXError(Exception):
    """Base error for all phx failures."""

    exit_code: int = 1
    error_type: str = "internal_error"

    def __init__(self, message: str = "", *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details: dict = details or {}

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "error": {
                "type": self.error_type,
                "message": str(self),
                "details": self.details,
            },
        }


class ConfigError(PHXError):
    """Missing or invalid configuration."""

    exit_code = 2
    error_type = "config_error"


class UpstreamError(PHXError):
    """HTTP, transport, JSON, or GraphQL failure from Product Hunt."""

    exit_code = 3
    error_type = "upstream_error"


class TransformError(PHXError):
    """Upstream payload cannot be normalized."""

    exit_code = 4
    error_type = "transform_error"


class NotFoundError(PHXError):
    """Requested Product Hunt post/product does not exist."""

    exit_code = 5
    error_type = "not_found"


class InvalidInputError(PHXError):
    """User supplied invalid flags or values."""

    exit_code = 6
    error_type = "invalid_input"
