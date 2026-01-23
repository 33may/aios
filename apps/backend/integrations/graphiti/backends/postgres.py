"""
PostgreSQL + pgvector storage backend for production use.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging

from .base import StorageBackend
from ..models import Node, Edge

logger = logging.getLogger(__name__)

# Optional import - only required when using PostgresBackend
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    psycopg = None


class PostgresBackend(StorageBackend):
    """
    PostgreSQL + pgvector storage backend.

    Provides persistent storage with vector similarity search.
    Requires PostgreSQL with pgvector extension.

    Connection string format:
        postgresql://user:password@host:port/database
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "knowledge_graph",
        user: str = "knowledge",
        password: str = "",
        embedding_dim: int = 1536,
    ):
        """
        Initialize PostgreSQL backend.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            embedding_dim: Dimension of embedding vectors
        """
        if not PSYCOPG_AVAILABLE:
            raise ImportError(
                "psycopg is required for PostgresBackend. "
                "Install with: pip install 'psycopg[binary]'"
            )

        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._embedding_dim = embedding_dim
        self._conn: Optional[psycopg.Connection] = None

    @property
    def _conninfo(self) -> str:
        """Build connection string."""
        return f"postgresql://{self._user}:{self._password}@{self._host}:{self._port}/{self._database}"

    def connect(self) -> None:
        """Establish connection to PostgreSQL."""
        try:
            self._conn = psycopg.connect(
                self._conninfo,
                row_factory=dict_row,
                autocommit=True,
            )
            logger.info(f"Connected to PostgreSQL at {self._host}:{self._port}/{self._database}")

            # Verify pgvector extension
            with self._conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                if not cur.fetchone():
                    logger.warning("pgvector extension not found - vector search will not work")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to PostgreSQL."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Disconnected from PostgreSQL")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._conn is not None and not self._conn.closed

    def _ensure_connected(self) -> None:
        """Ensure we have an active connection."""
        if not self.is_connected():
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

    # Node operations

    def add_node(self, node: Node) -> str:
        """Add a node to the graph."""
        self._ensure_connected()

        # Convert embedding to pgvector format
        embedding_sql = None
        if node.embedding:
            embedding_sql = f"[{','.join(str(x) for x in node.embedding)}]"

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nodes (uuid, type, content, embedding, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s::vector, %s, %s, %s)
                ON CONFLICT (uuid) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING uuid
                """,
                (
                    node.uuid,
                    node.type,
                    node.content,
                    embedding_sql,
                    json.dumps(node.metadata) if node.metadata else "{}",
                    node.created_at,
                    node.updated_at,
                ),
            )
            result = cur.fetchone()

        logger.debug(f"Added node: {node.uuid} ({node.type})")
        return result["uuid"]

    def get_node(self, uuid: str) -> Optional[Node]:
        """Get a node by UUID."""
        self._ensure_connected()

        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT uuid, type, content, embedding::text, metadata, created_at, updated_at
                FROM nodes WHERE uuid = %s
                """,
                (uuid,),
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_node(row)

    def update_node(self, uuid: str, updates: Dict[str, Any]) -> bool:
        """Update a node's properties."""
        self._ensure_connected()

        # Build SET clause dynamically
        set_parts = []
        params = []

        if "content" in updates:
            set_parts.append("content = %s")
            params.append(updates["content"])

        if "embedding" in updates:
            embedding = updates["embedding"]
            if embedding:
                set_parts.append("embedding = %s::vector")
                params.append(f"[{','.join(str(x) for x in embedding)}]")
            else:
                set_parts.append("embedding = NULL")

        if "metadata" in updates:
            set_parts.append("metadata = %s")
            params.append(json.dumps(updates["metadata"]))

        if not set_parts:
            return False

        set_parts.append("updated_at = NOW()")
        params.append(uuid)

        with self._conn.cursor() as cur:
            cur.execute(
                f"UPDATE nodes SET {', '.join(set_parts)} WHERE uuid = %s",
                params,
            )
            return cur.rowcount > 0

    def delete_node(self, uuid: str) -> bool:
        """Delete a node and its connected edges."""
        self._ensure_connected()

        with self._conn.cursor() as cur:
            # Edges are deleted by CASCADE
            cur.execute("DELETE FROM nodes WHERE uuid = %s", (uuid,))
            return cur.rowcount > 0

    def query_nodes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Node]:
        """Query nodes with optional filters."""
        self._ensure_connected()

        where_parts = []
        params = []

        if filters:
            if "type" in filters:
                where_parts.append("type = %s")
                params.append(filters["type"])

            if "project_id" in filters:
                where_parts.append("metadata->>'project_id' = %s")
                params.append(filters["project_id"])

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        params.append(limit)

        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT uuid, type, content, embedding::text, metadata, created_at, updated_at
                FROM nodes {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()

        return [self._row_to_node(row) for row in rows]

    def query_nodes_by_time(
        self,
        start: datetime,
        end: datetime,
        node_type: Optional[str] = None,
    ) -> List[Node]:
        """Query nodes within a time range."""
        self._ensure_connected()

        params = [start, end, start, end]

        type_filter = ""
        if node_type:
            type_filter = "AND type = %s"
            params.append(node_type)

        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT uuid, type, content, embedding::text, metadata, created_at, updated_at
                FROM nodes
                WHERE (created_at BETWEEN %s AND %s OR updated_at BETWEEN %s AND %s)
                {type_filter}
                ORDER BY created_at DESC
                """,
                params,
            )
            rows = cur.fetchall()

        return [self._row_to_node(row) for row in rows]

    # Edge operations

    def add_edge(self, edge: Edge) -> str:
        """Add an edge to the graph."""
        self._ensure_connected()

        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO edges (uuid, type, source_id, target_id, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (uuid) DO UPDATE SET
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING uuid
                """,
                (
                    edge.uuid,
                    edge.type,
                    edge.source_id,
                    edge.target_id,
                    json.dumps(edge.metadata) if edge.metadata else "{}",
                    edge.created_at,
                    edge.updated_at,
                ),
            )
            result = cur.fetchone()

        logger.debug(f"Added edge: {edge.uuid} ({edge.type})")
        return result["uuid"]

    def get_edge(self, uuid: str) -> Optional[Edge]:
        """Get an edge by UUID."""
        self._ensure_connected()

        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM edges WHERE uuid = %s",
                (uuid,),
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_edge(row)

    def delete_edge(self, uuid: str) -> bool:
        """Delete an edge."""
        self._ensure_connected()

        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM edges WHERE uuid = %s", (uuid,))
            return cur.rowcount > 0

    def query_edges(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Edge]:
        """Query edges with optional filters."""
        self._ensure_connected()

        where_parts = []
        params = []

        if filters:
            if "type" in filters:
                where_parts.append("type = %s")
                params.append(filters["type"])
            if "source_id" in filters:
                where_parts.append("source_id = %s")
                params.append(filters["source_id"])
            if "target_id" in filters:
                where_parts.append("target_id = %s")
                params.append(filters["target_id"])

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        params.append(limit)

        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM edges {where_clause} ORDER BY created_at DESC LIMIT %s",
                params,
            )
            rows = cur.fetchall()

        return [self._row_to_edge(row) for row in rows]

    # Search operations

    def search_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[Node, float]]:
        """Search for nodes similar to the given embedding using pgvector."""
        self._ensure_connected()

        embedding_sql = f"[{','.join(str(x) for x in embedding)}]"

        # Use cosine distance (1 - cosine_similarity)
        # pgvector's <=> operator returns cosine distance
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    uuid, type, content, embedding::text, metadata, created_at, updated_at,
                    1 - (embedding <=> %s::vector) as similarity
                FROM nodes
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding_sql, embedding_sql, limit * 2),  # Fetch extra for filtering
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            score = row.get("similarity", 0)
            if score >= min_score:
                node = self._row_to_node(row)
                results.append((node, score))

        return results[:limit]

    # Helper methods

    def _row_to_node(self, row: Dict[str, Any]) -> Node:
        """Convert database row to Node object."""
        # Parse embedding from string if present
        embedding = None
        if row.get("embedding"):
            embedding_str = row["embedding"]
            # pgvector returns as "[0.1,0.2,...]"
            if embedding_str.startswith("[") and embedding_str.endswith("]"):
                embedding = [float(x) for x in embedding_str[1:-1].split(",")]

        # Parse metadata
        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Node(
            type=row["type"],
            content=row["content"],
            uuid=str(row["uuid"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            embedding=embedding,
            metadata=metadata,
        )

    def _row_to_edge(self, row: Dict[str, Any]) -> Edge:
        """Convert database row to Edge object."""
        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Edge(
            type=row["type"],
            source_id=str(row["source_id"]),
            target_id=str(row["target_id"]),
            uuid=str(row["uuid"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=metadata,
        )
