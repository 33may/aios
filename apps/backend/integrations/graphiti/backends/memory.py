"""
In-memory storage backend for testing and development.
"""

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

from .base import StorageBackend
from ..models import Node, Edge

logger = logging.getLogger(__name__)


class MemoryBackend(StorageBackend):
    """
    In-memory storage backend.

    Stores all nodes and edges in Python dictionaries.
    Data is lost when the process exits.
    Useful for testing and development.
    """

    def __init__(self):
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._connected = False

    def connect(self) -> None:
        """Mark as connected (no-op for memory backend)."""
        self._connected = True
        logger.info("MemoryBackend connected")

    def disconnect(self) -> None:
        """Mark as disconnected (no-op for memory backend)."""
        self._connected = False
        logger.info("MemoryBackend disconnected")

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    # Node operations

    def add_node(self, node: Node) -> str:
        """Add a node to the graph."""
        self._nodes[node.uuid] = node
        logger.debug(f"Added node: {node.uuid} ({node.type})")
        return node.uuid

    def get_node(self, uuid: str) -> Optional[Node]:
        """Get a node by UUID."""
        return self._nodes.get(uuid)

    def update_node(self, uuid: str, updates: Dict[str, Any]) -> bool:
        """Update a node's properties."""
        node = self._nodes.get(uuid)
        if not node:
            return False

        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)

        node.updated_at = datetime.utcnow()
        return True

    def delete_node(self, uuid: str) -> bool:
        """Delete a node and its connected edges."""
        if uuid not in self._nodes:
            return False

        # Delete connected edges
        edges_to_delete = [
            e.uuid for e in self._edges.values()
            if e.source_id == uuid or e.target_id == uuid
        ]
        for edge_uuid in edges_to_delete:
            del self._edges[edge_uuid]

        del self._nodes[uuid]
        return True

    def query_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Node]:
        """Query nodes with optional filters."""
        results = list(self._nodes.values())

        if filters:
            if "type" in filters:
                results = [n for n in results if n.type == filters["type"]]

            if "project_id" in filters:
                results = [
                    n for n in results
                    if n.metadata and n.metadata.get("project_id") == filters["project_id"]
                ]

        return results[:limit]

    def query_nodes_by_time(
        self,
        start: datetime,
        end: datetime,
        node_type: Optional[str] = None,
    ) -> List[Node]:
        """Query nodes within a time range."""
        results = []

        for node in self._nodes.values():
            # Check time range
            in_range = (
                (start <= node.created_at <= end) or
                (start <= node.updated_at <= end)
            )
            if not in_range:
                continue

            # Check type filter
            if node_type and node.type != node_type:
                continue

            results.append(node)

        # Sort by created_at descending
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results

    # Edge operations

    def add_edge(self, edge: Edge) -> str:
        """Add an edge to the graph."""
        self._edges[edge.uuid] = edge
        logger.debug(f"Added edge: {edge.uuid} ({edge.type})")
        return edge.uuid

    def get_edge(self, uuid: str) -> Optional[Edge]:
        """Get an edge by UUID."""
        return self._edges.get(uuid)

    def delete_edge(self, uuid: str) -> bool:
        """Delete an edge."""
        if uuid not in self._edges:
            return False
        del self._edges[uuid]
        return True

    def query_edges(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Edge]:
        """Query edges with optional filters."""
        results = list(self._edges.values())

        if filters:
            if "type" in filters:
                results = [e for e in results if e.type == filters["type"]]
            if "source_id" in filters:
                results = [e for e in results if e.source_id == filters["source_id"]]
            if "target_id" in filters:
                results = [e for e in results if e.target_id == filters["target_id"]]

        return results[:limit]

    # Search operations

    def search_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[Node, float]]:
        """Search for nodes similar to the given embedding."""
        results: List[Tuple[Node, float]] = []

        for node in self._nodes.values():
            if node.embedding is None:
                continue

            # Compute cosine similarity
            score = self._cosine_similarity(embedding, node.embedding)
            if score >= min_score:
                results.append((node, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
