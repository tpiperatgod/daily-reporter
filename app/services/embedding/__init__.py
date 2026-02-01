"""Embedding provider abstraction layer."""

from .base import BaseEmbeddingProvider
from .factory import get_embedding_provider

__all__ = ["BaseEmbeddingProvider", "get_embedding_provider"]
