"""Structured error classes for hnx."""

from __future__ import annotations


class HNXError(Exception):
    """Base error for all hnx failures."""

    exit_code: int = 1
    error_type: str = "internal_error"
    retryable: bool = False

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


class UpstreamError(HNXError):
    """HTTP failure from the HackerNews API (after retries)."""

    exit_code = 3
    error_type = "upstream_error"
    retryable = True


class TransformError(HNXError):
    """Upstream payload cannot be normalized."""

    exit_code = 4
    error_type = "transform_error"


class NotFoundError(HNXError):
    """`hnx item <id>` and HN returned null — the id does not exist."""

    exit_code = 5
    error_type = "not_found"


class InvalidInputError(HNXError):
    """User supplied invalid flags / values (e.g. --limit 0)."""

    exit_code = 6
    error_type = "invalid_input"


class FilteredError(HNXError):
    """Item exists but was filtered out (deleted/dead) without --include-deleted.

    `details` carries `{"deleted": bool, "dead": bool}` so callers can tell
    this apart from a real NotFoundError.
    """

    exit_code = 7
    error_type = "filtered_out"
