"""
Knowledge Graph Data Models

Defines the base data models for nodes and edges in the AIOS knowledge graph.
These models support temporal queries, semantic search via embeddings, and
flexible metadata storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Node:
    """
    Base node data model for the knowledge graph.

    Nodes represent entities in the graph such as projects, sessions,
    decisions, tasks, ideas, and discoveries. Each node has a type,
    content, and optional embedding for semantic search.

    Attributes:
        type: The node type (e.g., 'project', 'session', 'decision')
        content: The main content or description of the node
        uuid: Unique identifier for the node
        created_at: Timestamp when the node was created
        updated_at: Timestamp when the node was last updated
        embedding: Optional vector embedding for semantic search
        metadata: Optional additional properties and custom fields
    """

    type: str
    content: str
    uuid: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate node after initialization."""
        if not self.type:
            raise ValueError("Node type cannot be empty")
        if not self.content:
            raise ValueError("Node content cannot be empty")


@dataclass
class Edge:
    """
    Base edge data model for the knowledge graph.

    Edges represent relationships between nodes, such as containment,
    references, dependencies, and temporal sequences.

    Attributes:
        type: The edge type (e.g., 'contains', 'references', 'spawned')
        source_id: UUID of the source node
        target_id: UUID of the target node
        uuid: Unique identifier for the edge
        created_at: Timestamp when the edge was created
        updated_at: Timestamp when the edge was last updated
        metadata: Optional additional properties and custom fields
    """

    type: str
    source_id: str
    target_id: str
    uuid: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate edge after initialization."""
        if not self.type:
            raise ValueError("Edge type cannot be empty")
        if not self.source_id:
            raise ValueError("Edge source_id cannot be empty")
        if not self.target_id:
            raise ValueError("Edge target_id cannot be empty")
        if self.source_id == self.target_id:
            raise ValueError("Edge cannot connect a node to itself")
