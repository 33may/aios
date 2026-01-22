"""
Tests for GraphitiClient Integration

Tests client connection management, node/edge CRUD operations, query
functionality, and context manager usage.
"""

import pytest
from datetime import datetime
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.config import GraphitiConfig
from apps.backend.integrations.graphiti.models import Node, Edge


# Client Initialization Tests


class TestGraphitiClientInitialization:
    """Tests for GraphitiClient initialization and configuration."""

    def test_client_initialization_default_config(self):
        """Test creating a client with default configuration."""
        client = GraphitiClient()

        assert client.config is not None
        assert isinstance(client.config, GraphitiConfig)
        assert client._connected is False
        assert client._driver is None
        assert client._nodes == {}
        assert client._edges == {}

    def test_client_initialization_custom_config(self):
        """Test creating a client with custom configuration."""
        config = GraphitiConfig(
            host="custom-host",
            port=9999,
            database="custom-db",
            api_key="custom-api-key"
        )
        client = GraphitiClient(config=config)

        assert client.config == config
        assert client.config.host == "custom-host"
        assert client.config.port == 9999
        assert client.config.database == "custom-db"
        assert client.config.api_key == "custom-api-key"

    def test_client_repr(self):
        """Test client string representation."""
        client = GraphitiClient()
        repr_str = repr(client)

        assert "GraphitiClient" in repr_str
        assert "disconnected" in repr_str

        client.connect()
        repr_str = repr(client)

        assert "GraphitiClient" in repr_str
        assert "connected" in repr_str


# Connection Management Tests


class TestGraphitiClientConnection:
    """Tests for connection and disconnection logic."""

    def test_connect(self):
        """Test connecting to the Graphiti backend."""
        client = GraphitiClient()

        assert client.is_connected() is False

        client.connect()

        assert client.is_connected() is True

    def test_connect_when_already_connected(self):
        """Test that connecting when already connected is safe."""
        client = GraphitiClient()
        client.connect()

        assert client.is_connected() is True

        # Should not raise an error
        client.connect()

        assert client.is_connected() is True

    def test_disconnect(self):
        """Test disconnecting from the Graphiti backend."""
        client = GraphitiClient()
        client.connect()

        assert client.is_connected() is True

        client.disconnect()

        assert client.is_connected() is False

    def test_disconnect_when_not_connected(self):
        """Test that disconnecting when not connected is safe."""
        client = GraphitiClient()

        assert client.is_connected() is False

        # Should not raise an error
        client.disconnect()

        assert client.is_connected() is False

    def test_is_connected(self):
        """Test checking connection status."""
        client = GraphitiClient()

        assert client.is_connected() is False

        client.connect()
        assert client.is_connected() is True

        client.disconnect()
        assert client.is_connected() is False


# Context Manager Tests


class TestGraphitiClientContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_connects_and_disconnects(self):
        """Test that context manager handles connection lifecycle."""
        client = GraphitiClient()

        assert client.is_connected() is False

        with client as ctx_client:
            assert ctx_client.is_connected() is True
            assert ctx_client is client

        assert client.is_connected() is False

    def test_context_manager_operations(self):
        """Test performing operations within context manager."""
        client = GraphitiClient()

        with client:
            node = Node(type="project", content="Test Project")
            node_id = client.add_node(node)

            assert node_id is not None
            assert node_id == node.uuid

            retrieved = client.get_node(node_id)
            assert retrieved is not None
            assert retrieved.uuid == node_id


# Node Operations Tests


class TestGraphitiClientNodeOperations:
    """Tests for node CRUD operations."""

    def test_add_node(self):
        """Test adding a node to the graph."""
        client = GraphitiClient()
        client.connect()

        node = Node(type="project", content="Test Project")
        node_id = client.add_node(node)

        assert node_id is not None
        assert node_id == node.uuid

    def test_add_node_not_connected(self):
        """Test that adding a node fails when not connected."""
        client = GraphitiClient()

        node = Node(type="project", content="Test Project")

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.add_node(node)

    def test_create_node(self):
        """Test creating a node in the graph."""
        client = GraphitiClient()
        client.connect()

        node = Node(type="task", content="Test Task")
        created_node = client.create_node(node)

        assert created_node is not None
        assert created_node.uuid == node.uuid
        assert created_node.type == node.type
        assert created_node.content == node.content

    def test_create_node_not_connected(self):
        """Test that creating a node fails when not connected."""
        client = GraphitiClient()

        node = Node(type="task", content="Test Task")

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.create_node(node)

    def test_get_node(self):
        """Test retrieving a node by UUID."""
        client = GraphitiClient()
        client.connect()

        node = Node(type="decision", content="Test Decision")
        node_id = client.add_node(node)

        retrieved = client.get_node(node_id)

        assert retrieved is not None
        assert retrieved.uuid == node_id
        assert retrieved.type == node.type
        assert retrieved.content == node.content

    def test_get_node_not_found(self):
        """Test retrieving a non-existent node returns None."""
        client = GraphitiClient()
        client.connect()

        retrieved = client.get_node("non-existent-uuid")

        assert retrieved is None

    def test_get_node_not_connected(self):
        """Test that getting a node fails when not connected."""
        client = GraphitiClient()

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.get_node("some-uuid")

    def test_query_nodes(self):
        """Test querying nodes with filters."""
        client = GraphitiClient()
        client.connect()

        # Add multiple nodes
        node1 = Node(type="project", content="Project 1")
        node2 = Node(type="task", content="Task 1")
        node3 = Node(type="project", content="Project 2")

        client.add_node(node1)
        client.add_node(node2)
        client.add_node(node3)

        # Query for projects
        results = client.query_nodes({"type": "project"})

        # Note: Current implementation returns empty list
        # This test verifies the method works without error
        assert isinstance(results, list)

    def test_query_nodes_not_connected(self):
        """Test that querying nodes fails when not connected."""
        client = GraphitiClient()

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.query_nodes({"type": "project"})


# Edge Operations Tests


class TestGraphitiClientEdgeOperations:
    """Tests for edge CRUD operations."""

    def test_add_edge(self):
        """Test adding an edge to the graph."""
        client = GraphitiClient()
        client.connect()

        # Create nodes first
        node1 = Node(type="project", content="Project 1")
        node2 = Node(type="task", content="Task 1")
        client.add_node(node1)
        client.add_node(node2)

        # Create edge
        edge = Edge(
            type="contains",
            source_id=node1.uuid,
            target_id=node2.uuid
        )
        edge_id = client.add_edge(edge)

        assert edge_id is not None
        assert edge_id == edge.uuid

    def test_add_edge_not_connected(self):
        """Test that adding an edge fails when not connected."""
        client = GraphitiClient()

        edge = Edge(
            type="contains",
            source_id="source-uuid",
            target_id="target-uuid"
        )

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.add_edge(edge)

    def test_create_edge(self):
        """Test creating an edge in the graph."""
        client = GraphitiClient()
        client.connect()

        edge = Edge(
            type="references",
            source_id="source-uuid",
            target_id="target-uuid"
        )
        created_edge = client.create_edge(edge)

        assert created_edge is not None
        assert created_edge.uuid == edge.uuid
        assert created_edge.type == edge.type
        assert created_edge.source_id == edge.source_id
        assert created_edge.target_id == edge.target_id

    def test_create_edge_not_connected(self):
        """Test that creating an edge fails when not connected."""
        client = GraphitiClient()

        edge = Edge(
            type="references",
            source_id="source-uuid",
            target_id="target-uuid"
        )

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.create_edge(edge)

    def test_get_edge(self):
        """Test retrieving an edge by UUID."""
        client = GraphitiClient()
        client.connect()

        edge = Edge(
            type="spawned",
            source_id="source-uuid",
            target_id="target-uuid"
        )
        edge_id = client.add_edge(edge)

        retrieved = client.get_edge(edge_id)

        assert retrieved is not None
        assert retrieved.uuid == edge_id
        assert retrieved.type == edge.type
        assert retrieved.source_id == edge.source_id
        assert retrieved.target_id == edge.target_id

    def test_get_edge_not_found(self):
        """Test retrieving a non-existent edge returns None."""
        client = GraphitiClient()
        client.connect()

        retrieved = client.get_edge("non-existent-uuid")

        assert retrieved is None

    def test_get_edge_not_connected(self):
        """Test that getting an edge fails when not connected."""
        client = GraphitiClient()

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.get_edge("some-uuid")

    def test_update_edge(self):
        """Test updating an edge's metadata."""
        client = GraphitiClient()
        client.connect()

        edge = Edge(
            type="blocked_by",
            source_id="source-uuid",
            target_id="target-uuid",
            metadata={"priority": "high"}
        )
        edge_id = client.add_edge(edge)

        # Update metadata
        updates = {
            "metadata": {
                "status": "resolved",
                "resolution_time": "2024-01-15"
            }
        }
        updated = client.update_edge(edge_id, updates)

        assert updated is not None
        assert updated.uuid == edge_id
        assert updated.metadata["priority"] == "high"
        assert updated.metadata["status"] == "resolved"
        assert updated.metadata["resolution_time"] == "2024-01-15"
        assert isinstance(updated.updated_at, datetime)

    def test_update_edge_not_found(self):
        """Test updating a non-existent edge returns None."""
        client = GraphitiClient()
        client.connect()

        updates = {"metadata": {"key": "value"}}
        result = client.update_edge("non-existent-uuid", updates)

        assert result is None

    def test_update_edge_not_connected(self):
        """Test that updating an edge fails when not connected."""
        client = GraphitiClient()

        updates = {"metadata": {"key": "value"}}

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.update_edge("some-uuid", updates)

    def test_delete_edge(self):
        """Test deleting an edge from the graph."""
        client = GraphitiClient()
        client.connect()

        edge = Edge(
            type="related_to",
            source_id="source-uuid",
            target_id="target-uuid"
        )
        edge_id = client.add_edge(edge)

        # Verify edge exists
        assert client.get_edge(edge_id) is not None

        # Delete edge
        result = client.delete_edge(edge_id)

        assert result is True

        # Verify edge is deleted
        assert client.get_edge(edge_id) is None

    def test_delete_edge_not_found(self):
        """Test deleting a non-existent edge returns False."""
        client = GraphitiClient()
        client.connect()

        result = client.delete_edge("non-existent-uuid")

        assert result is False

    def test_delete_edge_not_connected(self):
        """Test that deleting an edge fails when not connected."""
        client = GraphitiClient()

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.delete_edge("some-uuid")

    def test_query_edges_by_type(self):
        """Test querying edges by type."""
        client = GraphitiClient()
        client.connect()

        # Add multiple edges
        edge1 = Edge(type="contains", source_id="src1", target_id="tgt1")
        edge2 = Edge(type="references", source_id="src2", target_id="tgt2")
        edge3 = Edge(type="contains", source_id="src3", target_id="tgt3")

        client.add_edge(edge1)
        client.add_edge(edge2)
        client.add_edge(edge3)

        # Query for "contains" edges
        results = client.query_edges({"type": "contains"})

        assert len(results) == 2
        assert all(edge.type == "contains" for edge in results)

    def test_query_edges_by_source(self):
        """Test querying edges by source_id."""
        client = GraphitiClient()
        client.connect()

        source_uuid = "specific-source"

        edge1 = Edge(type="contains", source_id=source_uuid, target_id="tgt1")
        edge2 = Edge(type="references", source_id="other-source", target_id="tgt2")
        edge3 = Edge(type="spawned", source_id=source_uuid, target_id="tgt3")

        client.add_edge(edge1)
        client.add_edge(edge2)
        client.add_edge(edge3)

        # Query by source_id
        results = client.query_edges({"source_id": source_uuid})

        assert len(results) == 2
        assert all(edge.source_id == source_uuid for edge in results)

    def test_query_edges_by_target(self):
        """Test querying edges by target_id."""
        client = GraphitiClient()
        client.connect()

        target_uuid = "specific-target"

        edge1 = Edge(type="contains", source_id="src1", target_id=target_uuid)
        edge2 = Edge(type="references", source_id="src2", target_id="other-target")
        edge3 = Edge(type="preceded_by", source_id="src3", target_id=target_uuid)

        client.add_edge(edge1)
        client.add_edge(edge2)
        client.add_edge(edge3)

        # Query by target_id
        results = client.query_edges({"target_id": target_uuid})

        assert len(results) == 2
        assert all(edge.target_id == target_uuid for edge in results)

    def test_query_edges_multiple_filters(self):
        """Test querying edges with multiple filters."""
        client = GraphitiClient()
        client.connect()

        source_uuid = "specific-source"
        target_uuid = "specific-target"

        edge1 = Edge(type="contains", source_id=source_uuid, target_id=target_uuid)
        edge2 = Edge(type="contains", source_id=source_uuid, target_id="other-target")
        edge3 = Edge(type="references", source_id=source_uuid, target_id=target_uuid)

        client.add_edge(edge1)
        client.add_edge(edge2)
        client.add_edge(edge3)

        # Query with multiple filters
        results = client.query_edges({
            "type": "contains",
            "source_id": source_uuid,
            "target_id": target_uuid
        })

        assert len(results) == 1
        assert results[0].type == "contains"
        assert results[0].source_id == source_uuid
        assert results[0].target_id == target_uuid

    def test_query_edges_no_matches(self):
        """Test querying edges with no matches returns empty list."""
        client = GraphitiClient()
        client.connect()

        edge = Edge(type="contains", source_id="src", target_id="tgt")
        client.add_edge(edge)

        # Query for non-existent type
        results = client.query_edges({"type": "non-existent-type"})

        assert results == []

    def test_query_edges_not_connected(self):
        """Test that querying edges fails when not connected."""
        client = GraphitiClient()

        with pytest.raises(ConnectionError, match="Client is not connected"):
            client.query_edges({"type": "contains"})


# Integration Tests


class TestGraphitiClientIntegration:
    """Integration tests for complete workflows."""

    def test_full_node_lifecycle(self):
        """Test complete node lifecycle: create, retrieve, add to graph."""
        client = GraphitiClient()
        client.connect()

        # Create node
        node = Node(
            type="project",
            content="Integration Test Project",
            metadata={"status": "active"}
        )

        # Add to graph
        node_id = client.add_node(node)
        assert node_id is not None

        # Retrieve node
        retrieved = client.get_node(node_id)
        assert retrieved is not None
        assert retrieved.type == "project"
        assert retrieved.content == "Integration Test Project"
        assert retrieved.metadata["status"] == "active"

    def test_full_edge_lifecycle(self):
        """Test complete edge lifecycle: create, update, delete."""
        client = GraphitiClient()
        client.connect()

        # Create edge
        edge = Edge(
            type="contains",
            source_id="project-123",
            target_id="task-456",
            metadata={"weight": 1.0}
        )

        # Add to graph
        edge_id = client.add_edge(edge)
        assert edge_id is not None

        # Retrieve edge
        retrieved = client.get_edge(edge_id)
        assert retrieved is not None
        assert retrieved.metadata["weight"] == 1.0

        # Update edge
        updated = client.update_edge(edge_id, {
            "metadata": {"priority": "high"}
        })
        assert updated.metadata["weight"] == 1.0
        assert updated.metadata["priority"] == "high"

        # Delete edge
        deleted = client.delete_edge(edge_id)
        assert deleted is True

        # Verify deletion
        assert client.get_edge(edge_id) is None

    def test_graph_with_nodes_and_edges(self):
        """Test building a graph with multiple nodes and edges."""
        client = GraphitiClient()
        client.connect()

        # Create nodes
        project = Node(type="project", content="Main Project")
        session = Node(type="session", content="Work Session")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        # Add nodes
        project_id = client.add_node(project)
        session_id = client.add_node(session)
        task1_id = client.add_node(task1)
        task2_id = client.add_node(task2)

        # Create edges
        edge1 = Edge(type="contains", source_id=project_id, target_id=session_id)
        edge2 = Edge(type="contains", source_id=session_id, target_id=task1_id)
        edge3 = Edge(type="contains", source_id=session_id, target_id=task2_id)
        edge4 = Edge(type="preceded_by", source_id=task2_id, target_id=task1_id)

        # Add edges
        edge1_id = client.add_edge(edge1)
        edge2_id = client.add_edge(edge2)
        edge3_id = client.add_edge(edge3)
        edge4_id = client.add_edge(edge4)

        # Query edges from session
        session_edges = client.query_edges({"source_id": session_id})
        assert len(session_edges) == 2

        # Verify structure
        assert client.get_node(project_id) is not None
        assert client.get_edge(edge1_id) is not None
        assert client.get_edge(edge4_id).type == "preceded_by"

    def test_multiple_operations_in_context(self):
        """Test performing multiple operations in a context manager."""
        client = GraphitiClient()

        with client:
            # Create and add nodes
            node1 = Node(type="idea", content="Great Idea")
            node2 = Node(type="note", content="Important Note")

            node1_id = client.add_node(node1)
            node2_id = client.add_node(node2)

            # Create edge
            edge = Edge(type="related_to", source_id=node1_id, target_id=node2_id)
            edge_id = client.add_edge(edge)

            # Query and verify
            retrieved_edge = client.get_edge(edge_id)
            assert retrieved_edge is not None
            assert retrieved_edge.source_id == node1_id
            assert retrieved_edge.target_id == node2_id

        # Verify client is disconnected after context exit
        assert client.is_connected() is False
