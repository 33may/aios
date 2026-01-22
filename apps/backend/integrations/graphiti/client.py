"""
Graphiti Client Wrapper

Provides a high-level Python client for interacting with the Graphiti knowledge
graph backend. Handles connection management, query execution, and CRUD operations
for nodes and edges.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .config import GraphitiConfig
from .models import Node, Edge

logger = logging.getLogger(__name__)


class GraphitiClient:
    """
    High-level client for the Graphiti knowledge graph.

    This client provides a Pythonic interface for interacting with the Graphiti
    backend, abstracting away low-level connection details and providing
    convenient methods for common operations.

    Attributes:
        config: The configuration for this client instance
        _connected: Whether the client is currently connected

    Example:
        >>> client = GraphitiClient()
        >>> client.connect()
        >>> node = Node(type="project", content="My AIOS Project")
        >>> client.add_node(node)
        >>> client.disconnect()
    """

    def __init__(self, config: Optional[GraphitiConfig] = None):
        """
        Initialize the Graphiti client.

        Args:
            config: Optional configuration object. If not provided, uses
                   default configuration from environment variables.
        """
        self.config = config or GraphitiConfig()
        self._connected = False
        self._driver = None
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        logger.info(f"Initialized GraphitiClient with host={self.config.host}")

    def connect(self) -> None:
        """
        Establish a connection to the Graphiti backend.

        Raises:
            ConnectionError: If unable to connect to the server
        """
        if self._connected:
            logger.warning("Client is already connected")
            return

        try:
            logger.info(f"Connecting to Graphiti at {self.config.connection_string}")
            # TODO: Implement actual connection logic with Neo4j/LadybugDB driver
            self._connected = True
            logger.info("Successfully connected to Graphiti")
        except Exception as e:
            logger.error(f"Failed to connect to Graphiti: {e}")
            raise ConnectionError(f"Unable to connect to Graphiti: {e}")

    def disconnect(self) -> None:
        """
        Close the connection to the Graphiti backend.
        """
        if not self._connected:
            logger.warning("Client is not connected")
            return

        try:
            logger.info("Disconnecting from Graphiti")
            # TODO: Implement actual disconnection logic
            if self._driver:
                self._driver = None
            self._connected = False
            logger.info("Successfully disconnected from Graphiti")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def is_connected(self) -> bool:
        """
        Check if the client is currently connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def add_node(self, node: Node) -> str:
        """
        Add a new node to the knowledge graph.

        Args:
            node: The node to add

        Returns:
            The UUID of the created node

        Raises:
            ConnectionError: If not connected to the server
            ValueError: If the node is invalid
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Adding node: type={node.type}, uuid={node.uuid}")
        self._nodes[node.uuid] = node
        return node.uuid

    def create_node(self, node: Node) -> Node:
        """
        Create a new node in the knowledge graph.

        Args:
            node: The node to create

        Returns:
            The created node object

        Raises:
            ConnectionError: If not connected to the server
            ValueError: If the node is invalid
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Creating node: type={node.type}, uuid={node.uuid}")
        self._nodes[node.uuid] = node
        return node

    def add_edge(self, edge: Edge) -> str:
        """
        Add a new edge to the knowledge graph.

        Args:
            edge: The edge to add

        Returns:
            The UUID of the created edge

        Raises:
            ConnectionError: If not connected to the server
            ValueError: If the edge is invalid
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Adding edge: type={edge.type}, source={edge.source_id}, target={edge.target_id}")
        self._edges[edge.uuid] = edge
        return edge.uuid

    def create_edge(self, edge: Edge) -> Edge:
        """
        Create a new edge in the knowledge graph.

        Args:
            edge: The edge to create

        Returns:
            The created edge object

        Raises:
            ConnectionError: If not connected to the server
            ValueError: If the edge is invalid
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Creating edge: type={edge.type}, source={edge.source_id}, target={edge.target_id}")
        self._edges[edge.uuid] = edge
        return edge

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """
        Retrieve an edge by its UUID.

        Args:
            edge_id: The UUID of the edge to retrieve

        Returns:
            The edge if found, None otherwise

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Retrieving edge: {edge_id}")
        return self._edges.get(edge_id)

    def update_edge(self, edge_id: str, updates: Dict[str, Any]) -> Optional[Edge]:
        """
        Update an existing edge's metadata.

        Args:
            edge_id: The UUID of the edge to update
            updates: Dictionary of fields to update

        Returns:
            The updated edge if found, None otherwise

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        edge = self._edges.get(edge_id)
        if not edge:
            logger.warning(f"Edge not found: {edge_id}")
            return None

        logger.info(f"Updating edge: {edge_id}")
        # Update metadata fields
        if 'metadata' in updates:
            if edge.metadata is None:
                edge.metadata = {}
            edge.metadata.update(updates['metadata'])
        # Update timestamp
        edge.updated_at = datetime.utcnow()

        return edge

    def delete_edge(self, edge_id: str) -> bool:
        """
        Delete an edge from the knowledge graph.

        Args:
            edge_id: The UUID of the edge to delete

        Returns:
            True if the edge was deleted, False if not found

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        if edge_id in self._edges:
            logger.info(f"Deleting edge: {edge_id}")
            del self._edges[edge_id]
            return True

        logger.warning(f"Edge not found for deletion: {edge_id}")
        return False

    def query_edges(self, filters: Dict[str, Any]) -> List[Edge]:
        """
        Query edges based on filters.

        Args:
            filters: Dictionary of filter criteria (e.g., {"type": "contains"})

        Returns:
            List of edges matching the filters

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Querying edges with filters: {filters}")

        results = []
        for edge in self._edges.values():
            match = True
            for key, value in filters.items():
                if key == 'type' and edge.type != value:
                    match = False
                    break
                elif key == 'source_id' and edge.source_id != value:
                    match = False
                    break
                elif key == 'target_id' and edge.target_id != value:
                    match = False
                    break
            if match:
                results.append(edge)

        return results

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Retrieve a node by its UUID.

        Args:
            node_id: The UUID of the node to retrieve

        Returns:
            The node if found, None otherwise

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Retrieving node: {node_id}")
        return self._nodes.get(node_id)

    def query_nodes(self, filters: Dict[str, Any]) -> List[Node]:
        """
        Query nodes based on filters.

        Args:
            filters: Dictionary of filter criteria (e.g., {"type": "project"})

        Returns:
            List of nodes matching the filters

        Raises:
            ConnectionError: If not connected to the server
        """
        if not self._connected:
            raise ConnectionError("Client is not connected. Call connect() first.")

        logger.info(f"Querying nodes with filters: {filters}")
        # TODO: Implement actual node query
        return []

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def __repr__(self) -> str:
        """String representation of the client."""
        status = "connected" if self._connected else "disconnected"
        return f"GraphitiClient(host={self.config.host}, status={status})"
