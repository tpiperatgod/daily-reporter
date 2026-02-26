"""Ollama embedding provider for local models."""

from typing import List
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaEmbeddingProvider:
    """
    Embedding provider for Ollama local models.

    API format: POST {base_url}/api/embed
    No authentication required for local service.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        batch_size: int = 64,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        """
        Initialize Ollama embedding provider.

        Args:
            base_url: Ollama API base URL (e.g., http://localhost:11434)
            model: Model name (e.g., bge-m3:567m)
            batch_size: Maximum items per batch request (default: 64)
            max_retries: Maximum retry attempts (default: 3)
            initial_backoff: Initial backoff in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0),  # Longer timeout for local inference
            headers={"Content-Type": "application/json"},
        )

        logger.info(
            "Initialized Ollama embedding provider",
            extra={
                "base_url": self.base_url,
                "model": self.model,
                "batch_size": self.batch_size,
            },
        )

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
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text[:1000],  # Truncate very long text
                },
                # No Authorization header for local Ollama
            )

            response.raise_for_status()
            data = response.json()

            # Extract embedding from Ollama response
            # Ollama returns: {"embeddings": [[...], [...]]}
            embedding = data["embeddings"][0]

            logger.debug(f"Generated embedding for text (length: {len(text)})")

            return embedding

        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running? Try: ollama serve")
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Model '{self.model}' not found. Pull the model: ollama pull {self.model}")
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except KeyError as e:
            logger.error(f"Unexpected Ollama response format: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = None) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process in each batch (uses provider default if None)

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            Exception: If batch embedding generation fails
        """
        import time

        if batch_size is None:
            batch_size = self.batch_size

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.info(
            "Starting batch embedding generation",
            extra={
                "total_texts": len(texts),
                "batch_size": batch_size,
                "total_batches": total_batches,
                "provider": "ollama",
            },
        )

        start_time = time.time()

        # Process in chunks
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

            # Truncate long texts
            truncated_batch = [text[:1000] for text in batch]

            # Make API call with retry
            data = await self._api_call_with_retry(json_data={"model": self.model, "input": truncated_batch})

            # Extract embeddings in order
            # Ollama returns: {"embeddings": [[...], [...], ...]}
            embeddings = data["embeddings"]
            all_embeddings.extend(embeddings)

            logger.debug(
                f"Batch {batch_num}/{total_batches} completed",
                extra={"embeddings_count": len(embeddings)},
            )

        duration = time.time() - start_time

        logger.info(
            f"Batch embedding generation completed in {duration:.2f}s",
            extra={
                "total_embeddings": len(all_embeddings),
                "provider": "ollama",
                "duration_seconds": duration,
            },
        )

        return all_embeddings

    async def _api_call_with_retry(self, json_data: dict) -> dict:
        """
        Make API call with exponential backoff retry.

        Args:
            json_data: Request payload

        Returns:
            API response JSON

        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        from app.core.http_utils import api_call_with_retry

        def handle_ollama_errors(error: httpx.HTTPStatusError, attempt: int):
            """Custom error handling for Ollama API."""
            if error.response.status_code == 404:
                logger.error(f"Model '{self.model}' not found. Pull the model: ollama pull {self.model}")
                raise
            # Return None to continue retry for other errors
            return None

        try:
            return await api_call_with_retry(
                client=self.client,
                method="POST",
                url=f"{self.base_url}/api/embed",
                json_data=json_data,
                max_retries=self.max_retries,
                initial_backoff=self.initial_backoff,
                retryable_status_codes=set(),  # No rate limits for local Ollama
                error_handler=handle_ollama_errors,
            )
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running? Try: ollama serve")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
