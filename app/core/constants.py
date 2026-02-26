"""Centralized constants for the application.

This module provides type-safe enums and configuration constants
to eliminate magic strings and improve maintainability.
"""

from enum import Enum


class DeliveryStatus(str, Enum):
    """Delivery status values for notification tracking."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """Supported notification channels."""

    FEISHU = "feishu"
    EMAIL = "email"


class HTTPTimeouts:
    """HTTP timeout values in seconds."""

    EMBEDDING_API = 30
    TWITTER_API = 30
    DEFAULT = 30


class TextLimits:
    """Text processing limits."""

    TRUNCATION_LENGTH = 1000
    MAX_DIGEST_LENGTH = 12000


class RetryConfig:
    """Retry configuration for HTTP calls."""

    MAX_ATTEMPTS = 5
    INITIAL_BACKOFF = 1.0
    BATCH_SIZE = 64


__all__ = [
    "DeliveryStatus",
    "NotificationChannel",
    "HTTPTimeouts",
    "TextLimits",
    "RetryConfig",
]
