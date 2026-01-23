"""
Abstract base class for knowledge graph storage backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..models import Node, Edge


class StorageBackend(ABC):
    """
    Abstract base class for knowledge graph storage.

    All storage backends must implement these methods to provide
    CRUD operations for nodes and edges.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the storage backend."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        pass

    # Node operations

    @abstractmethod
    def add_node(self, node: Node) -> str:
        """
        Add a node to the graph.

        Args:
            node: The node to add

        Returns:
            The UUID of the added node
        """
        pass

    @abstractmethod
    def get_node(self, uuid: str) -> Optional[Node]:
        """
        Get a node by UUID.

        Args:
            uuid: The node UUID

        Returns:
            The node if found, None otherwise
        """
        pass

    @abstractmethod
    def update_node(self, uuid: str, updates: Dict[str, Any]) -> bool:
        """
        Update a node's properties.

        Args:
            uuid: The node UUID
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if node not found
        """
        pass

    @abstractmethod
    def delete_node(self, uuid: str) -> bool:
        """
        Delete a node and its connected edges.

        Args:
            uuid: The node UUID

        Returns:
            True if deleted, False if node not found
        """
        pass

    @abstractmethod
    def query_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Node]:
        """
        Query nodes with optional filters.

        Args:
            filters: Optional filter criteria (type, metadata, etc.)
            limit: Maximum number of nodes to return

        Returns:
            List of matching nodes
        """
        pass

    @abstractmethod
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
        pass

    # Edge operations

    @abstractmethod
    def add_edge(self, edge: Edge) -> str:
        """
        Add an edge to the graph.

        Args:
            edge: The edge to add

        Returns:
            The UUID of the added edge
        """
        pass

    @abstractmethod
    def get_edge(self, uuid: str) -> Optional[Edge]:
        """
        Get an edge by UUID.

        Args:
            uuid: The edge UUID

        Returns:
            The edge if found, None otherwise
        """
        pass

    @abstractmethod
    def delete_edge(self, uuid: str) -> bool:
        """
        Delete an edge.

        Args:
            uuid: The edge UUID

        Returns:
            True if deleted, False if edge not found
        """
        pass

    @abstractmethod
    def query_edges(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Edge]:
        """
        Query edges with optional filters.

        Args:
            filters: Optional filter criteria (type, source_id, target_id)
            limit: Maximum number of edges to return

        Returns:
            List of matching edges
        """
        pass

    # Search operations

    @abstractmethod
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
        pass
