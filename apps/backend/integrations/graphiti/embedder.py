"""
Centralized Embedding Generation for Knowledge Graph
=====================================================

Provides a singleton embedder for generating vector embeddings across
all node creation and query paths. Uses Ollama for local embedding
generation with graceful degradation when unavailable.

Usage:
    from apps.backend.integrations.graphiti.embedder import embed_text

    embedding = embed_text("Some text to embed")
    if embedding is None:
        # Handle graceful degradation
        pass
"""

import logging
from typing import List, Optional

from .providers.ollama_embedder import (
    EmbedderError,
    OllamaConnectionError,
    OllamaEmbedder,
)

logger = logging.getLogger(__name__)

_embedder: Optional[OllamaEmbedder] = None


def get_embedder() -> OllamaEmbedder:
    """
    Get or create the Ollama embedder singleton.

    Returns:
        Configured OllamaEmbedder instance

    Note:
        Configuration is read from environment variables:
        - OLLAMA_EMBEDDING_MODEL (default: embeddinggemma)
        - OLLAMA_BASE_URL (default: http://localhost:11434)
        - OLLAMA_EMBEDDING_DIM (auto-detected if not set)
    """
    global _embedder
    if _embedder is None:
        _embedder = OllamaEmbedder()
        logger.info(f"Initialized embedder: {_embedder}")
    return _embedder


def embed_text(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text with graceful degradation.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector, or None on failure.
        Returns None if:
        - Text is empty or whitespace
        - Ollama server is not running
        - Embedding generation fails for any reason

    Note:
        This function never raises exceptions - it returns None on failure
        to allow node creation to proceed without embeddings.
    """
    if not text or not text.strip():
        return None

    try:
        return get_embedder().embed(text)
    except OllamaConnectionError as e:
        logger.warning(f"Ollama not available - embedding skipped: {e}")
        return None
    except EmbedderError as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected embedding error: {e}")
        return None


def get_embedding_dimension() -> int:
    """
    Get the configured embedding dimension.

    Returns:
        The embedding dimension for the configured model.

    Raises:
        EmbedderError: If dimension cannot be determined
    """
    return get_embedder().embedding_dim


def reset_embedder() -> None:
    """
    Reset the embedder singleton (useful for testing or reconfiguration).
    """
    global _embedder
    _embedder = None
