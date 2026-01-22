"""
Ollama Embedder Provider
========================

Ollama embedder implementation for generating vector embeddings using local
Ollama models. This enables fully offline semantic search capabilities.

Supported models with known dimensions:
- embeddinggemma (768) - Google's lightweight embedding model
- nomic-embed-text (768) - Nomic's embedding model with large context
- mxbai-embed-large (1024) - MixedBread AI large embedding model
- bge-large (1024) - BAAI general embedding large
- all-minilm (384) - Small, fast embedding model

Usage:
    embedder = OllamaEmbedder(model="embeddinggemma")
    embedding = embedder.embed("Some text to embed")
    embeddings = embedder.embed_batch(["Text 1", "Text 2"])
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

import requests


class EmbedderError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class OllamaConnectionError(EmbedderError):
    """Exception raised when Ollama server is not reachable."""
    pass


class ModelNotFoundError(EmbedderError):
    """Exception raised when the specified model is not available."""
    pass


class DimensionMismatchError(EmbedderError):
    """Exception raised when embedding dimensions don't match expected."""
    pass


# Known Ollama embedding models and their default dimensions
# Users can override with OLLAMA_EMBEDDING_DIM env var
KNOWN_OLLAMA_EMBEDDING_MODELS: dict[str, int] = {
    # Google EmbeddingGemma (supports 128-768 via MRL)
    "embeddinggemma": 768,
    "embeddinggemma:300m": 768,
    # Qwen3 Embedding series (support flexible dimensions)
    "qwen3-embedding": 1024,
    "qwen3-embedding:0.6b": 1024,
    "qwen3-embedding:4b": 2560,
    "qwen3-embedding:8b": 4096,
    # Other popular models
    "nomic-embed-text": 768,
    "nomic-embed-text:latest": 768,
    "mxbai-embed-large": 1024,
    "mxbai-embed-large:latest": 1024,
    "bge-large": 1024,
    "bge-large:latest": 1024,
    "bge-m3": 1024,
    "bge-m3:latest": 1024,
    "all-minilm": 384,
    "all-minilm:latest": 384,
}


def get_embedding_dim_for_model(model_name: str, configured_dim: int = 0) -> int:
    """
    Get the embedding dimension for an Ollama model.

    Args:
        model_name: The Ollama model name (e.g., "embeddinggemma", "qwen3-embedding:8b")
        configured_dim: User-configured dimension (takes precedence if > 0)

    Returns:
        Embedding dimension to use

    Raises:
        EmbedderError: If model is unknown and no dimension configured
    """
    # User override takes precedence
    if configured_dim > 0:
        return configured_dim

    # Check known models (exact match first)
    if model_name in KNOWN_OLLAMA_EMBEDDING_MODELS:
        return KNOWN_OLLAMA_EMBEDDING_MODELS[model_name]

    # Try without tag suffix
    base_name = model_name.split(":")[0]
    if base_name in KNOWN_OLLAMA_EMBEDDING_MODELS:
        return KNOWN_OLLAMA_EMBEDDING_MODELS[base_name]

    raise EmbedderError(
        f"Unknown Ollama embedding model: {model_name}. "
        f"Please set OLLAMA_EMBEDDING_DIM or use a known model: "
        f"{', '.join(sorted(set(k.split(':')[0] for k in KNOWN_OLLAMA_EMBEDDING_MODELS.keys())))}"
    )


@dataclass
class OllamaEmbedderConfig:
    """
    Configuration for the Ollama embedder.

    Attributes:
        model: The Ollama embedding model name
        base_url: Base URL for the Ollama API
        embedding_dim: Expected embedding dimension (auto-detected if 0)
        timeout: Request timeout in seconds
    """
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma"))
    base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    embedding_dim: int = field(default_factory=lambda: int(os.getenv("OLLAMA_EMBEDDING_DIM", "0")))
    timeout: int = field(default_factory=lambda: int(os.getenv("OLLAMA_TIMEOUT", "60")))

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.model:
            raise ValueError("Ollama embedding model cannot be empty")
        if not self.base_url:
            raise ValueError("Ollama base URL cannot be empty")


class OllamaEmbedder:
    """
    Ollama embedder for generating vector embeddings.

    This class provides a Pythonic interface for generating embeddings
    using Ollama's local API. It supports auto-dimension detection for
    known models and validates embedding dimensions.

    Attributes:
        config: Configuration for this embedder instance
        embedding_dim: The dimension of generated embeddings

    Example:
        >>> embedder = OllamaEmbedder()
        >>> embedding = embedder.embed("Hello world")
        >>> print(f"Embedding dimension: {len(embedding)}")
    """

    def __init__(self, config: Optional[OllamaEmbedderConfig] = None, model: Optional[str] = None):
        """
        Initialize the Ollama embedder.

        Args:
            config: Optional configuration object
            model: Optional model name (shortcut, creates config internally)
        """
        if config:
            self.config = config
        elif model:
            self.config = OllamaEmbedderConfig(model=model)
        else:
            self.config = OllamaEmbedderConfig()

        # Auto-detect embedding dimension if not configured
        self.embedding_dim = get_embedding_dim_for_model(
            self.config.model,
            self.config.embedding_dim
        )

        self._verified = False

    @property
    def api_url(self) -> str:
        """Get the Ollama embeddings API URL."""
        return f"{self.config.base_url.rstrip('/')}/api/embeddings"

    def verify_connection(self) -> bool:
        """
        Verify that Ollama is running and the model is available.

        Returns:
            True if connection is verified

        Raises:
            OllamaConnectionError: If Ollama server is not reachable
            ModelNotFoundError: If the specified model is not available
        """
        try:
            tags_url = f"{self.config.base_url.rstrip('/')}/api/tags"
            resp = requests.get(tags_url, timeout=10)

            if resp.status_code != 200:
                raise OllamaConnectionError(
                    f"Ollama server returned status {resp.status_code}. "
                    f"Ensure Ollama is running: ollama serve"
                )

            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if model is available
            model_found = any(
                self.config.model in name or self.config.model.split(":")[0] in name
                for name in model_names
            )

            if not model_found:
                raise ModelNotFoundError(
                    f"Model '{self.config.model}' not found. "
                    f"Pull it with: ollama pull {self.config.model}\n"
                    f"Available models: {', '.join(model_names)}"
                )

            self._verified = True
            return True

        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError(
                "Cannot connect to Ollama server. "
                "Ensure Ollama is running: ollama serve"
            )

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            A list of floats representing the embedding vector

        Raises:
            EmbedderError: If embedding generation fails
            DimensionMismatchError: If embedding dimension doesn't match expected
        """
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        try:
            resp = requests.post(
                self.api_url,
                json={"model": self.config.model, "prompt": text},
                timeout=self.config.timeout,
            )

            if resp.status_code != 200:
                raise EmbedderError(
                    f"Ollama embedding failed with status {resp.status_code}: "
                    f"{resp.text[:200]}"
                )

            data = resp.json()
            embedding = data.get("embedding", [])

            if not embedding:
                raise EmbedderError("Ollama returned empty embedding")

            # Validate dimension
            if len(embedding) != self.embedding_dim:
                raise DimensionMismatchError(
                    f"Embedding dimension mismatch: got {len(embedding)}, "
                    f"expected {self.embedding_dim}. "
                    f"Update OLLAMA_EMBEDDING_DIM={len(embedding)} in your config"
                )

            return embedding

        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError(
                "Cannot connect to Ollama server. "
                "Ensure Ollama is running: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise EmbedderError(
                f"Ollama embedding request timed out after {self.config.timeout}s. "
                f"Try increasing OLLAMA_TIMEOUT or using a faster model."
            )

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Note:
            Currently processes texts sequentially. Ollama doesn't have
            native batch embedding support.
        """
        return [self.embed(text) for text in texts]

    def get_status(self) -> dict:
        """
        Get the embedder status information.

        Returns:
            Dictionary with status information
        """
        status = {
            "model": self.config.model,
            "base_url": self.config.base_url,
            "embedding_dim": self.embedding_dim,
            "verified": self._verified,
        }

        try:
            self.verify_connection()
            status["connected"] = True
            status["error"] = None
        except EmbedderError as e:
            status["connected"] = False
            status["error"] = str(e)

        return status

    def __repr__(self) -> str:
        """String representation of the embedder."""
        return f"OllamaEmbedder(model={self.config.model}, dim={self.embedding_dim})"


def create_ollama_embedder(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    embedding_dim: Optional[int] = None,
) -> OllamaEmbedder:
    """
    Create an Ollama embedder with optional configuration overrides.

    This is a convenience factory function that creates an embedder
    with settings from environment variables and optional overrides.

    Args:
        model: Optional model name override
        base_url: Optional base URL override
        embedding_dim: Optional embedding dimension override

    Returns:
        Configured OllamaEmbedder instance

    Example:
        >>> embedder = create_ollama_embedder(model="nomic-embed-text")
        >>> embedding = embedder.embed("Hello world")
    """
    config = OllamaEmbedderConfig()

    if model:
        config.model = model
    if base_url:
        config.base_url = base_url
    if embedding_dim:
        config.embedding_dim = embedding_dim

    return OllamaEmbedder(config=config)
