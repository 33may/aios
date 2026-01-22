"""
Graphiti Client Configuration

Defines configuration settings for the Graphiti knowledge graph client,
including database connection, API settings, and client behavior options.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class GraphitiConfig:
    """
    Configuration for the Graphiti client.

    This class encapsulates all settings required to connect to and interact
    with the Graphiti knowledge graph backend powered by LadybugDB.

    Attributes:
        host: The hostname or IP address of the Graphiti server
        port: The port number for the Graphiti server
        database: The name of the database to connect to
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts for failed requests
        api_key: Optional API key for authentication
        use_ssl: Whether to use SSL/TLS for connections
        embedding_model: The model to use for generating embeddings
    """

    host: str = field(default_factory=lambda: os.getenv("GRAPHITI_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("GRAPHITI_PORT", "7687")))
    database: str = field(default_factory=lambda: os.getenv("GRAPHITI_DB", "aios"))
    timeout: int = field(default_factory=lambda: int(os.getenv("GRAPHITI_TIMEOUT", "30")))
    max_retries: int = 3
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("GRAPHITI_API_KEY"))
    use_ssl: bool = field(default_factory=lambda: os.getenv("GRAPHITI_USE_SSL", "false").lower() == "true")
    embedding_model: str = field(default_factory=lambda: os.getenv("GRAPHITI_EMBEDDING_MODEL", "text-embedding-ada-002"))

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.host:
            raise ValueError("Graphiti host cannot be empty")
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")
        if not self.database:
            raise ValueError("Database name cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")

    @property
    def connection_string(self) -> str:
        """
        Generate the connection string for the Graphiti server.

        Returns:
            A formatted connection string based on the configuration.
        """
        protocol = "bolt+s" if self.use_ssl else "bolt"
        return f"{protocol}://{self.host}:{self.port}/{self.database}"
