"""
Graphiti Embedding Providers

This module provides embedding generation providers for semantic search
functionality in the knowledge graph.
"""

from .ollama_embedder import (
    KNOWN_OLLAMA_EMBEDDING_MODELS,
    get_embedding_dim_for_model,
    OllamaEmbedder,
    create_ollama_embedder,
)

__all__ = [
    "KNOWN_OLLAMA_EMBEDDING_MODELS",
    "get_embedding_dim_for_model",
    "OllamaEmbedder",
    "create_ollama_embedder",
]
