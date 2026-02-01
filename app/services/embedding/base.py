"""Base protocol for embedding providers."""

from typing import List, Protocol


class BaseEmbeddingProvider(Protocol):
    """Protocol defining the interface for embedding providers."""

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        ...

    async def generate_embeddings_batch(
        self, texts: List[str], batch_size: int
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            Exception: If batch embedding generation fails
        """
        ...
