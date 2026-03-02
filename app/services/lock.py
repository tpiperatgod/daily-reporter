"""
Distributed locking service using Redis.

Provides async context manager for acquiring distributed locks
to prevent concurrent operations on the same resource.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging("lock")


class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired."""

    pass


class LockService:
    """
    Redis-based distributed lock service.

    Uses SET NX EX for atomic lock acquisition with TTL.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize lock service.

        Args:
            redis_url: Redis connection URL (defaults to settings.REDIS_URL)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        return self._client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @asynccontextmanager
    async def acquire_lock(self, lock_name: str, ttl: int = 300, fail_silent: bool = False):
        """
        Acquire a distributed lock.

        Args:
            lock_name: Unique name for the lock
            ttl: Lock timeout in seconds (prevents deadlocks on crash)
            fail_silent: If True, return False instead of raising on failure

        Yields:
            bool: True if lock acquired, False if already locked (when fail_silent=True)

        Raises:
            LockAcquisitionError: If lock cannot be acquired (when fail_silent=False)
        """
        client = await self._get_client()
        lock_key = f"lock:{lock_name}"
        # Generate unique token for this lock holder
        token = str(uuid.uuid4())

        acquired = False
        try:
            # SET NX EX: Set if Not eXists, with Expire time
            # This is atomic - no race condition
            acquired = await client.set(
                lock_key,
                token,
                nx=True,  # Only set if not exists
                ex=ttl,  # Expire after TTL seconds
            )

            if not acquired:
                logger.warning(f"Lock acquisition failed: {lock_name} already locked")
                if fail_silent:
                    yield False
                    return
                raise LockAcquisitionError(f"Resource '{lock_name}' is locked by another process")

            logger.info(f"Lock acquired: {lock_name} (TTL: {ttl}s)")
            yield True

        finally:
            # Only release if we acquired it and token matches
            # This prevents releasing a lock we don't own
            if acquired:
                try:
                    current_value = await client.get(lock_key)
                    if current_value == token:
                        await client.delete(lock_key)
                        logger.info(f"Lock released: {lock_name}")
                except Exception as e:
                    logger.error(f"Error releasing lock {lock_name}: {e}")
                    # Don't raise - lock will expire via TTL

    async def is_locked(self, lock_name: str) -> bool:
        """
        Check if a lock is currently held.

        Args:
            lock_name: Name of the lock to check

        Returns:
            bool: True if locked, False otherwise
        """
        client = await self._get_client()
        lock_key = f"lock:{lock_name}"
        return await client.exists(lock_key) > 0


# Global lock service instance
_lock_service: Optional[LockService] = None


def get_lock_service() -> LockService:
    """Get or create the global lock service instance."""
    global _lock_service
    if _lock_service is None:
        _lock_service = LockService()
    return _lock_service


@asynccontextmanager
async def user_trigger_lock(user_id: str, ttl: int = 300):
    """
    Acquire a lock for user trigger operations.

    Prevents concurrent trigger operations for the same user.

    Args:
        user_id: User UUID to lock
        ttl: Lock timeout in seconds (default: 5 minutes)

    Yields:
        bool: True if lock acquired, False if already locked

    Example:
        async with user_trigger_lock(str(user.id)) as acquired:
            if not acquired:
                return {"status": "conflict", "message": "Operation in progress"}
            # ... perform trigger operation
    """
    lock_service = get_lock_service()
    async with lock_service.acquire_lock(f"user_trigger:{user_id}", ttl=ttl, fail_silent=True) as acquired:
        yield acquired
