"""Structured error classes for twx."""


class TWXError(Exception):
    """Base error for all twx failures."""

    exit_code: int = 1
    error_type: str = "internal_error"
    retryable: bool = False

    def __init__(
        self,
        message: str = "",
        *,
        exit_code: int | None = None,
        error_type: str | None = None,
        retryable: bool | None = None,
    ):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code
        if error_type is not None:
            self.error_type = error_type
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "error": {
                "type": self.error_type,
                "message": str(self),
                "retryable": self.retryable,
            },
        }


class ConfigError(TWXError):
    """Missing or invalid configuration."""

    exit_code = 2
    error_type = "config_error"


class UpstreamError(TWXError):
    """Failure from the upstream API."""

    exit_code = 3
    error_type = "upstream_error"
    retryable = True


class TransformError(TWXError):
    """Failure to normalize upstream data."""

    exit_code = 4
    error_type = "transform_error"
