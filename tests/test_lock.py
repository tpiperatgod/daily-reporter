"""Unit tests for distributed lock service."""

import pytest
from unittest.mock import AsyncMock

from app.services.lock import (
    LockService,
    LockAcquisitionError,
    get_lock_service,
    user_trigger_lock,
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.set = AsyncMock()
    mock.get = AsyncMock()
    mock.delete = AsyncMock()
    mock.exists = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def lock_service(mock_redis):
    """Create LockService with mocked Redis."""
    service = LockService(redis_url="redis://localhost:6379/0")
    service._client = mock_redis
    return service


@pytest.fixture
def reset_lock_singleton():
    """Reset the global lock service singleton before/after each test."""
    import app.services.lock as lock_module

    lock_module._lock_service = None
    yield
    lock_module._lock_service = None


class TestLockService:
    """Test LockService class."""

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self, lock_service, mock_redis):
        """Test successful lock acquisition."""
        mock_redis.set.return_value = True

        async with lock_service.acquire_lock("test_lock", ttl=60) as acquired:
            assert acquired is True

        # Verify SET was called with correct params
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "lock:test_lock"
        assert call_args[1]["nx"] is True
        assert call_args[1]["ex"] == 60

    @pytest.mark.asyncio
    async def test_acquire_lock_already_locked(self, lock_service, mock_redis):
        """Test lock acquisition failure when already locked."""
        mock_redis.set.return_value = False

        with pytest.raises(LockAcquisitionError) as exc_info:
            async with lock_service.acquire_lock("test_lock"):
                pass

        assert "locked" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_acquire_lock_fail_silent(self, lock_service, mock_redis):
        """Test silent failure mode returns False."""
        mock_redis.set.return_value = False

        async with lock_service.acquire_lock("test_lock", fail_silent=True) as acquired:
            assert acquired is False

    @pytest.mark.asyncio
    async def test_lock_release_on_exit(self, lock_service, mock_redis):
        """Test lock is released when context exits."""
        mock_redis.set.return_value = True

        # Capture the actual token used in SET
        actual_token = None

        async def mock_set(key, value, **kwargs):
            nonlocal actual_token
            actual_token = value
            return True

        mock_redis.set.side_effect = mock_set

        # Mock get to return the captured token
        async def mock_get(key):
            return actual_token

        mock_redis.get.side_effect = mock_get

        async with lock_service.acquire_lock("test_lock") as acquired:
            assert acquired is True

        # Verify delete was called since tokens match
        mock_redis.delete.assert_called_once_with("lock:test_lock")

    @pytest.mark.asyncio
    async def test_lock_not_released_by_other(self, lock_service, mock_redis):
        """Test lock not released if token doesn't match (another process owns it)."""
        mock_redis.set.return_value = True

        # Mock get to return different token (lock was stolen/reacquired)
        mock_redis.get.return_value = "different-token"

        async with lock_service.acquire_lock("test_lock") as _:
            pass

        # Delete should NOT be called since tokens don't match
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_lock_release_error_handling(self, lock_service, mock_redis):
        """Test lock release errors are caught and logged."""
        mock_redis.set.return_value = True
        mock_redis.get.side_effect = Exception("Redis error")

        # Should not raise exception
        async with lock_service.acquire_lock("test_lock") as _:
            pass

    @pytest.mark.asyncio
    async def test_is_locked_true(self, lock_service, mock_redis):
        """Test is_locked returns True when lock exists."""
        mock_redis.exists.return_value = 1

        result = await lock_service.is_locked("test_lock")

        assert result is True
        mock_redis.exists.assert_called_once_with("lock:test_lock")

    @pytest.mark.asyncio
    async def test_is_locked_false(self, lock_service, mock_redis):
        """Test is_locked returns False when lock doesn't exist."""
        mock_redis.exists.return_value = 0

        result = await lock_service.is_locked("test_lock")

        assert result is False

    @pytest.mark.asyncio
    async def test_close_client(self, lock_service, mock_redis):
        """Test close() closes Redis client."""
        await lock_service.close()

        mock_redis.close.assert_called_once()
        assert lock_service._client is None


class TestUserTriggerLock:
    """Test user_trigger_lock convenience function."""

    @pytest.mark.asyncio
    async def test_user_trigger_lock_acquired(self, mock_redis, reset_lock_singleton):
        """Test user trigger lock acquisition."""
        import app.services.lock as lock_module

        # Create a mock lock service with mocked Redis
        mock_service = LockService(redis_url="redis://localhost:6379/0")
        mock_service._client = mock_redis
        lock_module._lock_service = mock_service

        mock_redis.set.return_value = True

        # Capture token for proper release
        actual_token = None

        async def mock_set(key, value, **kwargs):
            nonlocal actual_token
            actual_token = value
            return True

        mock_redis.set.side_effect = mock_set
        mock_redis.get.return_value = actual_token

        async with user_trigger_lock("user-123", ttl=300) as acquired:
            assert acquired is True

        # Verify correct lock key format
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "lock:user_trigger:user-123"
        assert call_args[1]["ex"] == 300

    @pytest.mark.asyncio
    async def test_user_trigger_lock_conflict(self, mock_redis, reset_lock_singleton):
        """Test user trigger lock returns False on conflict."""
        import app.services.lock as lock_module

        # Create a mock lock service with mocked Redis
        mock_service = LockService(redis_url="redis://localhost:6379/0")
        mock_service._client = mock_redis
        lock_module._lock_service = mock_service

        mock_redis.set.return_value = False

        async with user_trigger_lock("user-123") as acquired:
            assert acquired is False

    @pytest.mark.asyncio
    async def test_concurrent_lock_attempts(self, mock_redis, reset_lock_singleton):
        """Test that concurrent attempts properly conflict."""
        import app.services.lock as lock_module

        # Create a mock lock service with mocked Redis
        mock_service = LockService(redis_url="redis://localhost:6379/0")
        mock_service._client = mock_redis
        lock_module._lock_service = mock_service

        # Set up token capture for proper release
        actual_token = None
        call_count = 0

        async def mock_set(key, value, **kwargs):
            nonlocal actual_token, call_count
            call_count += 1
            if call_count == 1:
                actual_token = value
                return True
            # Second call returns False (lock already held)
            return False

        async def mock_get(key):
            return actual_token

        mock_redis.set.side_effect = mock_set
        mock_redis.get.side_effect = mock_get

        async with user_trigger_lock("user-123") as acquired1:
            assert acquired1 is True

            async with user_trigger_lock("user-123") as acquired2:
                assert acquired2 is False


class TestGetLockService:
    """Test global lock service singleton."""

    def test_singleton_pattern(self, reset_lock_singleton):
        """Test that get_lock_service returns same instance."""
        service1 = get_lock_service()
        service2 = get_lock_service()

        assert service1 is service2

    def test_creates_new_instance(self, reset_lock_singleton):
        """Test that new instance is created when None."""
        service = get_lock_service()

        assert service is not None
        assert isinstance(service, LockService)


class TestLockEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_lock_with_exception_in_context(self, lock_service, mock_redis):
        """Test lock is released even when exception occurs in context."""
        # Capture token for proper release
        actual_token = None

        async def mock_set(key, value, **kwargs):
            nonlocal actual_token
            actual_token = value
            return True

        async def mock_get(key):
            return actual_token

        mock_redis.set.side_effect = mock_set
        mock_redis.get.side_effect = mock_get

        with pytest.raises(ValueError):
            async with lock_service.acquire_lock("test_lock") as _:
                raise ValueError("Test error")

        # Lock should still be released
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_ttl(self, lock_service, mock_redis):
        """Test custom TTL is applied."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "token"

        async with lock_service.acquire_lock("test_lock", ttl=600) as _:
            pass

        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 600

    @pytest.mark.asyncio
    async def test_lock_key_format(self, lock_service, mock_redis):
        """Test lock key has correct prefix."""
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "token"

        async with lock_service.acquire_lock("my_resource") as _:
            pass

        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "lock:my_resource"
