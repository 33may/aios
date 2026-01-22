"""
Graphiti Knowledge Graph Integration

This module provides the core schema and client for the AIOS knowledge graph,
built on Graphiti + LadybugDB.
"""

from .client import GraphitiClient
from .config import GraphitiConfig
from .models import Edge, Node
from .queries import get_relevant_context, search_semantic, search_scoped
from .schema import (
    EdgeType,
    NodeType,
    METADATA_SOURCE_FILE,
    METADATA_CAPTURED_AT,
    METADATA_EPISODE_TYPE,
)

__all__ = [
    "NodeType",
    "EdgeType",
    "Node",
    "Edge",
    "GraphitiClient",
    "GraphitiConfig",
    "get_relevant_context",
    "search_semantic",
    "search_scoped",
    "METADATA_SOURCE_FILE",
    "METADATA_CAPTURED_AT",
    "METADATA_EPISODE_TYPE",
]
