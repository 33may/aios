"""
Tests for Graphiti Query Utilities

Tests semantic search, hierarchical scoping, graph traversal, temporal queries,
and related node retrieval functionality.
"""

import pytest
from datetime import datetime, timedelta
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import (
    _compute_cosine_similarity,
    _generate_query_embedding,
    search_semantic,
    search_scoped,
    traverse,
    get_related,
    query_temporal,
    query_temporal_nodes,
)


# Helper Function Tests


class TestCosineSimilarity:
    """Tests for cosine similarity computation."""

    def test_identical_vectors(self):
        """Test that identical vectors have similarity of 1.0."""
        vec = [1.0, 2.0, 3.0, 4.0]
        similarity = _compute_cosine_similarity(vec, vec)

        assert similarity == pytest.approx(1.0, rel=1e-6)

    def test_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity of 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = _compute_cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0, rel=1e-6)

    def test_opposite_vectors(self):
        """Test that opposite vectors have similarity of -1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        similarity = _compute_cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0, rel=1e-6)

    def test_different_length_vectors(self):
        """Test that vectors of different lengths return 0.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        similarity = _compute_cosine_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_zero_magnitude_vectors(self):
        """Test that zero vectors return 0.0."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = _compute_cosine_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_partial_similarity(self):
        """Test vectors with partial similarity."""
        vec1 = [1.0, 1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = _compute_cosine_similarity(vec1, vec2)

        # Should be positive but less than 1.0
        assert 0.0 < similarity < 1.0


class TestQueryEmbedding:
    """Tests for query embedding generation."""

    def test_generate_embedding_structure(self):
        """Test that generated embedding has correct structure."""
        query = "test query"
        embedding = _generate_query_embedding(query)

        assert isinstance(embedding, list)
        assert len(embedding) == 5
        assert all(isinstance(val, float) for val in embedding)

    def test_generate_embedding_deterministic(self):
        """Test that same query generates same embedding."""
        query = "authentication implementation"
        embedding1 = _generate_query_embedding(query)
        embedding2 = _generate_query_embedding(query)

        assert embedding1 == embedding2

    def test_generate_embedding_normalized(self):
        """Test that generated embeddings are normalized."""
        query = "project management"
        embedding = _generate_query_embedding(query)

        # Calculate magnitude
        import math
        magnitude = math.sqrt(sum(x * x for x in embedding))

        assert magnitude == pytest.approx(1.0, rel=1e-6)

    def test_generate_embedding_different_queries(self):
        """Test that different queries generate different embeddings."""
        embedding1 = _generate_query_embedding("test")
        embedding2 = _generate_query_embedding("project")

        assert embedding1 != embedding2


# Semantic Search Tests


class TestSemanticSearch:
    """Tests for semantic search functionality."""

    def test_search_semantic_basic(self):
        """Test basic semantic search."""
        client = GraphitiClient()
        client.connect()

        # Add nodes with embeddings
        node1 = Node(
            type="task",
            content="Implement authentication",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        node2 = Node(
            type="task",
            content="Write tests",
            embedding=[0.0, 0.0, 0.8, 0.6, 0.0]
        )
        node3 = Node(
            type="project",
            content="Authentication project",
            embedding=[0.7, 0.7, 0.1, 0.0, 0.0]
        )

        client.add_node(node1)
        client.add_node(node2)
        client.add_node(node3)

        # Search for authentication-related content
        results = search_semantic("authentication", limit=10, client=client)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(item, tuple) for item in results)
        assert all(len(item) == 2 for item in results)
        assert all(isinstance(item[0], Node) for item in results)
        assert all(isinstance(item[1], float) for item in results)

    def test_search_semantic_limit(self):
        """Test that search respects limit parameter."""
        client = GraphitiClient()
        client.connect()

        # Add multiple nodes with embeddings
        for i in range(10):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i % 3), float(i % 2), 0.5, 0.3, 0.1]
            )
            client.add_node(node)

        # Search with limit
        results = search_semantic("task", limit=3, client=client)

        assert len(results) <= 3

    def test_search_semantic_sorted_by_relevance(self):
        """Test that results are sorted by relevance score."""
        client = GraphitiClient()
        client.connect()

        # Add nodes with embeddings
        for i in range(5):
            node = Node(
                type="task",
                content=f"Task {i}",
                embedding=[float(i) * 0.2, 0.5, 0.3, 0.1, 0.1]
            )
            client.add_node(node)

        results = search_semantic("query", limit=5, client=client)

        # Verify results are sorted by score (descending)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_semantic_excludes_nodes_without_embeddings(self):
        """Test that nodes without embeddings are excluded."""
        client = GraphitiClient()
        client.connect()

        # Add nodes with and without embeddings
        node1 = Node(type="task", content="Task 1", embedding=[0.8, 0.6, 0.0, 0.0, 0.0])
        node2 = Node(type="task", content="Task 2", embedding=None)
        node3 = Node(type="task", content="Task 3", embedding=[0.7, 0.7, 0.1, 0.0, 0.0])

        client.add_node(node1)
        client.add_node(node2)
        client.add_node(node3)

        results = search_semantic("task", client=client)

        # Only nodes with embeddings should be returned
        result_nodes = [node for node, _ in results]
        assert node1 in result_nodes
        assert node2 not in result_nodes
        assert node3 in result_nodes

    def test_search_semantic_without_client(self):
        """Test semantic search creates its own client if not provided."""
        # This should not raise an error
        results = search_semantic("test query", limit=5)

        assert isinstance(results, list)


# Scoped Search Tests


class TestScopedSearch:
    """Tests for hierarchical scoped search."""

    def test_search_scoped_basic(self):
        """Test basic scoped search within a hierarchy."""
        client = GraphitiClient()
        client.connect()

        # Create hierarchy: project -> session -> tasks
        project = Node(type="project", content="Main Project", embedding=[0.8, 0.6, 0.0, 0.0, 0.0])
        session = Node(type="session", content="Work Session", embedding=[0.7, 0.7, 0.1, 0.0, 0.0])
        task1 = Node(type="task", content="Authentication task", embedding=[0.9, 0.5, 0.0, 0.0, 0.0])
        task2 = Node(type="task", content="Testing task", embedding=[0.0, 0.0, 0.8, 0.6, 0.0])
        other_task = Node(type="task", content="Other task", embedding=[0.5, 0.5, 0.5, 0.0, 0.0])

        project_id = client.add_node(project)
        session_id = client.add_node(session)
        task1_id = client.add_node(task1)
        task2_id = client.add_node(task2)
        other_task_id = client.add_node(other_task)

        # Create hierarchy edges
        client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
        client.add_edge(Edge(type="contains", source_id=session_id, target_id=task1_id))
        client.add_edge(Edge(type="contains", source_id=session_id, target_id=task2_id))

        # Search within session scope
        results = search_scoped(session_id, "authentication", limit=10, client=client)

        # Should only return nodes within the session scope
        result_nodes = [node for node, _ in results]
        assert task1 in result_nodes or session in result_nodes
        assert other_task not in result_nodes

    def test_search_scoped_includes_scope_node(self):
        """Test that scope node itself is included in search."""
        client = GraphitiClient()
        client.connect()

        project = Node(type="project", content="Test Project", embedding=[0.8, 0.6, 0.0, 0.0, 0.0])
        project_id = client.add_node(project)

        results = search_scoped(project_id, "test", limit=10, client=client)

        result_nodes = [node for node, _ in results]
        assert project in result_nodes

    def test_search_scoped_limit(self):
        """Test that scoped search respects limit parameter."""
        client = GraphitiClient()
        client.connect()

        # Create scope with multiple children
        scope = Node(type="project", content="Scope", embedding=[0.5, 0.5, 0.5, 0.0, 0.0])
        scope_id = client.add_node(scope)

        for i in range(10):
            child = Node(type="task", content=f"Task {i}", embedding=[0.1 * i, 0.2, 0.3, 0.4, 0.5])
            child_id = client.add_node(child)
            client.add_edge(Edge(type="contains", source_id=scope_id, target_id=child_id))

        results = search_scoped(scope_id, "task", limit=3, client=client)

        assert len(results) <= 3

    def test_search_scoped_without_client(self):
        """Test scoped search creates its own client if not provided."""
        # Create a temporary client to set up data
        setup_client = GraphitiClient()
        setup_client.connect()
        node = Node(type="project", content="Test", embedding=[0.5, 0.5, 0.5, 0.0, 0.0])
        node_id = setup_client.add_node(node)
        setup_client.disconnect()

        # Search should work without passing client
        results = search_scoped(node_id, "test", limit=5)

        assert isinstance(results, list)


# Graph Traversal Tests


class TestTraverse:
    """Tests for graph traversal functionality."""

    def test_traverse_depth_1(self):
        """Test traversal with depth 1 (direct neighbors)."""
        client = GraphitiClient()
        client.connect()

        # Create a simple graph
        node1 = Node(type="project", content="Project 1")
        node2 = Node(type="task", content="Task 1")
        node3 = Node(type="task", content="Task 2")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)
        node3_id = client.add_node(node3)

        # Create edges
        client.add_edge(Edge(type="contains", source_id=node1_id, target_id=node2_id))
        client.add_edge(Edge(type="contains", source_id=node1_id, target_id=node3_id))

        # Traverse from node1
        results = traverse(node1_id, depth=1, client=client)

        assert "0" in results
        assert "1" in results
        assert len(results["0"]) == 1
        assert results["0"][0].uuid == node1_id
        assert len(results["1"]) == 2

    def test_traverse_depth_2(self):
        """Test traversal with depth 2 (multi-hop)."""
        client = GraphitiClient()
        client.connect()

        # Create a chain: node1 -> node2 -> node3
        node1 = Node(type="project", content="Project")
        node2 = Node(type="session", content="Session")
        node3 = Node(type="task", content="Task")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)
        node3_id = client.add_node(node3)

        client.add_edge(Edge(type="contains", source_id=node1_id, target_id=node2_id))
        client.add_edge(Edge(type="contains", source_id=node2_id, target_id=node3_id))

        # Traverse from node1 with depth 2
        results = traverse(node1_id, depth=2, client=client)

        assert "0" in results
        assert "1" in results
        assert "2" in results
        assert len(results["0"]) == 1
        assert len(results["1"]) >= 1
        assert len(results["2"]) >= 1

    def test_traverse_nonexistent_node(self):
        """Test traversal from non-existent node returns empty dict."""
        client = GraphitiClient()
        client.connect()

        results = traverse("non-existent-uuid", depth=1, client=client)

        assert results == {}

    def test_traverse_includes_bidirectional_edges(self):
        """Test that traversal follows both incoming and outgoing edges."""
        client = GraphitiClient()
        client.connect()

        node1 = Node(type="task", content="Task 1")
        node2 = Node(type="task", content="Task 2")
        node3 = Node(type="project", content="Project")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)
        node3_id = client.add_node(node3)

        # node1 -> node2 (outgoing from node1)
        client.add_edge(Edge(type="preceded_by", source_id=node1_id, target_id=node2_id))
        # node3 -> node1 (incoming to node1)
        client.add_edge(Edge(type="contains", source_id=node3_id, target_id=node1_id))

        results = traverse(node1_id, depth=1, client=client)

        # Should find both node2 and node3
        depth_1_nodes = results["1"]
        depth_1_ids = [node.uuid for node in depth_1_nodes]

        assert node2_id in depth_1_ids
        assert node3_id in depth_1_ids

    def test_traverse_without_client(self):
        """Test traverse creates its own client if not provided."""
        # Create a temporary client to set up data
        setup_client = GraphitiClient()
        setup_client.connect()
        node = Node(type="project", content="Test")
        node_id = setup_client.add_node(node)
        setup_client.disconnect()

        # Traverse should work without passing client
        results = traverse(node_id, depth=1)

        assert isinstance(results, dict)


# Related Nodes Tests


class TestGetRelated:
    """Tests for getting related nodes."""

    def test_get_related_outgoing(self):
        """Test getting nodes via outgoing edges."""
        client = GraphitiClient()
        client.connect()

        project = Node(type="project", content="Project")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        project_id = client.add_node(project)
        task1_id = client.add_node(task1)
        task2_id = client.add_node(task2)

        edge1 = Edge(type="contains", source_id=project_id, target_id=task1_id)
        edge2 = Edge(type="contains", source_id=project_id, target_id=task2_id)
        client.add_edge(edge1)
        client.add_edge(edge2)

        results = get_related(project_id, direction="outgoing", client=client)

        assert len(results) == 2
        result_nodes = [node for node, _ in results]
        assert task1 in result_nodes
        assert task2 in result_nodes

    def test_get_related_incoming(self):
        """Test getting nodes via incoming edges."""
        client = GraphitiClient()
        client.connect()

        project = Node(type="project", content="Project")
        task = Node(type="task", content="Task")
        decision = Node(type="decision", content="Decision")

        project_id = client.add_node(project)
        task_id = client.add_node(task)
        decision_id = client.add_node(decision)

        # Both reference the task
        client.add_edge(Edge(type="references", source_id=project_id, target_id=task_id))
        client.add_edge(Edge(type="references", source_id=decision_id, target_id=task_id))

        results = get_related(task_id, direction="incoming", client=client)

        assert len(results) == 2
        result_nodes = [node for node, _ in results]
        assert project in result_nodes
        assert decision in result_nodes

    def test_get_related_both_directions(self):
        """Test getting nodes via edges in both directions."""
        client = GraphitiClient()
        client.connect()

        node1 = Node(type="task", content="Task 1")
        node2 = Node(type="task", content="Task 2")
        node3 = Node(type="project", content="Project")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)
        node3_id = client.add_node(node3)

        # Outgoing from node1
        client.add_edge(Edge(type="preceded_by", source_id=node1_id, target_id=node2_id))
        # Incoming to node1
        client.add_edge(Edge(type="contains", source_id=node3_id, target_id=node1_id))

        results = get_related(node1_id, direction="both", client=client)

        assert len(results) == 2
        result_nodes = [node for node, _ in results]
        assert node2 in result_nodes
        assert node3 in result_nodes

    def test_get_related_filter_by_edge_type(self):
        """Test filtering related nodes by edge type."""
        client = GraphitiClient()
        client.connect()

        project = Node(type="project", content="Project")
        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")

        project_id = client.add_node(project)
        task1_id = client.add_node(task1)
        task2_id = client.add_node(task2)

        client.add_edge(Edge(type="contains", source_id=project_id, target_id=task1_id))
        client.add_edge(Edge(type="references", source_id=project_id, target_id=task2_id))

        # Get only "contains" relations
        results = get_related(project_id, edge_type="contains", direction="outgoing", client=client)

        assert len(results) == 1
        result_node, result_edge = results[0]
        assert result_node == task1
        assert result_edge.type == "contains"

    def test_get_related_nonexistent_node(self):
        """Test getting related nodes for non-existent node returns empty list."""
        client = GraphitiClient()
        client.connect()

        results = get_related("non-existent-uuid", client=client)

        assert results == []

    def test_get_related_returns_edges(self):
        """Test that get_related returns both nodes and edges."""
        client = GraphitiClient()
        client.connect()

        node1 = Node(type="project", content="Project")
        node2 = Node(type="task", content="Task")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)

        edge = Edge(type="contains", source_id=node1_id, target_id=node2_id)
        edge_id = client.add_edge(edge)

        results = get_related(node1_id, direction="outgoing", client=client)

        assert len(results) == 1
        result_node, result_edge = results[0]
        assert isinstance(result_node, Node)
        assert isinstance(result_edge, Edge)
        assert result_edge.uuid == edge_id

    def test_get_related_without_client(self):
        """Test get_related creates its own client if not provided."""
        # Create a temporary client to set up data
        setup_client = GraphitiClient()
        setup_client.connect()
        node = Node(type="project", content="Test")
        node_id = setup_client.add_node(node)
        setup_client.disconnect()

        # Should work without passing client
        results = get_related(node_id)

        assert isinstance(results, list)


# Temporal Query Tests


class TestQueryTemporal:
    """Tests for temporal range queries."""

    def test_query_temporal_nodes_only(self):
        """Test querying nodes within a time range."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)

        # Add nodes at different times
        node1 = Node(type="task", content="Old Task")
        node1.created_at = past - timedelta(hours=1)
        node1.updated_at = past - timedelta(hours=1)

        node2 = Node(type="task", content="Current Task")
        node2.created_at = now
        node2.updated_at = now

        node3 = Node(type="task", content="Future Task")
        node3.created_at = future + timedelta(hours=1)
        node3.updated_at = future + timedelta(hours=1)

        client.add_node(node1)
        client.add_node(node2)
        client.add_node(node3)

        # Query for nodes between past and future
        results = query_temporal(past, future, include_edges=False, client=client)

        assert "nodes" in results
        assert "edges" in results
        assert node2 in results["nodes"]
        assert len(results["edges"]) == 0

    def test_query_temporal_with_edges(self):
        """Test querying both nodes and edges within a time range."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        node1 = Node(type="task", content="Task 1")
        node2 = Node(type="task", content="Task 2")
        client.add_node(node1)
        client.add_node(node2)

        edge = Edge(type="preceded_by", source_id=node1.uuid, target_id=node2.uuid)
        client.add_edge(edge)

        # Query with edges
        results = query_temporal(start, end, include_edges=True, client=client)

        assert "nodes" in results
        assert "edges" in results
        assert len(results["nodes"]) >= 2
        assert len(results["edges"]) >= 1

    def test_query_temporal_sorted_by_created_at(self):
        """Test that results are sorted by created_at (newest first)."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=5)
        end = now + timedelta(hours=1)

        # Create nodes with different timestamps
        node1 = Node(type="task", content="Task 1")
        node1.created_at = now - timedelta(hours=4)

        node2 = Node(type="task", content="Task 2")
        node2.created_at = now - timedelta(hours=2)

        node3 = Node(type="task", content="Task 3")
        node3.created_at = now - timedelta(hours=1)

        client.add_node(node1)
        client.add_node(node2)
        client.add_node(node3)

        results = query_temporal(start, end, client=client)

        # Verify sorted by created_at (newest first)
        nodes = results["nodes"]
        for i in range(len(nodes) - 1):
            assert nodes[i].created_at >= nodes[i + 1].created_at

    def test_query_temporal_empty_range(self):
        """Test querying a time range with no matching nodes."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        past = now - timedelta(days=10)
        past_end = now - timedelta(days=9)

        # Add a current node
        node = Node(type="task", content="Current Task")
        client.add_node(node)

        # Query for old time range
        results = query_temporal(past, past_end, client=client)

        assert results["nodes"] == []
        assert results["edges"] == []

    def test_query_temporal_without_client(self):
        """Test query_temporal creates its own client if not provided."""
        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        results = query_temporal(start, end)

        assert isinstance(results, dict)
        assert "nodes" in results
        assert "edges" in results


class TestQueryTemporalNodes:
    """Tests for temporal node queries with type filtering."""

    def test_query_temporal_nodes_all_types(self):
        """Test querying all node types within a time range."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        task = Node(type="task", content="Task")
        project = Node(type="project", content="Project")
        decision = Node(type="decision", content="Decision")

        client.add_node(task)
        client.add_node(project)
        client.add_node(decision)

        results = query_temporal_nodes(start, end, client=client)

        assert len(results) >= 3
        assert task in results
        assert project in results
        assert decision in results

    def test_query_temporal_nodes_filter_by_type(self):
        """Test filtering temporal nodes by type."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        task1 = Node(type="task", content="Task 1")
        task2 = Node(type="task", content="Task 2")
        project = Node(type="project", content="Project")

        client.add_node(task1)
        client.add_node(task2)
        client.add_node(project)

        # Query only tasks
        results = query_temporal_nodes(start, end, node_type="task", client=client)

        assert len(results) == 2
        assert task1 in results
        assert task2 in results
        assert project not in results

    def test_query_temporal_nodes_sorted(self):
        """Test that temporal nodes are sorted by created_at."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=5)
        end = now + timedelta(hours=1)

        node1 = Node(type="task", content="Task 1")
        node1.created_at = now - timedelta(hours=3)

        node2 = Node(type="task", content="Task 2")
        node2.created_at = now - timedelta(hours=1)

        client.add_node(node1)
        client.add_node(node2)

        results = query_temporal_nodes(start, end, client=client)

        # Verify sorted (newest first)
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at

    def test_query_temporal_nodes_by_updated_at(self):
        """Test that nodes are included if updated_at is in range."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        # Node created in the past but updated recently
        node = Node(type="task", content="Task")
        node.created_at = now - timedelta(days=10)
        node.updated_at = now

        client.add_node(node)

        results = query_temporal_nodes(start, end, client=client)

        assert node in results

    def test_query_temporal_nodes_without_client(self):
        """Test query_temporal_nodes creates its own client if not provided."""
        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        results = query_temporal_nodes(start, end)

        assert isinstance(results, list)


# Integration Tests


class TestQueryIntegration:
    """Integration tests for query utilities."""

    def test_semantic_search_with_scoped_search(self):
        """Test combining semantic and scoped search."""
        client = GraphitiClient()
        client.connect()

        # Create hierarchy with embeddings
        project = Node(
            type="project",
            content="Authentication Project",
            embedding=[0.9, 0.5, 0.0, 0.0, 0.0]
        )
        task1 = Node(
            type="task",
            content="Implement login",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        task2 = Node(
            type="task",
            content="Write tests",
            embedding=[0.0, 0.0, 0.9, 0.5, 0.0]
        )

        project_id = client.add_node(project)
        task1_id = client.add_node(task1)
        task2_id = client.add_node(task2)

        client.add_edge(Edge(type="contains", source_id=project_id, target_id=task1_id))
        client.add_edge(Edge(type="contains", source_id=project_id, target_id=task2_id))

        # Global semantic search
        global_results = search_semantic("authentication", client=client)
        assert len(global_results) > 0

        # Scoped semantic search
        scoped_results = search_scoped(project_id, "authentication", client=client)
        assert len(scoped_results) > 0

    def test_traverse_and_get_related(self):
        """Test combining traverse and get_related."""
        client = GraphitiClient()
        client.connect()

        # Create a graph
        node1 = Node(type="project", content="Project")
        node2 = Node(type="session", content="Session")
        node3 = Node(type="task", content="Task")

        node1_id = client.add_node(node1)
        node2_id = client.add_node(node2)
        node3_id = client.add_node(node3)

        client.add_edge(Edge(type="contains", source_id=node1_id, target_id=node2_id))
        client.add_edge(Edge(type="contains", source_id=node2_id, target_id=node3_id))

        # Traverse from root
        traversal = traverse(node1_id, depth=2, client=client)
        assert len(traversal["1"]) >= 1

        # Get direct relations
        relations = get_related(node1_id, direction="outgoing", client=client)
        assert len(relations) >= 1

    def test_temporal_query_with_semantic_search(self):
        """Test combining temporal and semantic queries."""
        client = GraphitiClient()
        client.connect()

        now = datetime.utcnow()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        # Add recent nodes with embeddings
        node1 = Node(
            type="decision",
            content="Use authentication framework",
            embedding=[0.8, 0.6, 0.0, 0.0, 0.0]
        )
        node2 = Node(
            type="decision",
            content="Add testing suite",
            embedding=[0.0, 0.0, 0.8, 0.6, 0.0]
        )

        client.add_node(node1)
        client.add_node(node2)

        # Get recent decisions
        temporal_results = query_temporal_nodes(start, end, node_type="decision", client=client)
        assert len(temporal_results) >= 2

        # Search semantically
        semantic_results = search_semantic("authentication", client=client)
        result_nodes = [node for node, _ in semantic_results]

        # node1 should be in both results
        assert node1 in temporal_results
        assert node1 in result_nodes
