"""
Graphiti Client Configuration

Defines configuration settings for the Graphiti knowledge graph client,
supporting multiple storage backends (memory, PostgreSQL).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import os


class BackendType(Enum):
    """Supported storage backend types."""
    MEMORY = "memory"
    POSTGRES = "postgres"
    NEO4J = "neo4j"


@dataclass
class GraphitiConfig:
    """
    Configuration for the Graphiti knowledge graph client.

    Supports multiple backends:
    - memory: In-memory storage (for testing, no persistence)
    - postgres: PostgreSQL + pgvector (for production)

    Environment Variables:
        KNOWLEDGE_BACKEND: Backend type (memory, postgres). Default: memory
        KNOWLEDGE_DB_HOST: PostgreSQL host. Default: localhost
        KNOWLEDGE_DB_PORT: PostgreSQL port. Default: 5432
        KNOWLEDGE_DB_NAME: Database name. Default: knowledge_graph
        KNOWLEDGE_DB_USER: Database user. Default: knowledge
        KNOWLEDGE_DB_PASSWORD: Database password. Default: (empty)
        KNOWLEDGE_EMBEDDING_DIM: Embedding vector dimension. Default: 1536

    Attributes:
        backend: Storage backend type (memory or postgres)
        host: Database host for postgres backend
        port: Database port for postgres backend
        database: Database name
        user: Database username
        password: Database password
        embedding_dim: Dimension of embedding vectors
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
    """

    # Backend selection
    backend: BackendType = field(
        default_factory=lambda: BackendType(os.getenv("KNOWLEDGE_BACKEND", "memory"))
    )

    # PostgreSQL connection settings
    host: str = field(default_factory=lambda: os.getenv("KNOWLEDGE_DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("KNOWLEDGE_DB_PORT", "5432")))
    database: str = field(default_factory=lambda: os.getenv("KNOWLEDGE_DB_NAME", "knowledge_graph"))
    user: str = field(default_factory=lambda: os.getenv("KNOWLEDGE_DB_USER", "knowledge"))
    password: str = field(default_factory=lambda: os.getenv("KNOWLEDGE_DB_PASSWORD", ""))

    # Neo4j connection settings
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "devpassword"))
    neo4j_database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))

    # Embedding settings
    embedding_dim: int = field(default_factory=lambda: int(os.getenv("KNOWLEDGE_EMBEDDING_DIM", "1536")))

    # Client behavior
    timeout: int = field(default_factory=lambda: int(os.getenv("KNOWLEDGE_TIMEOUT", "30")))
    max_retries: int = 3

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.backend == BackendType.POSTGRES:
            if not self.host:
                raise ValueError("Database host cannot be empty for postgres backend")
            if self.port <= 0 or self.port > 65535:
                raise ValueError(f"Invalid port number: {self.port}")
            if not self.database:
                raise ValueError("Database name cannot be empty")

        if self.backend == BackendType.NEO4J:
            if not self.neo4j_uri:
                raise ValueError("Neo4j URI cannot be empty for neo4j backend")
            if not self.neo4j_user:
                raise ValueError("Neo4j user cannot be empty")

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        if self.embedding_dim <= 0:
            raise ValueError("Embedding dimension must be positive")

    @property
    def connection_string(self) -> str:
        """
        Generate the PostgreSQL connection string.

        Returns:
            A formatted connection string for psycopg.
        """
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def for_postgres(
        cls,
        host: str = "localhost",
        port: int = 5432,
        database: str = "knowledge_graph",
        user: str = "knowledge",
        password: str = "",
    ) -> "GraphitiConfig":
        """
        Create a configuration for PostgreSQL backend.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password

        Returns:
            GraphitiConfig configured for PostgreSQL
        """
        return cls(
            backend=BackendType.POSTGRES,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

    @classmethod
    def for_memory(cls) -> "GraphitiConfig":
        """
        Create a configuration for in-memory backend.

        Returns:
            GraphitiConfig configured for memory storage
        """
        return cls(backend=BackendType.MEMORY)

    @classmethod
    def for_neo4j(
        cls,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "devpassword",
        database: str = "neo4j",
    ) -> "GraphitiConfig":
        """
        Create a configuration for Neo4j backend.

        Args:
            uri: Neo4j Bolt URI
            user: Database user
            password: Database password
            database: Database name

        Returns:
            GraphitiConfig configured for Neo4j
        """
        return cls(
            backend=BackendType.NEO4J,
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            neo4j_database=database,
        )
