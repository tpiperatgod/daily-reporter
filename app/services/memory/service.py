"""Service for managing long-term memory facts with semantic search."""

from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import text

from app.db.models import MemoryFact
from app.services.embedding.base import BaseEmbeddingProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Service for managing long-term memory facts with semantic search."""

    def __init__(self, session: AsyncSession, embedding_provider: BaseEmbeddingProvider):
        """
        Initialize MemoryService.

        Args:
            session: Async database session
            embedding_provider: Provider for generating embeddings
        """
        self.session = session
        self.embedding_provider = embedding_provider

    async def search_relevant_facts(
        self,
        topic_id: UUID,
        query_text: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[str]:
        """
        Search for relevant facts using semantic similarity.

        Args:
            topic_id: UUID of the topic to search within
            query_text: Text to search for (will be embedded)
            limit: Maximum number of facts to return
            threshold: Minimum cosine similarity threshold (0-1, higher = more similar)

        Returns:
            List of fact content strings (ordered by relevance)

        Raises:
            Exception: If embedding generation or search fails
        """
        try:
            # Step 1: Generate embedding for query
            logger.debug(f"Generating embedding for query: {query_text[:100]}...")
            query_embedding = await self.embedding_provider.generate_embedding(query_text)

            # Step 2: Perform cosine similarity search using pgvector
            # Note: pgvector's <=> operator returns cosine distance (0=identical, 2=opposite)
            # We convert to similarity: similarity = 1 - distance

            # Convert embedding to PostgreSQL vector format for raw SQL
            # pgvector expects: '[0.1,0.2,0.3]' (no spaces between values)
            embedding_str = f"[{','.join(map(str, query_embedding))}]"

            # Use named parameters with asyncpg-compatible text() SQL
            query = text("""
                SELECT content, (1 - (embedding <=> CAST(:embedding AS vector))) as similarity
                FROM memory_facts
                WHERE topic_id = CAST(:topic_id AS uuid)
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """)

            result = await self.session.execute(
                query,
                {"embedding": embedding_str, "topic_id": str(topic_id), "limit": limit}
            )
            facts = result.all()

            # Step 3: Filter by threshold
            relevant_facts = [
                fact.content for fact in facts
                if fact.similarity >= threshold
            ]

            logger.info(
                f"Retrieved {len(relevant_facts)}/{len(facts)} facts above threshold {threshold} "
                f"for topic {topic_id}"
            )

            return relevant_facts

        except Exception as e:
            logger.error(f"Failed to search relevant facts: {e}", exc_info=True)
            # Return empty list on failure (graceful degradation)
            return []

    async def store_new_facts(
        self,
        topic_id: UUID,
        facts: List[str],
        source_metadata: Dict[str, Any] = None
    ) -> int:
        """
        Store new facts with embeddings.

        Args:
            topic_id: UUID of the topic these facts belong to
            facts: List of fact strings to store
            source_metadata: Optional metadata about the source (digest_id, tweet_ids, etc.)

        Returns:
            Number of facts successfully stored

        Raises:
            Exception: If embedding generation or storage fails
        """
        if not facts:
            logger.debug("No facts to store")
            return 0

        try:
            # Step 1: Generate embeddings in batch
            logger.debug(f"Generating embeddings for {len(facts)} facts")
            from app.core.config import settings
            embeddings = await self.embedding_provider.generate_embeddings_batch(
                facts,
                batch_size=settings.LLM_EMBEDDING_BATCH_SIZE
            )

            # Step 2: Create MemoryFact records
            memory_facts = []
            for fact_text, embedding in zip(facts, embeddings):
                # Note: Pass raw embedding list to SQLAlchemy's Vector type
                # It handles conversion to PostgreSQL vector format internally
                memory_fact = MemoryFact(
                    topic_id=topic_id,
                    content=fact_text,
                    embedding=embedding,  # SQLAlchemy Vector type expects a list
                    source_metadata=source_metadata or {}
                )
                memory_facts.append(memory_fact)

            # Step 3: Bulk insert
            self.session.add_all(memory_facts)
            await self.session.flush()

            logger.info(f"Stored {len(memory_facts)} new memory facts for topic {topic_id}")
            return len(memory_facts)

        except Exception as e:
            logger.error(f"Failed to store new facts: {e}", exc_info=True)
            raise

    async def get_facts_count(self, topic_id: UUID) -> int:
        """
        Get the total number of facts stored for a topic.

        Args:
            topic_id: UUID of the topic

        Returns:
            Number of facts stored
        """
        try:
            result = await self.session.execute(
                select(func.count(MemoryFact.id)).where(MemoryFact.topic_id == topic_id)
            )
            count = result.scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get facts count: {e}", exc_info=True)
            return 0
