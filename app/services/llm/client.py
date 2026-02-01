"""LLM client for generating embeddings and digests."""

import json
import hashlib
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from pydantic import BaseModel, Field, validator
from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.prompts import build_digest_prompt

logger = get_logger(__name__)


# Pydantic models for LLM response validation
class Highlight(BaseModel):
    """A single highlight in the digest."""
    title: str = Field(..., description="Brief title for the highlight")
    summary: str = Field(..., description="2-3 sentence summary")
    representative_urls: List[str] = Field(default_factory=list, description="URLs to representative posts")
    score: int = Field(..., ge=1, le=10, description="Importance score 1-10")


class DigestStats(BaseModel):
    """Statistics about the digest."""
    total_posts_analyzed: int
    unique_authors: int
    total_engagement: float
    avg_engagement_per_post: float


class DigestResult(BaseModel):
    """Structured result from LLM digest generation."""
    headline: str = Field(..., description="Main headline")
    highlights: List[Highlight] = Field(..., description="Key highlights")
    themes: List[str] = Field(..., description="Main themes identified")
    sentiment: str = Field(..., description="Overall sentiment")
    stats: DigestStats = Field(..., description="Statistics")

    @validator('sentiment')
    def validate_sentiment(cls, v):
        allowed = ['positive', 'neutral', 'negative', 'mixed']
        if v not in allowed:
            raise ValueError(f"sentiment must be one of {allowed}")
        return v


class LLMClient:
    """
    Client for interacting with LLM APIs (DeepSeek/OpenAI-compatible).

    Handles:
    - Embedding generation for semantic deduplication
    - Digest generation with structured JSON output
    """

    def __init__(self):
        """Initialize the LLM client."""
        # Chat API configuration
        self.chat_base_url = settings.LLM_CHAT_BASE_URL.rstrip('/')
        self.chat_model = settings.LLM_CHAT_MODEL
        self.chat_api_key = settings.LLM_CHAT_API_KEY

        # Embedding API configuration
        self.embedding_base_url = settings.LLM_EMBEDDING_BASE_URL.rstrip('/')
        self.embedding_model = settings.LLM_EMBEDDING_MODEL
        self.embedding_api_key = settings.LLM_EMBEDDING_API_KEY

        # Shared configuration
        self.max_tokens = settings.LLM_MAX_TOKENS

        # HTTP client - no default Authorization header
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Content-Type": "application/json"
            }
        )

        logger.info(
            f"Initialized LLM client",
            extra={
                "chat_base_url": self.chat_base_url,
                "chat_model": self.chat_model,
                "embedding_base_url": self.embedding_base_url,
                "embedding_model": self.embedding_model
            }
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = await self.client.post(
                f"{self.embedding_base_url}/embeddings",
                json={
                    "model": self.embedding_model,
                    "input": text[:1000]  # Truncate very long text
                },
                headers={
                    "Authorization": f"Bearer {self.embedding_api_key}"
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract embedding from response (OpenAI-compatible format)
            embedding = data["data"][0]["embedding"]

            logger.debug(f"Generated embedding for text (length: {len(text)})")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def generate_embedding_hash(self, text: str) -> str:
        """
        Generate a hash of the embedding vector for deduplication.

        Args:
            text: Text to hash

        Returns:
            SHA256 hash of the embedding vector
        """
        embedding = await self.generate_embedding(text)

        # Convert embedding to string and hash
        embedding_str = json.dumps(embedding)
        hash_obj = hashlib.sha256(embedding_str.encode())
        return hash_obj.hexdigest()

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batched API calls.

        GLM embedding-3 supports:
        - Max 64 items per request
        - Max 3072 tokens per item

        Args:
            texts: List of texts to embed
            batch_size: Items per API call (default from settings, max 64)

        Returns:
            List of embedding vectors (same order as input texts)

        Raises:
            Exception: If embedding generation fails after retries
        """
        if batch_size is None:
            batch_size = getattr(settings, 'LLM_EMBEDDING_BATCH_SIZE', 64)

        # Validate batch size
        batch_size = min(batch_size, 64)  # GLM max is 64

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.info(
            f"Starting batch embedding generation",
            extra={
                "total_texts": len(texts),
                "batch_size": batch_size,
                "total_batches": total_batches
            }
        )

        # Process in chunks of batch_size
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)"
            )

            # Truncate long texts to fit token limit
            truncated_batch = [text[:1000] for text in batch]

            # Make API call with retry
            data = await self._api_call_with_retry(
                url=f"{self.embedding_base_url}/embeddings",
                json_data={
                    "model": self.embedding_model,
                    "input": truncated_batch  # Array instead of string
                }
            )

            # Extract embeddings in order
            embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(embeddings)

            logger.debug(
                f"Batch {batch_num}/{total_batches} completed",
                extra={"embeddings_count": len(embeddings)}
            )

        logger.info(
            f"Batch embedding generation completed",
            extra={"total_embeddings": len(all_embeddings)}
        )

        return all_embeddings

    async def generate_embedding_hashes_batch(
        self,
        texts: List[str],
        batch_size: int = None
    ) -> List[Optional[str]]:
        """
        Generate embedding hashes for multiple texts using batched API calls.

        Args:
            texts: List of texts to hash
            batch_size: Items per API call (default from settings)

        Returns:
            List of SHA256 hashes (same order as input texts)
            Returns None for texts that failed to embed
        """
        try:
            embeddings = await self.generate_embeddings_batch(texts, batch_size)

            # Convert each embedding to hash
            hashes = []
            for embedding in embeddings:
                embedding_str = json.dumps(embedding)
                hash_obj = hashlib.sha256(embedding_str.encode())
                hashes.append(hash_obj.hexdigest())

            return hashes

        except Exception as e:
            logger.error(f"Batch embedding hash generation failed: {e}")
            # Return None for all texts on failure
            return [None] * len(texts)

    async def _api_call_with_retry(
        self,
        url: str,
        json_data: dict,
        max_retries: int = None,
        initial_backoff: float = None
    ) -> dict:
        """
        Make API call with exponential backoff retry on rate limits.

        Args:
            url: API endpoint URL
            json_data: Request payload
            max_retries: Maximum retry attempts (default from settings)
            initial_backoff: Initial backoff in seconds (default from settings)

        Returns:
            API response JSON

        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        if max_retries is None:
            max_retries = getattr(settings, 'LLM_EMBEDDING_RETRY_MAX_ATTEMPTS', 5)
        if initial_backoff is None:
            initial_backoff = getattr(settings, 'LLM_EMBEDDING_RETRY_INITIAL_BACKOFF', 1.0)

        backoff = initial_backoff

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.post(
                    url,
                    json=json_data,
                    headers={
                        "Authorization": f"Bearer {self.embedding_api_key}"
                    }
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries:
                        logger.warning(
                            f"Rate limited (429), retrying in {backoff}s "
                            f"(attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential: 1s, 2s, 4s, 8s, 16s
                        continue
                    else:
                        logger.error(f"Rate limit (429) - all retries exhausted")
                        raise
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    raise
            except Exception as e:
                logger.error(f"API call failed: {e}")
                raise

        raise Exception(f"Failed after {max_retries + 1} attempts")

    async def generate_digest(
        self,
        topic: str,
        items: List[Dict[str, Any]],
        time_window_start: datetime,
        time_window_end: datetime
    ) -> DigestResult:
        """
        Generate a digest from collected items.

        Args:
            topic: Topic name
            items: List of item dictionaries (from DB)
            time_window_start: Start of time window
            time_window_end: End of time window

        Returns:
            DigestResult with structured analysis

        Raises:
            Exception: If digest generation fails
        """
        if not items:
            logger.warning("No items to generate digest from")
            # Return empty digest
            return DigestResult(
                headline=f"No new developments for {topic}",
                highlights=[],
                themes=[],
                sentiment="neutral",
                stats=DigestStats(
                    total_posts_analyzed=0,
                    unique_authors=0,
                    total_engagement=0,
                    avg_engagement_per_post=0.0
                )
            )

        logger.info(
            f"Generating digest for topic: {topic}",
            extra={
                "topic": topic,
                "num_items": len(items),
                "time_window": f"{time_window_start} to {time_window_end}"
            }
        )

        # Prepare items for prompt (with token management)
        posts = self._prepare_posts_for_prompt(items)

        # Build prompt
        prompt = build_digest_prompt(
            topic=topic,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            posts=posts,
            total_items=len(items)
        )

        try:
            # Call LLM with JSON mode
            response = await self._call_llm_json(prompt)

            # Parse and validate response
            result = DigestResult(**response)

            logger.info(
                f"Successfully generated digest for {topic}",
                extra={
                    "num_highlights": len(result.highlights),
                    "sentiment": result.sentiment
                }
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate digest: {e}")
            # Retry once
            logger.info("Retrying digest generation...")
            try:
                response = await self._call_llm_json(prompt)
                result = DigestResult(**response)
                return result
            except Exception as retry_error:
                logger.error(f"Retry also failed: {retry_error}")
                raise

    def _prepare_posts_for_prompt(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare items for the LLM prompt with token management.

        Ranks items by engagement and selects top items to fit within token limit.

        Args:
            items: List of item dictionaries

        Returns:
            List of prepared post dictionaries
        """
        # Calculate engagement scores
        for item in items:
            metrics = item.get('metrics', {})
            item['engagement_score'] = (
                metrics.get('likes', 0) +
                metrics.get('retweets', 0) * 2 +
                metrics.get('replies', 0) * 1.5
            )

        # Sort by engagement
        sorted_items = sorted(items, key=lambda x: x['engagement_score'], reverse=True)

        # Estimate tokens and select items
        selected_items = []
        total_chars = 0
        max_chars = self.max_tokens * 3  # Rough estimate: 1 token ≈ 3 chars

        for item in sorted_items:
            text_length = len(item.get('text', ''))
            if total_chars + text_length > max_chars:
                break
            selected_items.append(item)
            total_chars += text_length

        logger.info(
            f"Selected {len(selected_items)} posts out of {len(items)} for digest generation",
            extra={
                "selected": len(selected_items),
                "total": len(items)
            }
        )

        return selected_items

    async def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM API and expect JSON response.

        Args:
            prompt: The prompt to send

        Returns:
            Parsed JSON response

        Raises:
            Exception: If API call fails or response is invalid
        """
        try:
            response = await self.client.post(
                f"{self.chat_base_url}/chat/completions",
                json={
                    "model": self.chat_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that always responds with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                headers={
                    "Authorization": f"Bearer {self.chat_api_key}"
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract content from response
            content = data["choices"][0]["message"]["content"]

            # Parse JSON
            result = json.loads(content)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
