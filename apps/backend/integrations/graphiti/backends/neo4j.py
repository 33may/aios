"""
Neo4j storage backend for graph-native knowledge storage.

Provides native graph storage with Cypher queries for efficient
traversal and relationship management.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

from .base import StorageBackend
from ..models import Node, Edge

logger = logging.getLogger(__name__)

# Optional import - only required when using Neo4jBackend
try:
    from neo4j import GraphDatabase, Driver
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None
    Driver = None


# Map our internal node types to Neo4j labels
NODE_TYPE_TO_LABEL = {
    "decision": "Decision",
    "task": "Task",
    "session": "Session",
    "concept": "Concept",
    "discovery": "Discovery",
    "project": "Project",
}

# Map edge types to Neo4j relationship types
EDGE_TYPE_TO_REL = {
    "relates_to": "RELATES_TO",
    "blocks": "BLOCKS",
    "spawned": "SPAWNED",
    "references": "REFERENCES",
    "led_to": "LED_TO",
    "contains": "CONTAINS",
    "similar_to": "SIMILAR_TO",
}


class Neo4jBackend(StorageBackend):
    """
    Neo4j storage backend for the knowledge graph.

    Provides native graph storage with efficient traversal queries.
    Supports vector similarity search via property storage (for use with
    external embedding comparison or Neo4j Graph Data Science library).

    Connection format:
        bolt://host:port
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "devpassword",
        database: str = "neo4j",
        embedding_dim: int = 1536,
    ):
        """
        Initialize Neo4j backend.

        Args:
            uri: Neo4j Bolt URI
            user: Database user
            password: Database password
            database: Database name (default: neo4j)
            embedding_dim: Dimension of embedding vectors
        """
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "neo4j driver is required for Neo4jBackend. "
                "Install with: pip install neo4j"
            )

        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._embedding_dim = embedding_dim
        self._driver: Optional[Driver] = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self._uri}")

        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to Neo4j."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Disconnected from Neo4j")

    def is_connected(self) -> bool:
        """Check if connected."""
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def _ensure_connected(self) -> None:
        """Ensure we have an active connection."""
        if not self.is_connected():
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

    def _get_label(self, node_type: str) -> str:
        """Convert node type to Neo4j label."""
        return NODE_TYPE_TO_LABEL.get(node_type.lower(), node_type.capitalize())

    def _get_rel_type(self, edge_type: str) -> str:
        """Convert edge type to Neo4j relationship type."""
        return EDGE_TYPE_TO_REL.get(edge_type.lower(), edge_type.upper())

    # Node operations

    def add_node(self, node: Node) -> str:
        """Add a node to the graph."""
        self._ensure_connected()

        label = self._get_label(node.type)

        # Prepare properties
        props = {
            "uuid": node.uuid,
            "type": node.type,
            "content": node.content,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
        }

        # Store embedding as JSON string (for later vector search)
        if node.embedding:
            props["embedding"] = json.dumps(node.embedding)

        # Flatten metadata into properties with prefix
        if node.metadata:
            for key, value in node.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    props[f"meta_{key}"] = value
                else:
                    props[f"meta_{key}"] = json.dumps(value)

        query = f"""
        MERGE (n:{label} {{uuid: $uuid}})
        SET n += $props
        RETURN n.uuid as uuid
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, uuid=node.uuid, props=props)
            record = result.single()

        logger.debug(f"Added node: {node.uuid} ({label})")
        return record["uuid"]

    def get_node(self, uuid: str) -> Optional[Node]:
        """Get a node by UUID."""
        self._ensure_connected()

        query = """
        MATCH (n {uuid: $uuid})
        RETURN n, labels(n) as labels
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, uuid=uuid)
            record = result.single()

        if not record:
            return None

        return self._record_to_node(record["n"], record["labels"])

    def update_node(self, uuid: str, updates: Dict[str, Any]) -> bool:
        """Update a node's properties."""
        self._ensure_connected()

        # Build SET clause
        set_parts = ["n.updated_at = datetime()"]
        params = {"uuid": uuid}

        if "content" in updates:
            set_parts.append("n.content = $content")
            params["content"] = updates["content"]

        if "embedding" in updates:
            if updates["embedding"]:
                set_parts.append("n.embedding = $embedding")
                params["embedding"] = json.dumps(updates["embedding"])
            else:
                set_parts.append("n.embedding = null")

        if "metadata" in updates:
            for key, value in updates["metadata"].items():
                param_name = f"meta_{key}"
                if isinstance(value, (str, int, float, bool)):
                    set_parts.append(f"n.meta_{key} = ${param_name}")
                    params[param_name] = value
                else:
                    set_parts.append(f"n.meta_{key} = ${param_name}")
                    params[param_name] = json.dumps(value)

        query = f"""
        MATCH (n {{uuid: $uuid}})
        SET {', '.join(set_parts)}
        RETURN count(n) as count
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **params)
            record = result.single()

        return record["count"] > 0

    def delete_node(self, uuid: str) -> bool:
        """Delete a node and its connected edges."""
        self._ensure_connected()

        query = """
        MATCH (n {uuid: $uuid})
        DETACH DELETE n
        RETURN count(n) as count
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, uuid=uuid)
            record = result.single()

        return record["count"] > 0

    def query_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Node]:
        """Query nodes with optional filters."""
        self._ensure_connected()

        where_parts = []
        params = {"limit": limit}

        if filters:
            if "type" in filters:
                label = self._get_label(filters["type"])
                # Use label matching
                where_parts.append(f"n:{label}")

            if "project_id" in filters:
                where_parts.append("n.meta_project_id = $project_id")
                params["project_id"] = filters["project_id"]

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        query = f"""
        MATCH (n)
        {where_clause}
        RETURN n, labels(n) as labels
        ORDER BY n.created_at DESC
        LIMIT $limit
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **params)
            records = list(result)

        return [self._record_to_node(r["n"], r["labels"]) for r in records]

    def query_nodes_by_time(
        self,
        start: datetime,
        end: datetime,
        node_type: Optional[str] = None,
    ) -> List[Node]:
        """Query nodes within a time range."""
        self._ensure_connected()

        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

        type_filter = ""
        if node_type:
            label = self._get_label(node_type)
            type_filter = f" AND n:{label}"

        query = f"""
        MATCH (n)
        WHERE (n.created_at >= $start AND n.created_at <= $end)
           OR (n.updated_at >= $start AND n.updated_at <= $end)
        {type_filter}
        RETURN n, labels(n) as labels
        ORDER BY n.created_at DESC
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **params)
            records = list(result)

        return [self._record_to_node(r["n"], r["labels"]) for r in records]

    # Edge operations

    def add_edge(self, edge: Edge) -> str:
        """Add an edge to the graph."""
        self._ensure_connected()

        rel_type = self._get_rel_type(edge.type)

        props = {
            "uuid": edge.uuid,
            "type": edge.type,
            "created_at": edge.created_at.isoformat(),
            "updated_at": edge.updated_at.isoformat(),
        }

        if edge.metadata:
            for key, value in edge.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    props[f"meta_{key}"] = value
                else:
                    props[f"meta_{key}"] = json.dumps(value)

        query = f"""
        MATCH (source {{uuid: $source_id}})
        MATCH (target {{uuid: $target_id}})
        MERGE (source)-[r:{rel_type} {{uuid: $uuid}}]->(target)
        SET r += $props
        RETURN r.uuid as uuid
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(
                query,
                source_id=edge.source_id,
                target_id=edge.target_id,
                uuid=edge.uuid,
                props=props,
            )
            record = result.single()

        if not record:
            raise ValueError(
                f"Could not create edge: source {edge.source_id} or "
                f"target {edge.target_id} not found"
            )

        logger.debug(f"Added edge: {edge.uuid} ({rel_type})")
        return record["uuid"]

    def get_edge(self, uuid: str) -> Optional[Edge]:
        """Get an edge by UUID."""
        self._ensure_connected()

        query = """
        MATCH (source)-[r {uuid: $uuid}]->(target)
        RETURN r, source.uuid as source_id, target.uuid as target_id, type(r) as rel_type
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, uuid=uuid)
            record = result.single()

        if not record:
            return None

        return self._record_to_edge(record)

    def delete_edge(self, uuid: str) -> bool:
        """Delete an edge."""
        self._ensure_connected()

        query = """
        MATCH ()-[r {uuid: $uuid}]->()
        DELETE r
        RETURN count(r) as count
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, uuid=uuid)
            record = result.single()

        return record["count"] > 0

    def query_edges(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Edge]:
        """Query edges with optional filters."""
        self._ensure_connected()

        where_parts = []
        params = {"limit": limit}

        if filters:
            if "type" in filters:
                rel_type = self._get_rel_type(filters["type"])
                # Dynamic relationship type matching requires different approach
                where_parts.append(f"type(r) = '{rel_type}'")

            if "source_id" in filters:
                where_parts.append("source.uuid = $source_id")
                params["source_id"] = filters["source_id"]

            if "target_id" in filters:
                where_parts.append("target.uuid = $target_id")
                params["target_id"] = filters["target_id"]

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        query = f"""
        MATCH (source)-[r]->(target)
        {where_clause}
        RETURN r, source.uuid as source_id, target.uuid as target_id, type(r) as rel_type
        ORDER BY r.created_at DESC
        LIMIT $limit
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, **params)
            records = list(result)

        return [self._record_to_edge(r) for r in records]

    # Search operations

    def search_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[Node, float]]:
        """
        Search for nodes similar to the given embedding.

        Note: This performs in-memory cosine similarity calculation.
        For large-scale vector search, consider using Neo4j Graph Data Science
        library or an external vector store.
        """
        self._ensure_connected()

        # Fetch nodes with embeddings
        query = """
        MATCH (n)
        WHERE n.embedding IS NOT NULL
        RETURN n, labels(n) as labels, n.embedding as embedding_json
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query)
            records = list(result)

        results = []
        for record in records:
            try:
                node_embedding = json.loads(record["embedding_json"])
                score = self._cosine_similarity(embedding, node_embedding)
                if score >= min_score:
                    node = self._record_to_node(record["n"], record["labels"])
                    results.append((node, score))
            except (json.JSONDecodeError, TypeError):
                continue

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    # Graph-specific operations (not in base interface)

    def traverse_from_node(
        self,
        start_uuid: str,
        edge_types: Optional[List[str]] = None,
        max_depth: int = 2,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Traverse the graph starting from a node.

        Returns nodes and their relationships within max_depth hops.

        Args:
            start_uuid: Starting node UUID
            edge_types: Optional list of edge types to follow
            max_depth: Maximum traversal depth
            limit: Maximum nodes to return

        Returns:
            List of dicts with 'node', 'depth', 'path' keys
        """
        self._ensure_connected()

        rel_filter = ""
        if edge_types:
            rel_types = [self._get_rel_type(t) for t in edge_types]
            rel_filter = ":" + "|".join(rel_types)

        query = f"""
        MATCH path = (start {{uuid: $start_uuid}})-[r{rel_filter}*1..{max_depth}]-(connected)
        WITH connected, length(path) as depth, path
        ORDER BY depth
        LIMIT $limit
        RETURN connected, labels(connected) as labels, depth,
               [rel in relationships(path) | type(rel)] as rel_types
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(query, start_uuid=start_uuid, limit=limit)
            records = list(result)

        return [
            {
                "node": self._record_to_node(r["connected"], r["labels"]),
                "depth": r["depth"],
                "path": r["rel_types"],
            }
            for r in records
        ]

    def find_path(
        self,
        source_uuid: str,
        target_uuid: str,
        max_depth: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two nodes.

        Args:
            source_uuid: Source node UUID
            target_uuid: Target node UUID
            max_depth: Maximum path length

        Returns:
            List of nodes in the path, or None if no path exists
        """
        self._ensure_connected()

        query = f"""
        MATCH path = shortestPath(
            (source {{uuid: $source_uuid}})-[*1..{max_depth}]-(target {{uuid: $target_uuid}})
        )
        RETURN nodes(path) as nodes,
               [n in nodes(path) | labels(n)] as all_labels,
               [r in relationships(path) | type(r)] as rels
        """

        with self._driver.session(database=self._database) as session:
            result = session.run(
                query,
                source_uuid=source_uuid,
                target_uuid=target_uuid,
            )
            record = result.single()

        if not record:
            return None

        path_nodes = []
        for i, node in enumerate(record["nodes"]):
            path_nodes.append({
                "node": self._record_to_node(node, record["all_labels"][i]),
                "relationship": record["rels"][i] if i < len(record["rels"]) else None,
            })

        return path_nodes

    # Helper methods

    def _record_to_node(self, neo4j_node, labels: List[str]) -> Node:
        """Convert Neo4j node to our Node model."""
        props = dict(neo4j_node)

        # Determine type from labels or stored type
        node_type = props.get("type", labels[0].lower() if labels else "unknown")

        # Parse embedding
        embedding = None
        if props.get("embedding"):
            try:
                embedding = json.loads(props["embedding"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Reconstruct metadata from meta_ prefixed properties
        metadata = {}
        for key, value in props.items():
            if key.startswith("meta_"):
                meta_key = key[5:]  # Remove "meta_" prefix
                # Try to parse JSON values
                if isinstance(value, str):
                    try:
                        metadata[meta_key] = json.loads(value)
                    except json.JSONDecodeError:
                        metadata[meta_key] = value
                else:
                    metadata[meta_key] = value

        # Parse timestamps
        created_at = props.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        updated_at = props.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.utcnow()

        return Node(
            type=node_type,
            content=props.get("content", ""),
            uuid=props.get("uuid", ""),
            created_at=created_at,
            updated_at=updated_at,
            embedding=embedding,
            metadata=metadata,
        )

    def _record_to_edge(self, record) -> Edge:
        """Convert Neo4j query result to our Edge model."""
        rel = record["r"]
        props = dict(rel)

        # Get edge type from stored type or relationship type
        edge_type = props.get("type", record.get("rel_type", "unknown").lower())

        # Reconstruct metadata
        metadata = {}
        for key, value in props.items():
            if key.startswith("meta_"):
                meta_key = key[5:]
                if isinstance(value, str):
                    try:
                        metadata[meta_key] = json.loads(value)
                    except json.JSONDecodeError:
                        metadata[meta_key] = value
                else:
                    metadata[meta_key] = value

        # Parse timestamps
        created_at = props.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        updated_at = props.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.utcnow()

        return Edge(
            type=edge_type,
            source_id=record["source_id"],
            target_id=record["target_id"],
            uuid=props.get("uuid", ""),
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
