"""Integration tests for memory service with real database."""

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock

from app.services.memory import MemoryService


@pytest_asyncio.fixture
async def db_session():
    """Create real database session for integration testing."""
    from app.db.session import get_async_session_local

    session_maker = get_async_session_local()
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider that returns fixed vectors."""
    provider = AsyncMock()
    # Return different embeddings for different inputs to test similarity
    provider.generate_embedding = AsyncMock(side_effect=lambda text: (
        [0.9, 0.1] + [0.0] * 1534 if "AI" in text
        else [0.1, 0.9] + [0.0] * 1534
    ))
    provider.generate_embeddings_batch = AsyncMock(return_value=[
        [0.9, 0.1] + [0.0] * 1534,  # AI-related embedding
        [0.8, 0.2] + [0.0] * 1534,  # Similar AI embedding
        [0.1, 0.9] + [0.0] * 1534   # Different topic embedding
    ])
    return provider


@pytest.mark.asyncio
async def test_store_and_search_with_real_database(db_session, mock_embedding_provider):
    """
    Integration test: Store facts in real database and search them using vector similarity.

    This test validates:
    1. Embedding format is correct for PostgreSQL pgvector
    2. SQL query uses correct parameter binding
    3. Vector similarity search works end-to-end
    """
    # Setup: Create a test topic first (memory_facts has FK constraint)
    from app.db.models import Topic
    topic_id = uuid4()
    topic = Topic(
        id=topic_id,
        name="Test Topic for Memory",
        query="test query",
        cron_expression="0 0 * * *",
        is_enabled=True
    )
    db_session.add(topic)
    await db_session.commit()

    memory_service = MemoryService(db_session, mock_embedding_provider)

    # Step 1: Store facts with embeddings
    facts = [
        "DeepSeek released V3 AI model on Jan 15, 2025",
        "OpenAI announced GPT-5 AI in February 2025",
        "Python 3.13 was released in October 2024"
    ]
    source_metadata = {"digest_id": str(uuid4()), "test": True}

    count = await memory_service.store_new_facts(
        topic_id=topic_id,
        facts=facts,
        source_metadata=source_metadata
    )

    assert count == 3
    await db_session.commit()

    # Step 2: Search for AI-related facts (should match first two facts)
    results = await memory_service.search_relevant_facts(
        topic_id=topic_id,
        query_text="AI model releases",
        limit=5,
        threshold=0.5  # Low threshold to ensure we get results
    )

    # Verify: Should find at least the AI-related facts
    assert len(results) >= 2
    assert any("DeepSeek" in fact for fact in results)
    assert any("OpenAI" in fact for fact in results)

    # Step 3: Verify facts count
    total_count = await memory_service.get_facts_count(topic_id)
    assert total_count == 3

    # Cleanup
    await db_session.rollback()


@pytest.mark.asyncio
async def test_embedding_format_validation(db_session, mock_embedding_provider):
    """
    Test that embeddings are stored in correct PostgreSQL vector format.

    Validates that we use '[0.1,0.2,0.3]' (no spaces) instead of
    Python's str(list) which produces '[0.1, 0.2, 0.3]' (with spaces).
    """
    # Setup: Create a test topic first
    from app.db.models import Topic
    topic_id = uuid4()
    topic = Topic(
        id=topic_id,
        name="Test Topic for Format Validation",
        query="test query",
        cron_expression="0 0 * * *",
        is_enabled=True
    )
    db_session.add(topic)
    await db_session.commit()

    memory_service = MemoryService(db_session, mock_embedding_provider)

    # Store a single fact
    await memory_service.store_new_facts(
        topic_id=topic_id,
        facts=["Test fact for embedding format"],
        source_metadata={"test": "format_validation"}
    )
    await db_session.commit()

    # Query directly to check stored format
    from sqlalchemy import text
    result = await db_session.execute(
        text("SELECT embedding::text FROM memory_facts WHERE topic_id = :topic_id LIMIT 1"),
        {"topic_id": topic_id}
    )
    row = result.fetchone()

    assert row is not None
    embedding_str = row[0]

    # Validate format: should be [n1,n2,n3] without spaces
    assert embedding_str.startswith('[')
    assert embedding_str.endswith(']')
    # Python's str(list) adds spaces after commas, correct format doesn't
    # Check that we don't have ", " pattern (space after comma)
    assert ", " not in embedding_str, "Embedding has spaces - using wrong format!"

    # Cleanup
    await db_session.rollback()


@pytest.mark.asyncio
async def test_search_with_empty_database(db_session, mock_embedding_provider):
    """Test search returns empty list when no facts exist."""
    memory_service = MemoryService(db_session, mock_embedding_provider)
    topic_id = uuid4()  # New topic with no facts

    results = await memory_service.search_relevant_facts(
        topic_id=topic_id,
        query_text="Any query",
        limit=10
    )

    assert results == []
