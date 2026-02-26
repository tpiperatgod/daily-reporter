"""OpenAI-compatible embedding provider (GLM, OpenAI, etc.)."""

from typing import List
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIEmbeddingProvider:
    """
    Embedding provider for OpenAI-compatible APIs.

    Supports: OpenAI, GLM, and other compatible services.
    API format: POST {base_url}/embeddings
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        batch_size: int = 64,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
    ):
        """
        Initialize OpenAI-compatible embedding provider.

        Args:
            base_url: API base URL (e.g., https://api.openai.com/v1)
            model: Model name (e.g., text-embedding-3-small, embedding-3)
            api_key: API key for authentication
            batch_size: Maximum items per batch request (default: 64)
            max_retries: Maximum retry attempts for rate limits (default: 5)
            initial_backoff: Initial backoff in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.batch_size = min(batch_size, 64)  # OpenAI/GLM max is 64
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0), headers={"Content-Type": "application/json"})

        logger.info(
            "Initialized OpenAI-compatible embedding provider",
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
                f"{self.base_url}/embeddings",
                json={
                    "model": self.model,
                    "input": text[:1000],  # Truncate very long text
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            response.raise_for_status()
            data = response.json()

            # Extract embedding from OpenAI-compatible response
            embedding = data["data"][0]["embedding"]

            logger.debug(f"Generated embedding for text (length: {len(text)})")

            return embedding

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("Authentication failed - check API key")
            elif e.response.status_code == 429:
                logger.error("Rate limit exceeded")
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
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
        if batch_size is None:
            batch_size = self.batch_size

        # Validate batch size
        batch_size = min(batch_size, 64)  # OpenAI/GLM max

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.info(
            "Starting batch embedding generation",
            extra={
                "total_texts": len(texts),
                "batch_size": batch_size,
                "total_batches": total_batches,
                "provider": "openai",
            },
        )

        # Process in chunks
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

            # Truncate long texts to fit token limit
            truncated_batch = [text[:1000] for text in batch]

            # Make API call with retry
            data = await self._api_call_with_retry(json_data={"model": self.model, "input": truncated_batch})

            # Extract embeddings in order
            embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(embeddings)

            logger.debug(
                f"Batch {batch_num}/{total_batches} completed",
                extra={"embeddings_count": len(embeddings)},
            )

        logger.info(
            "Batch embedding generation completed",
            extra={"total_embeddings": len(all_embeddings), "provider": "openai"},
        )

        return all_embeddings

    async def _api_call_with_retry(self, json_data: dict) -> dict:
        """
        Make API call with exponential backoff retry on rate limits.

        Args:
            json_data: Request payload

        Returns:
            API response JSON

        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        from app.core.http_utils import api_call_with_retry

        def handle_openai_errors(error: httpx.HTTPStatusError, attempt: int):
            """Custom error handling for OpenAI API."""
            if error.response.status_code == 401:
                logger.error("Authentication failed - check API key")
                raise
            elif error.response.status_code == 400:
                logger.error(f"Bad request (400): {error.response.text}")
                # Return None for graceful degradation
                return {"data": [{"embedding": None}]}
            # Return None to continue retry for other errors
            return None

        return await api_call_with_retry(
            client=self.client,
            method="POST",
            url=f"{self.base_url}/embeddings",
            json_data=json_data,
            headers={"Authorization": f"Bearer {self.api_key}"},
            max_retries=self.max_retries,
            initial_backoff=self.initial_backoff,
            retryable_status_codes={429},  # Rate limit
            error_handler=handle_openai_errors,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
