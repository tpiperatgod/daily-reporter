"""Tests for MemoryService."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.memory import MemoryService


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider."""
    provider = AsyncMock()
    provider.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    provider.generate_embeddings_batch = AsyncMock(
        return_value=[[0.1] * 1536, [0.2] * 1536]
    )
    return provider


@pytest.fixture
def memory_service(mock_session, mock_embedding_provider):
    """Create MemoryService instance."""
    return MemoryService(mock_session, mock_embedding_provider)


@pytest.mark.asyncio
async def test_store_new_facts_batch(memory_service, mock_session, mock_embedding_provider):
    """Test storing multiple facts with embeddings."""
    topic_id = uuid4()
    facts = [
        "DeepSeek released V3 model on Jan 15, 2025",
        "OpenAI announced GPT-5 in February 2025"
    ]
    source_metadata = {"digest_id": str(uuid4())}

    # Execute
    count = await memory_service.store_new_facts(
        topic_id=topic_id,
        facts=facts,
        source_metadata=source_metadata
    )

    # Verify
    assert count == 2
    assert mock_embedding_provider.generate_embeddings_batch.called
    assert mock_session.add_all.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_store_empty_facts(memory_service):
    """Test storing empty facts list."""
    topic_id = uuid4()
    facts = []

    count = await memory_service.store_new_facts(
        topic_id=topic_id,
        facts=facts
    )

    assert count == 0


@pytest.mark.asyncio
async def test_search_relevant_facts_with_threshold(memory_service, mock_session, mock_embedding_provider):
    """Test searching facts with similarity threshold."""
    topic_id = uuid4()
    query_text = "What are the latest AI model releases?"

    # Mock database response
    mock_result = MagicMock()
    mock_result.all.return_value = [
        MagicMock(content="DeepSeek released V3", similarity=0.85),
        MagicMock(content="OpenAI announced GPT-5", similarity=0.75),
        MagicMock(content="Unrelated fact", similarity=0.5)
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    facts = await memory_service.search_relevant_facts(
        topic_id=topic_id,
        query_text=query_text,
        limit=5,
        threshold=0.7
    )

    # Verify - should only return facts above threshold
    assert len(facts) == 2
    assert "DeepSeek released V3" in facts
    assert "OpenAI announced GPT-5" in facts
    assert "Unrelated fact" not in facts


@pytest.mark.asyncio
async def test_search_relevant_facts_error_handling(memory_service, mock_session, mock_embedding_provider):
    """Test graceful degradation on search failure."""
    topic_id = uuid4()
    query_text = "Test query"

    # Mock embedding generation failure
    mock_embedding_provider.generate_embedding.side_effect = Exception("API error")

    # Execute - should return empty list instead of raising
    facts = await memory_service.search_relevant_facts(
        topic_id=topic_id,
        query_text=query_text
    )

    assert facts == []


@pytest.mark.asyncio
async def test_get_facts_count(memory_service, mock_session):
    """Test getting facts count for a topic."""
    topic_id = uuid4()

    # Mock database response
    mock_result = MagicMock()
    mock_result.scalar.return_value = 42
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    count = await memory_service.get_facts_count(topic_id)

    # Verify
    assert count == 42
    assert mock_session.execute.called
