"""Error classes for drm."""

from __future__ import annotations


class DRMError(Exception):
    """Base error for drm failures."""

    exit_code: int = 1

    def __init__(self, message: str, *, exit_code: int | None = None) -> None:
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class InputError(DRMError):
    """Invalid local input, such as missing report directory."""

    exit_code = 2


class OutputError(DRMError):
    """Could not write generated output."""

    exit_code = 3
