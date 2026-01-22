"""
Knowledge Graph Schema Definitions

Defines the core node types and edge types for the AIOS knowledge graph.
This schema enables automatic organization of development knowledge across
projects, sessions, decisions, tasks, ideas, and discoveries.
"""

from enum import Enum


class NodeType(str, Enum):
    """
    Node types in the knowledge graph.

    The schema supports flexible hierarchy where nodes CAN have parents
    but are not required to - avoiding forced hierarchies while enabling
    scoped queries.
    """

    PROJECT = "project"
    """Top-level container for a development project"""

    SESSION = "session"
    """A work session or coding session within a project"""

    DECISION = "decision"
    """An architectural or implementation decision with rationale"""

    TASK = "task"
    """A task or work item to be completed"""

    IDEA = "idea"
    """An idea or suggestion for future consideration"""

    DISCOVERY = "discovery"
    """A learning or insight discovered during development"""

    NOTE = "note"
    """A general note or piece of information"""


class EdgeType(str, Enum):
    """
    Edge types in the knowledge graph.

    Organized by category:
    - Structural: Hierarchical containment relationships
    - Associative: Cross-references and related content
    - Semantic: Domain-specific relationships
    - Temporal: Time-based sequencing
    """

    # Structural edges
    CONTAINS = "contains"
    """Hierarchical containment (e.g., Project contains Tasks)"""

    # Associative edges
    RELATED_TO = "related_to"
    """General association between nodes"""

    REFERENCES = "references"
    """One node references another (e.g., Decision references Task)"""

    # Semantic edges
    SPAWNED = "spawned"
    """One node spawned another (e.g., Idea spawned Task)"""

    DECIDED_IN = "decided_in"
    """Task or feature decided in a specific Decision"""

    BLOCKED_BY = "blocked_by"
    """Task is blocked by another Task or Decision"""

    # Temporal edges
    PRECEDED_BY = "preceded_by"
    """Sequential ordering (this node came after another)"""


# Context Metadata Field Constants
# These field names are used consistently across search results
# to provide context about where and when knowledge was captured.

METADATA_SOURCE_FILE = "source_file"
"""The file path where the knowledge was captured or originated from"""

METADATA_CAPTURED_AT = "captured_at"
"""The timestamp when the knowledge was captured (ISO 8601 format)"""

METADATA_EPISODE_TYPE = "episode_type"
"""The type of episode/event that captured this knowledge (e.g., 'session', 'task', 'discovery')"""