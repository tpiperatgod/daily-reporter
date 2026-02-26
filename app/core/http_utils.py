"""HTTP utilities for API calls with retry logic.

This module provides shared retry functionality for HTTP clients
to eliminate code duplication in embedding providers.
"""

import asyncio
from typing import Optional, Dict, Any, Callable, Set
import httpx

from app.core.logging import get_logger
from app.core.constants import RetryConfig

logger = get_logger(__name__)


async def api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    json_data: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    max_retries: int = RetryConfig.MAX_ATTEMPTS,
    initial_backoff: float = RetryConfig.INITIAL_BACKOFF,
    retryable_status_codes: Optional[Set[int]] = None,
    error_handler: Optional[Callable[[httpx.HTTPStatusError, int], Any]] = None,
) -> dict:
    """
    Make HTTP API call with exponential backoff retry.

    This utility eliminates ~100 lines of duplicate retry logic
    across embedding providers (OpenAI, Ollama).

    Args:
        client: httpx AsyncClient instance
        method: HTTP method ("POST", "GET", etc.)
        url: Full URL for the API endpoint
        json_data: Optional JSON payload
        headers: Optional HTTP headers
        max_retries: Maximum number of retry attempts (default: 5)
        initial_backoff: Initial backoff time in seconds (default: 1.0)
        retryable_status_codes: Set of status codes that should trigger retry
                               (default: {429} for rate limits)
        error_handler: Optional callback for custom error handling.
                      Should return None to continue retry, or a value to return immediately.
                      Signature: (error: httpx.HTTPStatusError, attempt: int) -> Optional[Any]

    Returns:
        Parsed JSON response from API

    Raises:
        Exception: If all retries exhausted or non-retryable error

    Example:
        # OpenAI with custom error handling
        def handle_openai_errors(error, attempt):
            if error.response.status_code == 401:
                logger.error("Auth failed")
                raise
            elif error.response.status_code == 400:
                return {"data": [{"embedding": None}]}  # Graceful degradation
            return None  # Continue retry

        result = await api_call_with_retry(
            client=client,
            method="POST",
            url="https://api.openai.com/v1/embeddings",
            json_data={"input": "text", "model": "text-embedding-3-small"},
            headers={"Authorization": f"Bearer {api_key}"},
            error_handler=handle_openai_errors
        )
    """
    if retryable_status_codes is None:
        retryable_status_codes = {429}  # Rate limit by default

    backoff = initial_backoff

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method=method, url=url, json=json_data, headers=headers)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            # Allow custom error handler to process
            if error_handler:
                result = error_handler(e, attempt)
                if result is not None:
                    return result

            # Check if this status code should trigger retry
            if e.response.status_code in retryable_status_codes:
                if attempt < max_retries:
                    logger.warning(
                        f"HTTP {e.response.status_code}, retrying in {backoff}s "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"HTTP {e.response.status_code} - all retries exhausted")
                    raise
            else:
                # Non-retryable status code
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                raise

        except httpx.TimeoutException:
            if attempt < max_retries:
                logger.warning(f"Request timeout, retrying in {backoff}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            else:
                logger.error("Request timeout - all retries exhausted")
                raise

        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise

    raise Exception(f"Failed after {max_retries + 1} attempts")


__all__ = ["api_call_with_retry"]
