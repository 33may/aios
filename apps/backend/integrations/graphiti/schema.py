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

    Categories:
    - Structural: project, session
    - Work items: task, idea
    - Knowledge capture: decision, discovery, note
    - Reasoning: thought, constraint, problem, fix, resource
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

    # Reasoning and knowledge-centric types
    THOUGHT = "thought"
    """A reasoning step, observation, or chain of thought during analysis"""

    CONSTRAINT = "constraint"
    """A user preference or requirement that shapes decisions"""

    PROBLEM = "problem"
    """An issue or bug encountered during work"""

    FIX = "fix"
    """A solution to a problem"""

    RESOURCE = "resource"
    """A file, URL, spec, or external reference"""


class EdgeType(str, Enum):
    """
    Edge types in the knowledge graph.

    Organized by category:
    - Structural: Hierarchical containment relationships
    - Associative: Cross-references and related content
    - Semantic: Domain-specific relationships
    - Temporal: Time-based sequencing
    - Causal: Reasoning chains and evidence relationships
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

    # Causal/reasoning edges
    LED_TO = "led_to"
    """Causal chain (e.g., thought led_to decision)"""

    SUPPORTS = "supports"
    """Evidence for (e.g., discovery supports decision)"""

    CONTRADICTS = "contradicts"
    """Evidence against (e.g., thought contradicts option)"""

    REFINED_BY = "refined_by"
    """Evolved thinking (e.g., thought refined_by thought)"""

    CONSTRAINED_BY = "constrained_by"
    """Limited by user preference (e.g., decision constrained_by constraint)"""

    FIXED_BY = "fixed_by"
    """Problem solved by (e.g., problem fixed_by fix)"""


# Context Metadata Field Constants
# These field names are used consistently across search results
# to provide context about where and when knowledge was captured.

METADATA_SOURCE_FILE = "source_file"
"""The file path where the knowledge was captured or originated from"""

METADATA_CAPTURED_AT = "captured_at"
"""The timestamp when the knowledge was captured (ISO 8601 format)"""

METADATA_EPISODE_TYPE = "episode_type"
"""The type of episode/event that captured this knowledge (e.g., 'session', 'task', 'discovery')"""