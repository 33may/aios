"""
Tests for Query Engine Module

Tests QueryEngine class methods including connection management,
semantic search, project-scoped search, related node retrieval,
and graph traversal functionality.
"""

import pytest
from apps.cli.query_engine import QueryEngine
from apps.cli.config import CLIConfig
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge


# QueryEngine Initialization Tests


class TestQueryEngineInit:
    """Tests for QueryEngine initialization."""

    def test_init_default_config(self):
        """Test that QueryEngine can be initialized with default config."""
        engine = QueryEngine()

        assert engine.config is not None
        assert isinstance(engine.config, CLIConfig)
        assert engine._connected is False
        assert engine._client is None

    def test_init_custom_config(self):
        """Test that QueryEngine accepts custom configuration."""
        config = CLIConfig(default_limit=5, max_limit=50)
        engine = QueryEngine(config=config)

        assert engine.config.default_limit == 5
        assert engine.config.max_limit == 50

    def test_init_not_connected(self):
        """Test that engine is not connected on initialization."""
        engine = QueryEngine()

        assert engine.is_connected() is False


# Connection Management Tests


class TestQueryEngineConnection:
    """Tests for QueryEngine connection management."""

    def test_connect_establishes_connection(self):
        """Test that connect() establishes a connection."""
        engine = QueryEngine()
        engine.connect()

        assert engine.is_connected() is True
        assert engine._client is not None
        assert isinstance(engine._client, GraphitiClient)

        engine.disconnect()

    def test_connect_idempotent(self):
        """Test that calling connect() multiple times is safe."""
        engine = QueryEngine()
        engine.connect()
        engine.connect()  # Should not raise

        assert engine.is_connected() is True

        engine.disconnect()

    def test_disconnect_closes_connection(self):
        """Test that disconnect() closes the connection."""
        engine = QueryEngine()
        engine.connect()
        engine.disconnect()

        assert engine.is_connected() is False
        assert engine._client is None

    def test_disconnect_idempotent(self):
        """Test that calling disconnect() multiple times is safe."""
        engine = QueryEngine()
        engine.connect()
        engine.disconnect()
        engine.disconnect()  # Should not raise

        assert engine.is_connected() is False

    def test_disconnect_when_not_connected(self):
        """Test that disconnect() is safe when not connected."""
        engine = QueryEngine()
        engine.disconnect()  # Should not raise

        assert engine.is_connected() is False

    def test_is_connected_reflects_state(self):
        """Test that is_connected() accurately reflects connection state."""
        engine = QueryEngine()

        assert engine.is_connected() is False

        engine.connect()
        assert engine.is_connected() is True

        engine.disconnect()
        assert engine.is_connected() is False


# Context Manager Tests


class TestQueryEngineContextManager:
    """Tests for QueryEngine context manager support."""

    def test_context_manager_connects(self):
        """Test that context manager connects on entry."""
        with QueryEngine() as engine:
            assert engine.is_connected() is True

    def test_context_manager_disconnects(self):
        """Test that context manager disconnects on exit."""
        engine = QueryEngine()

        with engine:
            assert engine.is_connected() is True

        assert engine.is_connected() is False

    def test_context_manager_returns_engine(self):
        """Test that context manager returns the engine instance."""
        with QueryEngine() as engine:
            assert isinstance(engine, QueryEngine)

    def test_context_manager_exception_handling(self):
        """Test that context manager disconnects even on exception."""
        engine = QueryEngine()

        try:
            with engine:
                assert engine.is_connected() is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert engine.is_connected() is False


# Search Tests


class TestQueryEngineSearch:
    """Tests for QueryEngine search functionality."""

    def test_search_returns_list(self):
        """Test that search() returns a list."""
        engine = QueryEngine()
        engine.connect()

        # Add test data
        node = Node(
            type="task",
            content="Test task content",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        engine._client.add_node(node)

        results = engine.search("test")

        assert isinstance(results, list)

        engine.disconnect()

    def test_search_returns_node_score_tuples(self):
        """Test that search() returns tuples of (Node, float)."""
        engine = QueryEngine()
        engine.connect()

        node = Node(
            type="task",
            content="Test task content",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        engine._client.add_node(node)

        results = engine.search("test")

        if len(results) > 0:
            assert all(isinstance(item, tuple) for item in results)
            assert all(len(item) == 2 for item in results)
            assert all(isinstance(item[0], Node) for item in results)
            assert all(isinstance(item[1], float) for item in results)

        engine.disconnect()

    def test_search_respects_limit(self):
        """Test that search() respects the limit parameter."""
        engine = QueryEngine()
        engine.connect()

        # Add multiple nodes
        for i in range(10):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i % 3), float(i % 2), 0.5, 0.3, 0.1]
            )
            engine._client.add_node(node)

        results = engine.search("task", limit=3)

        assert len(results) <= 3

        engine.disconnect()

    def test_search_uses_default_limit(self):
        """Test that search() uses config default_limit when not specified."""
        config = CLIConfig(default_limit=2, max_limit=100)
        engine = QueryEngine(config=config)
        engine.connect()

        # Add multiple nodes
        for i in range(10):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i % 3), float(i % 2), 0.5, 0.3, 0.1]
            )
            engine._client.add_node(node)

        results = engine.search("task")

        assert len(results) <= 2

        engine.disconnect()

    def test_search_limit_capped_by_max_limit(self):
        """Test that search limit is capped by config max_limit."""
        config = CLIConfig(default_limit=3, max_limit=3)
        engine = QueryEngine(config=config)
        engine.connect()

        # Add multiple nodes
        for i in range(10):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i % 3), float(i % 2), 0.5, 0.3, 0.1]
            )
            engine._client.add_node(node)

        # Request more than max_limit - should be capped
        results = engine.search("task", limit=10)

        assert len(results) <= 3

        engine.disconnect()

    def test_search_sorted_by_relevance(self):
        """Test that search results are sorted by relevance score."""
        engine = QueryEngine()
        engine.connect()

        # Add nodes with varying embeddings
        for i in range(5):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i) * 0.2, 0.5, 0.3, 0.1, 0.1]
            )
            engine._client.add_node(node)

        results = engine.search("query")

        # Verify results are sorted by score (descending)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

        engine.disconnect()


# Project-Scoped Search Tests


class TestQueryEngineSearchInProject:
    """Tests for QueryEngine project-scoped search functionality."""

    def test_search_in_project_returns_list(self):
        """Test that search_in_project() returns a list."""
        engine = QueryEngine()
        engine.connect()

        # Create project with child nodes
        project = Node(
            type="project",
            content="Test Project",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        project_id = engine._client.add_node(project)

        results = engine.search_in_project(project_id, "test")

        assert isinstance(results, list)

        engine.disconnect()

    def test_search_in_project_scoped_to_project(self):
        """Test that search_in_project() returns only nodes within scope."""
        engine = QueryEngine()
        engine.connect()

        # Create two projects
        project1 = Node(
            type="project",
            content="Project One",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        project2 = Node(
            type="project",
            content="Project Two",
            embedding=[0.7, 0.7, 0.1, 0.0, 0.0]
        )

        project1_id = engine._client.add_node(project1)
        project2_id = engine._client.add_node(project2)

        # Add tasks to project1
        task1 = Node(
            type="task",
            content="Task in project one",
            embedding=[0.9, 0.5, 0.0, 0.0, 0.0]
        )
        task1_id = engine._client.add_node(task1)
        engine._client.add_edge(Edge(
            type="contains",
            source_id=project1_id,
            target_id=task1_id
        ))

        # Add tasks to project2
        task2 = Node(
            type="task",
            content="Task in project two",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        task2_id = engine._client.add_node(task2)
        engine._client.add_edge(Edge(
            type="contains",
            source_id=project2_id,
            target_id=task2_id
        ))

        # Search within project1 scope
        results = engine.search_in_project(project1_id, "task")

        result_nodes = [node for node, _ in results]

        # Should find task1 or project1, not task2
        assert task2 not in result_nodes

        engine.disconnect()

    def test_search_in_project_respects_limit(self):
        """Test that search_in_project() respects the limit parameter."""
        engine = QueryEngine()
        engine.connect()

        # Create project
        project = Node(
            type="project",
            content="Test Project",
            embedding=[0.5, 0.5, 0.5, 0.0, 0.0]
        )
        project_id = engine._client.add_node(project)

        # Add multiple tasks
        for i in range(10):
            task = Node(
                type="task",
                content=f"Task {i}",
                embedding=[0.1 * i, 0.2, 0.3, 0.4, 0.5]
            )
            task_id = engine._client.add_node(task)
            engine._client.add_edge(Edge(
                type="contains",
                source_id=project_id,
                target_id=task_id
            ))

        results = engine.search_in_project(project_id, "task", limit=3)

        assert len(results) <= 3

        engine.disconnect()


# Related Nodes Tests


class TestQueryEngineGetRelated:
    """Tests for QueryEngine get_related functionality."""

    def test_get_related_returns_list(self):
        """Test that get_related() returns a list."""
        engine = QueryEngine()
        engine.connect()

        node = Node(type="project", content="Test Project")
        node_id = engine._client.add_node(node)

        results = engine.get_related(node_id)

        assert isinstance(results, list)

        engine.disconnect()

    def test_get_related_returns_node_edge_tuples(self):
        """Test that get_related() returns tuples of (Node, Edge)."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        task = Node(type="task", content="Task")

        project_id = engine._client.add_node(project)
        task_id = engine._client.add_node(task)

        edge = Edge(type="contains", source_id=project_id, target_id=task_id)
        engine._client.add_edge(edge)

        results = engine.get_related(project_id, direction="outgoing")

        assert len(results) == 1
        result_node, result_edge = results[0]
        assert isinstance(result_node, Node)
        assert isinstance(result_edge, Edge)

        engine.disconnect()

    def test_get_related_outgoing_direction(self):
        """Test that get_related() with outgoing direction works."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        project_id = engine._client.add_node(project)
        task1_id = engine._client.add_node(task1)
        task2_id = engine._client.add_node(task2)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task1_id))
        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task2_id))

        results = engine.get_related(project_id, direction="outgoing")

        assert len(results) == 2
        result_nodes = [node for node, _ in results]
        assert task1 in result_nodes
        assert task2 in result_nodes

        engine.disconnect()

    def test_get_related_incoming_direction(self):
        """Test that get_related() with incoming direction works."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        task = Node(type="task", content="Task")

        project_id = engine._client.add_node(project)
        task_id = engine._client.add_node(task)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task_id))

        results = engine.get_related(task_id, direction="incoming")

        assert len(results) == 1
        result_node, result_edge = results[0]
        assert result_node == project

        engine.disconnect()

    def test_get_related_both_directions(self):
        """Test that get_related() with both direction works."""
        engine = QueryEngine()
        engine.connect()

        node1 = Node(type="task", content="Task 1")
        node2 = Node(type="task", content="Task 2")
        node3 = Node(type="project", content="Project")

        node1_id = engine._client.add_node(node1)
        node2_id = engine._client.add_node(node2)
        node3_id = engine._client.add_node(node3)

        # Outgoing from node1
        engine._client.add_edge(Edge(type="preceded_by", source_id=node1_id, target_id=node2_id))
        # Incoming to node1
        engine._client.add_edge(Edge(type="contains", source_id=node3_id, target_id=node1_id))

        results = engine.get_related(node1_id, direction="both")

        assert len(results) == 2
        result_nodes = [node for node, _ in results]
        assert node2 in result_nodes
        assert node3 in result_nodes

        engine.disconnect()

    def test_get_related_filter_by_edge_type(self):
        """Test that get_related() filters by edge type."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        project_id = engine._client.add_node(project)
        task1_id = engine._client.add_node(task1)
        task2_id = engine._client.add_node(task2)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task1_id))
        engine._client.add_edge(Edge(type="references", source_id=project_id, target_id=task2_id))

        results = engine.get_related(project_id, edge_type="contains", direction="outgoing")

        assert len(results) == 1
        result_node, result_edge = results[0]
        assert result_node == task1
        assert result_edge.type == "contains"

        engine.disconnect()

    def test_get_related_nonexistent_node(self):
        """Test that get_related() returns empty list for non-existent node."""
        engine = QueryEngine()
        engine.connect()

        results = engine.get_related("non-existent-uuid")

        assert results == []

        engine.disconnect()


# Traverse Tests


class TestQueryEngineTraverse:
    """Tests for QueryEngine traverse functionality."""

    def test_traverse_returns_dict(self):
        """Test that traverse() returns a dictionary."""
        engine = QueryEngine()
        engine.connect()

        node = Node(type="project", content="Test Project")
        node_id = engine._client.add_node(node)

        results = engine.traverse(node_id, depth=1)

        assert isinstance(results, dict)

        engine.disconnect()

    def test_traverse_depth_1(self):
        """Test traverse with depth 1 (direct neighbors)."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        project_id = engine._client.add_node(project)
        task1_id = engine._client.add_node(task1)
        task2_id = engine._client.add_node(task2)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task1_id))
        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task2_id))

        results = engine.traverse(project_id, depth=1)

        assert "0" in results
        assert "1" in results
        assert len(results["0"]) == 1
        assert results["0"][0].uuid == project_id
        assert len(results["1"]) == 2

        engine.disconnect()

    def test_traverse_depth_2(self):
        """Test traverse with depth 2 (multi-hop)."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        session = Node(type="session", content="Session")
        task = Node(type="task", content="Task")

        project_id = engine._client.add_node(project)
        session_id = engine._client.add_node(session)
        task_id = engine._client.add_node(task)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
        engine._client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))

        results = engine.traverse(project_id, depth=2)

        assert "0" in results
        assert "1" in results
        assert "2" in results

        engine.disconnect()

    def test_traverse_nonexistent_node(self):
        """Test that traverse() returns empty dict for non-existent node."""
        engine = QueryEngine()
        engine.connect()

        results = engine.traverse("non-existent-uuid", depth=1)

        assert results == {}

        engine.disconnect()

    def test_traverse_default_depth(self):
        """Test that traverse uses default depth of 1."""
        engine = QueryEngine()
        engine.connect()

        project = Node(type="project", content="Project")
        session = Node(type="session", content="Session")
        task = Node(type="task", content="Task")

        project_id = engine._client.add_node(project)
        session_id = engine._client.add_node(session)
        task_id = engine._client.add_node(task)

        engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
        engine._client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))

        results = engine.traverse(project_id)

        # With default depth=1, should only have levels 0 and 1
        assert "0" in results
        assert "1" in results
        # Task at depth 2 should not be directly in results
        # (may still appear if there's a direct edge, but shouldn't be in level 2)

        engine.disconnect()


# Repr Tests


class TestQueryEngineRepr:
    """Tests for QueryEngine string representation."""

    def test_repr_disconnected(self):
        """Test string representation when disconnected."""
        engine = QueryEngine()

        repr_str = repr(engine)

        assert "disconnected" in repr_str

    def test_repr_connected(self):
        """Test string representation when connected."""
        engine = QueryEngine()
        engine.connect()

        repr_str = repr(engine)

        assert "connected" in repr_str

        engine.disconnect()

    def test_repr_format(self):
        """Test that repr follows expected format."""
        engine = QueryEngine()

        repr_str = repr(engine)

        assert repr_str.startswith("QueryEngine(")
        assert repr_str.endswith(")")


# Integration Tests


class TestQueryEngineIntegration:
    """Integration tests for QueryEngine."""

    def test_full_workflow_with_context_manager(self):
        """Test complete workflow using context manager."""
        with QueryEngine() as engine:
            # Create project with tasks
            project = Node(
                type="project",
                content="Test Project",
                embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
            )
            project_id = engine._client.add_node(project)

            task1 = Node(
                type="task",
                content="Implement feature",
                embedding=[0.7, 0.7, 0.1, 0.0, 0.0]
            )
            task1_id = engine._client.add_node(task1)

            engine._client.add_edge(Edge(
                type="contains",
                source_id=project_id,
                target_id=task1_id
            ))

            # Test search
            search_results = engine.search("feature")
            assert isinstance(search_results, list)

            # Test scoped search
            scoped_results = engine.search_in_project(project_id, "feature")
            assert isinstance(scoped_results, list)

            # Test get_related
            related = engine.get_related(project_id, direction="outgoing")
            assert len(related) == 1

            # Test traverse
            traversal = engine.traverse(project_id, depth=1)
            assert "0" in traversal
            assert "1" in traversal

    def test_search_and_traverse_combination(self):
        """Test combining search and traverse operations."""
        with QueryEngine() as engine:
            # Create graph
            project = Node(
                type="project",
                content="Authentication System",
                embedding=[0.9, 0.5, 0.0, 0.0, 0.0]
            )
            task = Node(
                type="task",
                content="Implement login",
                embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
            )
            decision = Node(
                type="decision",
                content="Use JWT tokens",
                embedding=[0.85, 0.55, 0.0, 0.0, 0.0]
            )

            project_id = engine._client.add_node(project)
            task_id = engine._client.add_node(task)
            decision_id = engine._client.add_node(decision)

            engine._client.add_edge(Edge(type="contains", source_id=project_id, target_id=task_id))
            engine._client.add_edge(Edge(type="references", source_id=task_id, target_id=decision_id))

            # Search for authentication
            results = engine.search("authentication")
            assert len(results) > 0

            # Traverse from first result
            first_node = results[0][0]
            traversal = engine.traverse(first_node.uuid, depth=2)
            assert isinstance(traversal, dict)

    def test_reconnect_after_disconnect(self):
        """Test that engine can reconnect after disconnect."""
        engine = QueryEngine()

        # First connection
        engine.connect()
        assert engine.is_connected() is True

        engine.disconnect()
        assert engine.is_connected() is False

        # Reconnect
        engine.connect()
        assert engine.is_connected() is True

        # Verify operations work
        node = Node(type="task", content="Test", embedding=[0.5, 0.5, 0.5, 0.0, 0.0])
        engine._client.add_node(node)

        results = engine.search("test")
        assert isinstance(results, list)

        engine.disconnect()
