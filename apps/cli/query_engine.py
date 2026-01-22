"""
Query Engine for CLI

Provides a high-level query interface for the Natural Language Query CLI.
Wraps Graphiti search functions to enable semantic search, project-scoped queries,
and specialized entity retrieval (tasks, decisions, sessions).
"""

from typing import List, Optional, Tuple
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti import queries
from apps.cli.config import CLIConfig

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    High-level query engine for the CLI application.

    This class provides a unified interface for querying the knowledge graph,
    abstracting away the details of the underlying Graphiti search functions.
    It manages client connections and provides convenience methods for common
    query patterns.

    Attributes:
        config: CLI configuration settings
        _client: GraphitiClient instance for backend communication
        _connected: Whether the engine is connected to the backend

    Example:
        >>> engine = QueryEngine()
        >>> engine.connect()
        >>> results = engine.search("authentication implementation")
        >>> for node, score in results:
        ...     print(f"{node.type}: {node.content[:50]} (score: {score:.2f})")
        >>> engine.disconnect()
    """

    def __init__(self, config: Optional[CLIConfig] = None):
        """
        Initialize the query engine.

        Args:
            config: Optional CLI configuration. If not provided, uses default configuration.
        """
        self.config = config or CLIConfig()
        self._client: Optional[GraphitiClient] = None
        self._connected = False
        logger.info("Initialized QueryEngine")

    def connect(self) -> None:
        """
        Establish connection to the Graphiti backend.

        Raises:
            ConnectionError: If unable to connect to the backend.
        """
        if self._connected:
            logger.warning("QueryEngine is already connected")
            return

        try:
            logger.info("Connecting to Graphiti backend")
            self._client = GraphitiClient()
            self._client.connect()
            self._connected = True
            logger.info("Successfully connected to Graphiti backend")
        except Exception as e:
            logger.error(f"Failed to connect to Graphiti backend: {e}")
            raise ConnectionError(f"Unable to connect to backend: {e}")

    def disconnect(self) -> None:
        """
        Close connection to the Graphiti backend.
        """
        if not self._connected:
            logger.warning("QueryEngine is not connected")
            return

        try:
            logger.info("Disconnecting from Graphiti backend")
            if self._client:
                self._client.disconnect()
                self._client = None
            self._connected = False
            logger.info("Successfully disconnected from Graphiti backend")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def is_connected(self) -> bool:
        """
        Check if the engine is connected to the backend.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected

    def search(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> List[Tuple[Node, float]]:
        """
        Perform semantic search across the entire knowledge graph.

        Uses embedding-based similarity to find nodes that are semantically
        similar to the query, regardless of exact keyword matches.

        Args:
            query: The search query (natural language or keywords)
            limit: Maximum number of results. Defaults to config.default_limit.

        Returns:
            List of (Node, score) tuples, sorted by relevance (highest first).

        Example:
            >>> results = engine.search("why did we choose ROS2?")
            >>> for node, score in results:
            ...     print(f"{node.type}: {node.content[:50]}")
        """
        effective_limit = min(limit or self.config.default_limit, self.config.max_limit)
        logger.info(f"Searching for: '{query}' (limit={effective_limit})")

        return queries.search_semantic(
            query=query,
            limit=effective_limit,
            client=self._client
        )

    def search_in_project(
        self,
        project_id: str,
        query: str,
        limit: Optional[int] = None
    ) -> List[Tuple[Node, float]]:
        """
        Perform semantic search within a specific project scope.

        Searches only within nodes that are hierarchically contained under
        the specified project node.

        Args:
            project_id: The UUID or identifier of the project to search within
            query: The search query (natural language or keywords)
            limit: Maximum number of results. Defaults to config.default_limit.

        Returns:
            List of (Node, score) tuples, sorted by relevance (highest first).

        Example:
            >>> results = engine.search_in_project("proj-123", "authentication")
            >>> for node, score in results:
            ...     print(f"{node.type}: {node.content[:50]}")
        """
        effective_limit = min(limit or self.config.default_limit, self.config.max_limit)
        logger.info(f"Searching in project '{project_id}' for: '{query}' (limit={effective_limit})")

        return queries.search_scoped(
            scope_node_id=project_id,
            query=query,
            limit=effective_limit,
            client=self._client
        )

    def get_related(
        self,
        node_id: str,
        edge_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Tuple[Node, Edge]]:
        """
        Get all nodes directly related to a given node.

        Retrieves nodes that are connected to the specified node via edges,
        optionally filtering by edge type and direction.

        Args:
            node_id: The UUID of the node to find relations for
            edge_type: Optional edge type filter (e.g., 'contains', 'references')
            direction: Direction of edges ("outgoing", "incoming", or "both")

        Returns:
            List of (Node, Edge) tuples for each related node.

        Example:
            >>> related = engine.get_related(project_id, edge_type="contains")
            >>> for node, edge in related:
            ...     print(f"{node.type}: {node.content[:50]}")
        """
        logger.info(f"Getting related nodes for: {node_id} (type={edge_type}, direction={direction})")

        return queries.get_related(
            node_id=node_id,
            edge_type=edge_type,
            direction=direction,
            client=self._client
        )

    def traverse(
        self,
        node_id: str,
        depth: int = 1
    ) -> dict:
        """
        Traverse the knowledge graph from a starting node.

        Performs a breadth-first traversal of the graph, following all edges
        from the starting node up to a specified depth.

        Args:
            node_id: The UUID of the starting node
            depth: Maximum depth to traverse (default: 1)

        Returns:
            Dictionary mapping depth levels to lists of nodes at that depth.

        Example:
            >>> results = engine.traverse(project_id, depth=2)
            >>> print(f"Direct neighbors: {len(results['1'])}")
        """
        logger.info(f"Traversing from node: {node_id} (depth={depth})")

        return queries.traverse(
            node_id=node_id,
            depth=depth,
            client=self._client
        )

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation of the engine."""
        status = "connected" if self._connected else "disconnected"
        return f"QueryEngine(status={status})"
