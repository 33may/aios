"""
Knowledge Graph Storage Backends

Provides pluggable storage backends for the knowledge graph:
- MemoryBackend: In-memory storage (for testing)
- PostgresBackend: PostgreSQL + pgvector (for production)
- Neo4jBackend: Neo4j graph database (for graph-native storage)
"""

from .base import StorageBackend
from .memory import MemoryBackend
from .postgres import PostgresBackend
from .neo4j import Neo4jBackend

__all__ = ["StorageBackend", "MemoryBackend", "PostgresBackend", "Neo4jBackend"]
