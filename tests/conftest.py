"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
import asyncio


@pytest_asyncio.fixture
async def async_session():
    """Create async database session for testing."""
    from app.db.session import get_async_session_local

    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
