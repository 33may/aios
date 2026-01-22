"""
Graphiti Knowledge Graph Integration

This module provides the core schema and client for the AIOS knowledge graph,
built on Graphiti + LadybugDB.
"""

from .schema import NodeType, EdgeType

__all__ = ["NodeType", "EdgeType"]
