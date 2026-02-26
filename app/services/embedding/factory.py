"""Factory for creating embedding providers based on configuration."""

import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.openai_provider import OpenAIEmbeddingProvider
from app.services.embedding.ollama_provider import OllamaEmbeddingProvider

logger = get_logger(__name__)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Create and return the configured embedding provider.

    Uses LLM_EMBEDDING_PROVIDER setting to determine which provider to use.
    Validates configuration and checks service availability.

    Returns:
        Configured embedding provider instance

    Raises:
        ValueError: If provider is not configured correctly
        Exception: If provider service is not reachable
    """
    provider_type = settings.LLM_EMBEDDING_PROVIDER.lower()

    logger.info(f"Initializing embedding provider: {provider_type}")

    if provider_type == "openai":
        return _create_openai_provider()
    elif provider_type == "ollama":
        return _create_ollama_provider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_type}. Must be 'openai' or 'ollama'")


def _create_openai_provider() -> OpenAIEmbeddingProvider:
    """
    Create OpenAI-compatible embedding provider.

    Returns:
        OpenAIEmbeddingProvider instance

    Raises:
        ValueError: If required configuration is missing
    """
    base_url = settings.OPENAI_EMBEDDING_BASE_URL
    model = settings.OPENAI_EMBEDDING_MODEL
    api_key = settings.OPENAI_EMBEDDING_API_KEY

    # Validate required fields
    if not base_url:
        raise ValueError("OPENAI_EMBEDDING_BASE_URL must be set when using OpenAI provider")
    if not model:
        raise ValueError("OPENAI_EMBEDDING_MODEL must be set when using OpenAI provider")
    if not api_key:
        raise ValueError("OPENAI_EMBEDDING_API_KEY must be set when using OpenAI provider")

    logger.info(f"Using OpenAI-compatible embedding provider ({model} at {base_url})")

    return OpenAIEmbeddingProvider(
        base_url=base_url,
        model=model,
        api_key=api_key,
        batch_size=settings.LLM_EMBEDDING_BATCH_SIZE,
        max_retries=settings.LLM_EMBEDDING_RETRY_MAX_ATTEMPTS,
        initial_backoff=settings.LLM_EMBEDDING_RETRY_INITIAL_BACKOFF,
    )


def _create_ollama_provider() -> OllamaEmbeddingProvider:
    """
    Create Ollama embedding provider.

    Validates that Ollama service is reachable and model is available.

    Returns:
        OllamaEmbeddingProvider instance

    Raises:
        ValueError: If required configuration is missing
        Exception: If Ollama service is not reachable
    """
    base_url = settings.OLLAMA_EMBEDDING_BASE_URL
    model = settings.OLLAMA_EMBEDDING_MODEL

    if not base_url:
        raise ValueError("OLLAMA_EMBEDDING_BASE_URL must be set when using Ollama provider")
    if not model:
        raise ValueError("OLLAMA_EMBEDDING_MODEL must be set when using Ollama provider")

    # Validate Ollama service is reachable
    try:
        _validate_ollama_service(base_url, model)
    except Exception as e:
        logger.error(f"Failed to validate Ollama service: {e}")
        raise

    logger.info(f"Using Ollama embedding provider ({model} at {base_url})")

    return OllamaEmbeddingProvider(
        base_url=base_url,
        model=model,
        batch_size=settings.LLM_EMBEDDING_BATCH_SIZE,
        max_retries=settings.LLM_EMBEDDING_RETRY_MAX_ATTEMPTS,
        initial_backoff=settings.LLM_EMBEDDING_RETRY_INITIAL_BACKOFF,
    )


def _validate_ollama_service(base_url: str, model: str) -> None:
    """
    Validate that Ollama service is running and model is available.

    Args:
        base_url: Ollama API base URL
        model: Model name to check

    Raises:
        Exception: If service is not reachable or model is not found
    """
    try:
        # Check if Ollama is running
        client = httpx.Client(timeout=5.0)
        response = client.get(f"{base_url.rstrip('/')}/api/tags")
        response.raise_for_status()

        # Check if model is available
        data = response.json()
        available_models = [m["name"] for m in data.get("models", [])]

        if model not in available_models:
            logger.warning(
                f"Model '{model}' not found in Ollama. Available models: {available_models}. Run: ollama pull {model}"
            )
            # Don't fail - model will be pulled on first use
        else:
            logger.info(f"Ollama model '{model}' is available")

        client.close()

    except httpx.ConnectError:
        raise Exception(f"Cannot connect to Ollama at {base_url}. Is Ollama running? Try: ollama serve")
    except Exception as e:
        raise Exception(f"Failed to validate Ollama service: {e}")
