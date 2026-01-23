"""
Graphiti Client Wrapper

Provides a high-level Python client for interacting with the knowledge graph.
Supports multiple storage backends (memory, PostgreSQL) with a unified API.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

from .config import GraphitiConfig, BackendType
from .models import Node, Edge
from .backends.base import StorageBackend
from .backends.memory import MemoryBackend

logger = logging.getLogger(__name__)


class GraphitiClient:
    """
    High-level client for the knowledge graph.

    Provides a unified interface for interacting with the knowledge graph
    regardless of the underlying storage backend.

    Supports:
    - Memory backend (for testing, no persistence)
    - PostgreSQL + pgvector backend (for production)

    Example:
        >>> # In-memory (default)
        >>> client = GraphitiClient()
        >>> client.connect()

        >>> # PostgreSQL
        >>> config = GraphitiConfig.for_postgres(host="192.168.1.100", password="secret")
        >>> client = GraphitiClient(config)
        >>> client.connect()

        >>> # Add nodes
        >>> node = Node(type="decision", content="Use PostgreSQL for persistence")
        >>> client.add_node(node)
    """

    def __init__(self, config: Optional[GraphitiConfig] = None):
        """
        Initialize the Graphiti client.

        Args:
            config: Optional configuration object. If not provided, uses
                   default configuration from environment variables.
        """
        self.config = config or GraphitiConfig()
        self._backend: Optional[StorageBackend] = None
        self._create_backend()
        logger.info(f"Initialized GraphitiClient with backend={self.config.backend.value}")

    def _create_backend(self) -> None:
        """Create the appropriate storage backend based on configuration."""
        if self.config.backend == BackendType.MEMORY:
            self._backend = MemoryBackend()

        elif self.config.backend == BackendType.POSTGRES:
            from .backends.postgres import PostgresBackend
            self._backend = PostgresBackend(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                embedding_dim=self.config.embedding_dim,
            )

        elif self.config.backend == BackendType.NEO4J:
            from .backends.neo4j import Neo4jBackend
            self._backend = Neo4jBackend(
                uri=self.config.neo4j_uri,
                user=self.config.neo4j_user,
                password=self.config.neo4j_password,
                database=self.config.neo4j_database,
                embedding_dim=self.config.embedding_dim,
            )

        else:
            raise ValueError(f"Unsupported backend type: {self.config.backend}")

    def connect(self) -> None:
        """
        Establish a connection to the storage backend.

        Raises:
            ConnectionError: If unable to connect
        """
        if self._backend.is_connected():
            logger.warning("Client is already connected")
            return

        try:
            self._backend.connect()
            logger.info(f"Connected to {self.config.backend.value} backend")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Unable to connect to backend: {e}")

    def disconnect(self) -> None:
        """Close the connection to the storage backend."""
        if not self._backend.is_connected():
            logger.warning("Client is not connected")
            return

        self._backend.disconnect()
        logger.info("Disconnected from backend")

    def is_connected(self) -> bool:
        """Check if the client is currently connected."""
        return self._backend.is_connected()

    # Node operations

    def add_node(self, node: Node) -> str:
        """
        Add a new node to the knowledge graph.

        Args:
            node: The node to add

        Returns:
            The UUID of the created node

        Raises:
            ConnectionError: If not connected
        """
        self._ensure_connected()
        return self._backend.add_node(node)

    def create_node(self, node: Node) -> Node:
        """
        Create a new node in the knowledge graph.

        Args:
            node: The node to create

        Returns:
            The created node object
        """
        self._ensure_connected()
        self._backend.add_node(node)
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Retrieve a node by its UUID.

        Args:
            node_id: The UUID of the node to retrieve

        Returns:
            The node if found, None otherwise
        """
        self._ensure_connected()
        return self._backend.get_node(node_id)

    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a node's properties.

        Args:
            node_id: The UUID of the node to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if node not found
        """
        self._ensure_connected()
        return self._backend.update_node(node_id, updates)

    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and its connected edges.

        Args:
            node_id: The UUID of the node to delete

        Returns:
            True if deleted, False if node not found
        """
        self._ensure_connected()
        return self._backend.delete_node(node_id)

    def query_nodes(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Node]:
        """
        Query nodes with optional filters.

        Args:
            filters: Optional filter criteria (e.g., {"type": "decision"})
            limit: Maximum number of nodes to return

        Returns:
            List of nodes matching the filters
        """
        self._ensure_connected()
        return self._backend.query_nodes(filters, limit)

    def query_nodes_by_time(
        self,
        start: datetime,
        end: datetime,
        node_type: Optional[str] = None,
    ) -> List[Node]:
        """
        Query nodes within a time range.

        Args:
            start: Start of time range
            end: End of time range
            node_type: Optional type filter

        Returns:
            List of nodes in the time range
        """
        self._ensure_connected()
        return self._backend.query_nodes_by_time(start, end, node_type)

    # Edge operations

    def add_edge(self, edge: Edge) -> str:
        """
        Add a new edge to the knowledge graph.

        Args:
            edge: The edge to add

        Returns:
            The UUID of the created edge
        """
        self._ensure_connected()
        return self._backend.add_edge(edge)

    def create_edge(self, edge: Edge) -> Edge:
        """
        Create a new edge in the knowledge graph.

        Args:
            edge: The edge to create

        Returns:
            The created edge object
        """
        self._ensure_connected()
        self._backend.add_edge(edge)
        return edge

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """
        Retrieve an edge by its UUID.

        Args:
            edge_id: The UUID of the edge to retrieve

        Returns:
            The edge if found, None otherwise
        """
        self._ensure_connected()
        return self._backend.get_edge(edge_id)

    def delete_edge(self, edge_id: str) -> bool:
        """
        Delete an edge from the knowledge graph.

        Args:
            edge_id: The UUID of the edge to delete

        Returns:
            True if deleted, False if edge not found
        """
        self._ensure_connected()
        return self._backend.delete_edge(edge_id)

    def query_edges(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Edge]:
        """
        Query edges with optional filters.

        Args:
            filters: Optional filter criteria (e.g., {"type": "contains"})
            limit: Maximum number of edges to return

        Returns:
            List of edges matching the filters
        """
        self._ensure_connected()
        return self._backend.query_edges(filters, limit)

    # Search operations

    def search_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[Node, float]]:
        """
        Search for nodes similar to the given embedding.

        Args:
            embedding: The query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of (node, score) tuples sorted by similarity
        """
        self._ensure_connected()
        return self._backend.search_similar(embedding, limit, min_score)

    # Legacy compatibility - expose internal storage for queries.py
    # TODO: Migrate queries.py to use client methods instead

    @property
    def _nodes(self) -> Dict[str, Node]:
        """Legacy access to nodes storage (for backward compatibility)."""
        if hasattr(self._backend, '_nodes'):
            return self._backend._nodes
        # For PostgreSQL backend, fetch all nodes (not recommended for large DBs)
        logger.warning("Accessing _nodes on non-memory backend - fetching all nodes")
        nodes = self._backend.query_nodes(limit=10000)
        return {n.uuid: n for n in nodes}

    @property
    def _edges(self) -> Dict[str, Edge]:
        """Legacy access to edges storage (for backward compatibility)."""
        if hasattr(self._backend, '_edges'):
            return self._backend._edges
        logger.warning("Accessing _edges on non-memory backend - fetching all edges")
        edges = self._backend.query_edges(limit=10000)
        return {e.uuid: e for e in edges}

    # Helper methods

    def _ensure_connected(self) -> None:
        """Ensure we have an active connection."""
        if not self._backend.is_connected():
            raise ConnectionError("Client is not connected. Call connect() first.")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation of the client."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"GraphitiClient(backend={self.config.backend.value}, status={status})"
