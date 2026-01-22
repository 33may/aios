"""
Tests for Knowledge Graph Schema and Models

Tests node types, edge types, node/edge model instantiation, and validation.
"""

import pytest
from datetime import datetime
from apps.backend.integrations.graphiti.schema import NodeType, EdgeType
from apps.backend.integrations.graphiti.models import Node, Edge


# Schema Tests - NodeType


class TestNodeType:
    """Tests for NodeType enum definitions."""

    def test_node_type_values(self):
        """Test that all expected node types are defined."""
        assert NodeType.PROJECT == "project"
        assert NodeType.SESSION == "session"
        assert NodeType.DECISION == "decision"
        assert NodeType.TASK == "task"
        assert NodeType.IDEA == "idea"
        assert NodeType.DISCOVERY == "discovery"
        assert NodeType.NOTE == "note"

    def test_node_type_count(self):
        """Test that we have the expected number of node types."""
        node_types = [t for t in NodeType]
        assert len(node_types) == 7

    def test_node_type_is_string_enum(self):
        """Test that NodeType is a string enum."""
        assert isinstance(NodeType.PROJECT, str)
        assert NodeType.PROJECT.value == "project"

    def test_node_type_iteration(self):
        """Test that we can iterate over node types."""
        types = [t.value for t in NodeType]
        expected = ["project", "session", "decision", "task", "idea", "discovery", "note"]
        assert sorted(types) == sorted(expected)


# Schema Tests - EdgeType


class TestEdgeType:
    """Tests for EdgeType enum definitions."""

    def test_edge_type_values(self):
        """Test that all expected edge types are defined."""
        assert EdgeType.CONTAINS == "contains"
        assert EdgeType.RELATED_TO == "related_to"
        assert EdgeType.REFERENCES == "references"
        assert EdgeType.SPAWNED == "spawned"
        assert EdgeType.DECIDED_IN == "decided_in"
        assert EdgeType.BLOCKED_BY == "blocked_by"
        assert EdgeType.PRECEDED_BY == "preceded_by"

    def test_edge_type_count(self):
        """Test that we have the expected number of edge types."""
        edge_types = [t for t in EdgeType]
        assert len(edge_types) == 7

    def test_edge_type_is_string_enum(self):
        """Test that EdgeType is a string enum."""
        assert isinstance(EdgeType.CONTAINS, str)
        assert EdgeType.CONTAINS.value == "contains"

    def test_edge_type_categories(self):
        """Test that edge types cover all required categories."""
        # Structural
        assert EdgeType.CONTAINS == "contains"

        # Associative
        assert EdgeType.RELATED_TO == "related_to"
        assert EdgeType.REFERENCES == "references"

        # Semantic
        assert EdgeType.SPAWNED == "spawned"
        assert EdgeType.DECIDED_IN == "decided_in"
        assert EdgeType.BLOCKED_BY == "blocked_by"

        # Temporal
        assert EdgeType.PRECEDED_BY == "preceded_by"


# Model Tests - Node


class TestNode:
    """Tests for Node data model."""

    def test_node_creation_minimal(self):
        """Test creating a node with minimal required fields."""
        node = Node(type="project", content="Test Project")

        assert node.type == "project"
        assert node.content == "Test Project"
        assert node.uuid is not None
        assert isinstance(node.uuid, str)
        assert node.created_at is not None
        assert isinstance(node.created_at, datetime)
        assert node.updated_at is not None
        assert isinstance(node.updated_at, datetime)
        assert node.embedding is None
        assert node.metadata == {}

    def test_node_creation_with_node_type_enum(self):
        """Test creating a node with NodeType enum."""
        node = Node(type=NodeType.PROJECT, content="Test Project")

        assert node.type == "project"
        assert node.content == "Test Project"

    def test_node_creation_with_all_fields(self):
        """Test creating a node with all fields specified."""
        test_uuid = "test-uuid-123"
        test_created_at = datetime(2024, 1, 1, 12, 0, 0)
        test_updated_at = datetime(2024, 1, 2, 12, 0, 0)
        test_embedding = [0.1, 0.2, 0.3]
        test_metadata = {"key": "value", "count": 42}

        node = Node(
            type="project",
            content="Test Project",
            uuid=test_uuid,
            created_at=test_created_at,
            updated_at=test_updated_at,
            embedding=test_embedding,
            metadata=test_metadata
        )

        assert node.type == "project"
        assert node.content == "Test Project"
        assert node.uuid == test_uuid
        assert node.created_at == test_created_at
        assert node.updated_at == test_updated_at
        assert node.embedding == test_embedding
        assert node.metadata == test_metadata

    def test_node_uuid_auto_generation(self):
        """Test that UUID is auto-generated if not provided."""
        node1 = Node(type="project", content="Project 1")
        node2 = Node(type="project", content="Project 2")

        assert node1.uuid != node2.uuid
        assert len(node1.uuid) > 0
        assert len(node2.uuid) > 0

    def test_node_timestamp_auto_generation(self):
        """Test that timestamps are auto-generated if not provided."""
        before = datetime.utcnow()
        node = Node(type="project", content="Test Project")
        after = datetime.utcnow()

        assert before <= node.created_at <= after
        assert before <= node.updated_at <= after

    def test_node_metadata_defaults_to_dict(self):
        """Test that metadata defaults to an empty dictionary."""
        node = Node(type="project", content="Test Project")

        assert node.metadata == {}
        assert isinstance(node.metadata, dict)

    def test_node_validation_empty_type(self):
        """Test that node validation fails for empty type."""
        with pytest.raises(ValueError, match="Node type cannot be empty"):
            Node(type="", content="Test Project")

    def test_node_validation_empty_content(self):
        """Test that node validation fails for empty content."""
        with pytest.raises(ValueError, match="Node content cannot be empty"):
            Node(type="project", content="")

    def test_node_validation_both_empty(self):
        """Test that node validation fails when both type and content are empty."""
        with pytest.raises(ValueError):
            Node(type="", content="")

    def test_node_with_embedding(self):
        """Test creating a node with embedding vector."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        node = Node(
            type="project",
            content="Test Project",
            embedding=embedding
        )

        assert node.embedding == embedding
        assert len(node.embedding) == 5

    def test_node_with_complex_metadata(self):
        """Test creating a node with complex metadata."""
        metadata = {
            "tags": ["important", "urgent"],
            "priority": 1,
            "assignee": "developer@example.com",
            "nested": {
                "key": "value"
            }
        }
        node = Node(
            type="task",
            content="Test Task",
            metadata=metadata
        )

        assert node.metadata == metadata
        assert node.metadata["tags"] == ["important", "urgent"]
        assert node.metadata["nested"]["key"] == "value"


# Model Tests - Edge


class TestEdge:
    """Tests for Edge data model."""

    def test_edge_creation_minimal(self):
        """Test creating an edge with minimal required fields."""
        edge = Edge(
            type="contains",
            source_id="source-uuid",
            target_id="target-uuid"
        )

        assert edge.type == "contains"
        assert edge.source_id == "source-uuid"
        assert edge.target_id == "target-uuid"
        assert edge.uuid is not None
        assert isinstance(edge.uuid, str)
        assert edge.created_at is not None
        assert isinstance(edge.created_at, datetime)
        assert edge.updated_at is not None
        assert isinstance(edge.updated_at, datetime)
        assert edge.metadata == {}

    def test_edge_creation_with_edge_type_enum(self):
        """Test creating an edge with EdgeType enum."""
        edge = Edge(
            type=EdgeType.CONTAINS,
            source_id="source-uuid",
            target_id="target-uuid"
        )

        assert edge.type == "contains"

    def test_edge_creation_with_all_fields(self):
        """Test creating an edge with all fields specified."""
        test_uuid = "edge-uuid-123"
        test_created_at = datetime(2024, 1, 1, 12, 0, 0)
        test_updated_at = datetime(2024, 1, 2, 12, 0, 0)
        test_metadata = {"weight": 0.9, "label": "strong"}

        edge = Edge(
            type="references",
            source_id="source-uuid",
            target_id="target-uuid",
            uuid=test_uuid,
            created_at=test_created_at,
            updated_at=test_updated_at,
            metadata=test_metadata
        )

        assert edge.type == "references"
        assert edge.source_id == "source-uuid"
        assert edge.target_id == "target-uuid"
        assert edge.uuid == test_uuid
        assert edge.created_at == test_created_at
        assert edge.updated_at == test_updated_at
        assert edge.metadata == test_metadata

    def test_edge_uuid_auto_generation(self):
        """Test that UUID is auto-generated if not provided."""
        edge1 = Edge(type="contains", source_id="src1", target_id="tgt1")
        edge2 = Edge(type="contains", source_id="src2", target_id="tgt2")

        assert edge1.uuid != edge2.uuid
        assert len(edge1.uuid) > 0
        assert len(edge2.uuid) > 0

    def test_edge_timestamp_auto_generation(self):
        """Test that timestamps are auto-generated if not provided."""
        before = datetime.utcnow()
        edge = Edge(type="contains", source_id="src", target_id="tgt")
        after = datetime.utcnow()

        assert before <= edge.created_at <= after
        assert before <= edge.updated_at <= after

    def test_edge_metadata_defaults_to_dict(self):
        """Test that metadata defaults to an empty dictionary."""
        edge = Edge(type="contains", source_id="src", target_id="tgt")

        assert edge.metadata == {}
        assert isinstance(edge.metadata, dict)

    def test_edge_validation_empty_type(self):
        """Test that edge validation fails for empty type."""
        with pytest.raises(ValueError, match="Edge type cannot be empty"):
            Edge(type="", source_id="src", target_id="tgt")

    def test_edge_validation_empty_source_id(self):
        """Test that edge validation fails for empty source_id."""
        with pytest.raises(ValueError, match="Edge source_id cannot be empty"):
            Edge(type="contains", source_id="", target_id="tgt")

    def test_edge_validation_empty_target_id(self):
        """Test that edge validation fails for empty target_id."""
        with pytest.raises(ValueError, match="Edge target_id cannot be empty"):
            Edge(type="contains", source_id="src", target_id="")

    def test_edge_validation_self_reference(self):
        """Test that edge validation fails for self-referencing edges."""
        with pytest.raises(ValueError, match="Edge cannot connect a node to itself"):
            Edge(type="contains", source_id="same-uuid", target_id="same-uuid")

    def test_edge_with_metadata(self):
        """Test creating an edge with metadata."""
        metadata = {
            "weight": 0.8,
            "confidence": 0.95,
            "tags": ["important"]
        }
        edge = Edge(
            type="references",
            source_id="src",
            target_id="tgt",
            metadata=metadata
        )

        assert edge.metadata == metadata
        assert edge.metadata["weight"] == 0.8
        assert edge.metadata["tags"] == ["important"]

    def test_edge_different_edge_types(self):
        """Test creating edges with different edge types."""
        edge_types = [
            EdgeType.CONTAINS,
            EdgeType.RELATED_TO,
            EdgeType.REFERENCES,
            EdgeType.SPAWNED,
            EdgeType.DECIDED_IN,
            EdgeType.BLOCKED_BY,
            EdgeType.PRECEDED_BY
        ]

        for edge_type in edge_types:
            edge = Edge(
                type=edge_type,
                source_id="src",
                target_id="tgt"
            )
            assert edge.type == edge_type.value


# Integration Tests


class TestNodeEdgeIntegration:
    """Tests for Node and Edge integration."""

    def test_create_nodes_and_edge(self):
        """Test creating nodes and an edge connecting them."""
        project = Node(type=NodeType.PROJECT, content="My Project")
        task = Node(type=NodeType.TASK, content="My Task")

        edge = Edge(
            type=EdgeType.CONTAINS,
            source_id=project.uuid,
            target_id=task.uuid
        )

        assert edge.source_id == project.uuid
        assert edge.target_id == task.uuid
        assert edge.type == "contains"

    def test_multiple_edges_between_nodes(self):
        """Test creating multiple edges between the same nodes."""
        node1 = Node(type=NodeType.TASK, content="Task 1")
        node2 = Node(type=NodeType.TASK, content="Task 2")

        edge1 = Edge(
            type=EdgeType.PRECEDED_BY,
            source_id=node2.uuid,
            target_id=node1.uuid
        )

        edge2 = Edge(
            type=EdgeType.RELATED_TO,
            source_id=node1.uuid,
            target_id=node2.uuid
        )

        assert edge1.source_id == node2.uuid
        assert edge1.target_id == node1.uuid
        assert edge2.source_id == node1.uuid
        assert edge2.target_id == node2.uuid
        assert edge1.uuid != edge2.uuid

    def test_hierarchical_structure(self):
        """Test creating a hierarchical structure with multiple levels."""
        project = Node(type=NodeType.PROJECT, content="Main Project")
        session = Node(type=NodeType.SESSION, content="Work Session")
        task = Node(type=NodeType.TASK, content="Implementation Task")

        project_to_session = Edge(
            type=EdgeType.CONTAINS,
            source_id=project.uuid,
            target_id=session.uuid
        )

        session_to_task = Edge(
            type=EdgeType.CONTAINS,
            source_id=session.uuid,
            target_id=task.uuid
        )

        assert project_to_session.source_id == project.uuid
        assert session_to_task.source_id == session.uuid
        assert session_to_task.target_id == task.uuid
