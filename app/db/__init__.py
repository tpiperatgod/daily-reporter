"""Database module for X-News-Digest."""

from app.db.session import get_async_session_local

__all__ = ["get_async_session_local"]
