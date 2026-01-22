"""
Integration Tests for Complete Knowledge Graph Workflow

Tests end-to-end workflows combining client operations with query utilities
to validate the complete knowledge graph system.
"""

import pytest
from datetime import datetime, timedelta
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import (
    search_semantic,
    search_scoped,
    traverse,
    get_related,
    query_temporal,
    query_temporal_nodes,
)


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    def test_project_management_workflow(self):
        """
        Test a complete project management workflow:
        1. Create a project
        2. Create a session within the project
        3. Add tasks to the session
        4. Create decisions related to tasks
        5. Query by scope (find all items in project)
        6. Perform semantic search
        7. Query by temporal range
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create a project
            project = Node(
                type="project",
                content="AIOS Knowledge Graph Implementation",
                embedding=[0.8, 0.6, 0.2, 0.0, 0.0]
            )
            project_id = client.add_node(project)
            assert project_id is not None

            # Step 2: Create a session within the project
            session = Node(
                type="session",
                content="Sprint 1 Planning Session",
                embedding=[0.7, 0.7, 0.1, 0.0, 0.0]
            )
            session_id = client.add_node(session)

            # Link session to project
            project_session_edge = client.add_edge(Edge(
                type="contains",
                source_id=project_id,
                target_id=session_id
            ))
            assert project_session_edge is not None

            # Step 3: Add tasks to the session
            task1 = Node(
                type="task",
                content="Implement semantic search functionality",
                embedding=[0.9, 0.5, 0.0, 0.0, 0.0]
            )
            task1_id = client.add_node(task1)

            task2 = Node(
                type="task",
                content="Create integration tests for workflow",
                embedding=[0.0, 0.0, 0.8, 0.6, 0.0]
            )
            task2_id = client.add_node(task2)

            task3 = Node(
                type="task",
                content="Set up temporal query utilities",
                embedding=[0.6, 0.4, 0.5, 0.3, 0.0]
            )
            task3_id = client.add_node(task3)

            # Link tasks to session
            client.add_edge(Edge(type="contains", source_id=session_id, target_id=task1_id))
            client.add_edge(Edge(type="contains", source_id=session_id, target_id=task2_id))
            client.add_edge(Edge(type="contains", source_id=session_id, target_id=task3_id))

            # Step 4: Create decisions related to tasks
            decision1 = Node(
                type="decision",
                content="Use cosine similarity for semantic search",
                embedding=[0.85, 0.55, 0.1, 0.0, 0.0]
            )
            decision1_id = client.add_node(decision1)

            decision2 = Node(
                type="decision",
                content="Implement BFS-based graph traversal",
                embedding=[0.75, 0.45, 0.3, 0.2, 0.0]
            )
            decision2_id = client.add_node(decision2)

            # Link decisions to tasks
            client.add_edge(Edge(type="related_to", source_id=decision1_id, target_id=task1_id))
            client.add_edge(Edge(type="related_to", source_id=decision2_id, target_id=task3_id))

            # Also link decisions to session
            client.add_edge(Edge(type="decided_in", source_id=decision1_id, target_id=session_id))
            client.add_edge(Edge(type="decided_in", source_id=decision2_id, target_id=session_id))

            # Step 5: Query by scope (find all items in project)
            scoped_results = search_scoped(project_id, "semantic", limit=10, client=client)

            # Results should be from within the project scope
            # The search may return results even if none explicitly match "semantic"
            # because semantic search is based on embeddings, not keyword matching
            assert isinstance(scoped_results, list)

            # Step 6: Perform semantic search (across entire graph)
            semantic_results = search_semantic("test", limit=10, client=client)
            assert len(semantic_results) > 0

            # Should find nodes related to testing
            result_nodes = [node for node, _ in semantic_results]
            assert any("test" in node.content.lower() for node in result_nodes)

            # Step 7: Query by temporal range
            now = datetime.utcnow()
            two_minutes_ago = now - timedelta(minutes=2)
            two_minutes_later = now + timedelta(minutes=2)

            temporal_results = query_temporal_nodes(
                start=two_minutes_ago,
                end=two_minutes_later,
                client=client
            )

            # All nodes should be within the time range since they were just created
            assert len(temporal_results) >= 7  # 1 project + 1 session + 3 tasks + 2 decisions

            # Verify that our project is in the results
            assert any(node.uuid == project_id for node in temporal_results)

        finally:
            client.disconnect()

    def test_knowledge_discovery_workflow(self):
        """
        Test a knowledge discovery workflow:
        1. Create multiple projects with related content
        2. Add discoveries and ideas to projects
        3. Use graph traversal to explore relationships
        4. Find related nodes using semantic search
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create multiple projects
            project1 = Node(
                type="project",
                content="Authentication System",
                embedding=[0.9, 0.3, 0.0, 0.0, 0.0]
            )
            project1_id = client.add_node(project1)

            project2 = Node(
                type="project",
                content="API Security Framework",
                embedding=[0.8, 0.4, 0.1, 0.0, 0.0]
            )
            project2_id = client.add_node(project2)

            # Step 2: Add discoveries to projects
            discovery1 = Node(
                type="discovery",
                content="JWT tokens provide stateless authentication",
                embedding=[0.85, 0.35, 0.05, 0.0, 0.0]
            )
            discovery1_id = client.add_node(discovery1)

            discovery2 = Node(
                type="discovery",
                content="Rate limiting prevents API abuse",
                embedding=[0.75, 0.45, 0.15, 0.0, 0.0]
            )
            discovery2_id = client.add_node(discovery2)

            # Add ideas
            idea1 = Node(
                type="idea",
                content="Implement OAuth2 for third-party integrations",
                embedding=[0.88, 0.32, 0.02, 0.0, 0.0]
            )
            idea1_id = client.add_node(idea1)

            # Link discoveries and ideas to projects
            client.add_edge(Edge(type="contains", source_id=project1_id, target_id=discovery1_id))
            client.add_edge(Edge(type="contains", source_id=project2_id, target_id=discovery2_id))
            client.add_edge(Edge(type="spawned", source_id=discovery1_id, target_id=idea1_id))

            # Create cross-project relationship
            client.add_edge(Edge(type="related_to", source_id=project1_id, target_id=project2_id))

            # Step 3: Use graph traversal to explore relationships
            traversal_results = traverse(project1_id, depth=2, client=client)

            # Should have multiple levels
            assert "0" in traversal_results
            assert "1" in traversal_results

            # At depth 0, should have project1
            assert len(traversal_results["0"]) == 1
            assert traversal_results["0"][0].uuid == project1_id

            # At depth 1, should have discovery1 and project2
            depth1_nodes = traversal_results["1"]
            depth1_uuids = [node.uuid for node in depth1_nodes]
            assert discovery1_id in depth1_uuids
            assert project2_id in depth1_uuids

            # Step 4: Find related nodes using get_related
            related_to_discovery1 = get_related(
                discovery1_id,
                edge_type="spawned",
                direction="outgoing",
                client=client
            )

            # Should find the idea spawned from discovery1
            assert len(related_to_discovery1) > 0
            # get_related returns list of (Node, Edge) tuples
            related_uuids = [node.uuid for node, edge in related_to_discovery1]
            assert idea1_id in related_uuids

            # Step 5: Semantic search for authentication-related content
            auth_results = search_semantic("authentication", limit=10, client=client)

            # Should find authentication-related nodes
            assert len(auth_results) > 0
            result_nodes = [node for node, _ in auth_results]

            # Project1 and discovery1 should rank high
            high_scoring_nodes = [node for node, score in auth_results[:3]]
            assert any(node.uuid in [project1_id, discovery1_id] for node in high_scoring_nodes)

        finally:
            client.disconnect()

    def test_hierarchical_scope_workflow(self):
        """
        Test hierarchical scoping workflow:
        1. Create multi-level hierarchy (project -> sessions -> tasks -> notes)
        2. Perform scoped searches at different levels
        3. Verify scope isolation
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Step 1: Create multi-level hierarchy
            project = Node(
                type="project",
                content="Documentation System",
                embedding=[0.5, 0.5, 0.5, 0.0, 0.0]
            )
            project_id = client.add_node(project)

            # Create two sessions under the project
            session1 = Node(
                type="session",
                content="Architecture Planning",
                embedding=[0.6, 0.4, 0.5, 0.1, 0.0]
            )
            session1_id = client.add_node(session1)

            session2 = Node(
                type="session",
                content="Implementation Sprint",
                embedding=[0.4, 0.6, 0.5, 0.1, 0.0]
            )
            session2_id = client.add_node(session2)

            # Link sessions to project
            client.add_edge(Edge(type="contains", source_id=project_id, target_id=session1_id))
            client.add_edge(Edge(type="contains", source_id=project_id, target_id=session2_id))

            # Add tasks to session1
            task1_1 = Node(
                type="task",
                content="Design database schema",
                embedding=[0.7, 0.3, 0.4, 0.2, 0.0]
            )
            task1_1_id = client.add_node(task1_1)

            # Add tasks to session2
            task2_1 = Node(
                type="task",
                content="Implement REST API endpoints",
                embedding=[0.3, 0.7, 0.4, 0.2, 0.0]
            )
            task2_1_id = client.add_node(task2_1)

            # Link tasks to sessions
            client.add_edge(Edge(type="contains", source_id=session1_id, target_id=task1_1_id))
            client.add_edge(Edge(type="contains", source_id=session2_id, target_id=task2_1_id))

            # Add notes to tasks
            note1 = Node(
                type="note",
                content="Consider using PostgreSQL for relational data",
                embedding=[0.75, 0.25, 0.35, 0.25, 0.0]
            )
            note1_id = client.add_node(note1)

            note2 = Node(
                type="note",
                content="Use FastAPI framework for API development",
                embedding=[0.25, 0.75, 0.35, 0.25, 0.0]
            )
            note2_id = client.add_node(note2)

            # Link notes to tasks
            client.add_edge(Edge(type="contains", source_id=task1_1_id, target_id=note1_id))
            client.add_edge(Edge(type="contains", source_id=task2_1_id, target_id=note2_id))

            # Step 2: Perform scoped searches at different levels

            # Search entire project for "API"
            project_results = search_scoped(project_id, "API", limit=10, client=client)
            project_result_nodes = [node for node, _ in project_results]

            # Should find task2_1 and note2 which mention API
            project_uuids = [node.uuid for node in project_result_nodes]
            assert task2_1_id in project_uuids or note2_id in project_uuids

            # Search only session1 for "database"
            session1_results = search_scoped(session1_id, "database", limit=10, client=client)
            session1_result_nodes = [node for node, _ in session1_results]

            # Should find task1_1 and note1 which mention database
            session1_uuids = [node.uuid for node in session1_result_nodes]
            assert task1_1_id in session1_uuids or note1_id in session1_uuids

            # Step 3: Verify scope isolation

            # Search session2 for "PostgreSQL" should NOT find note1 (which is in session1)
            session2_results = search_scoped(session2_id, "PostgreSQL", limit=10, client=client)
            session2_result_nodes = [node for node, _ in session2_results]
            session2_uuids = [node.uuid for node in session2_result_nodes]

            # note1 should NOT be in session2's scope
            assert note1_id not in session2_uuids

        finally:
            client.disconnect()

    def test_temporal_filtering_workflow(self):
        """
        Test temporal filtering workflow:
        1. Create nodes at different time points
        2. Query for specific time ranges
        3. Verify temporal accuracy
        """
        client = GraphitiClient()
        client.connect()

        try:
            # Use utcnow to match the timestamp format used in models.py
            now = datetime.utcnow()

            # Create project (time: now)
            project = Node(
                type="project",
                content="Time-based Analysis",
                embedding=[0.5, 0.5, 0.5, 0.0, 0.0]
            )
            project_id = client.add_node(project)

            # Create a task
            task = Node(
                type="task",
                content="Analyze temporal patterns",
                embedding=[0.6, 0.4, 0.5, 0.0, 0.0]
            )
            task_id = client.add_node(task)

            # Query for nodes created in the last minute
            # Add a small buffer to account for execution time
            one_minute_ago = now - timedelta(minutes=2)
            one_minute_later = now + timedelta(minutes=2)

            recent_nodes = query_temporal_nodes(
                start=one_minute_ago,
                end=one_minute_later,
                client=client
            )

            # Both nodes should be in the results
            recent_uuids = [node.uuid for node in recent_nodes]
            assert project_id in recent_uuids
            assert task_id in recent_uuids

            # Query for nodes created in the future (should be empty)
            future_start = now + timedelta(hours=1)
            future_end = now + timedelta(hours=2)

            future_nodes = query_temporal_nodes(
                start=future_start,
                end=future_end,
                client=client
            )

            # Should not find any nodes
            assert len(future_nodes) == 0

            # Query for nodes created in the past (before these were created)
            past_start = now - timedelta(hours=2)
            past_end = now - timedelta(hours=1)

            past_nodes = query_temporal_nodes(
                start=past_start,
                end=past_end,
                client=client
            )

            # Should not find our nodes (they were created more recently)
            past_uuids = [node.uuid for node in past_nodes]
            assert project_id not in past_uuids
            assert task_id not in past_uuids

        finally:
            client.disconnect()

    def test_context_manager_workflow(self):
        """
        Test using GraphitiClient as a context manager in a workflow.
        """
        # Use context manager for automatic connection/disconnection
        with GraphitiClient() as client:
            # Create a simple workflow
            project = Node(
                type="project",
                content="Context Manager Test",
                embedding=[0.5, 0.5, 0.5, 0.0, 0.0]
            )
            project_id = client.add_node(project)

            # Verify node was added
            retrieved = client.get_node(project_id)
            assert retrieved is not None
            assert retrieved.content == "Context Manager Test"

            # Perform a search
            results = search_semantic("context", limit=5, client=client)
            assert isinstance(results, list)

        # Client should be disconnected after exiting context
        # (We can't easily verify this without accessing internal state,
        # but the context manager should handle it)

    def test_error_handling_workflow(self):
        """
        Test error handling in a workflow scenario.
        """
        client = GraphitiClient()

        # Attempt operations without connecting (should raise errors)
        with pytest.raises(ConnectionError):
            client.add_node(Node(type="project", content="Test"))

        with pytest.raises(ConnectionError):
            client.get_node("non-existent-id")

        # Connect and perform valid operations
        client.connect()

        try:
            # Create a node
            node = Node(type="project", content="Error Handling Test")
            node_id = client.add_node(node)

            # Try to get a non-existent node
            result = client.get_node("non-existent-uuid")
            assert result is None  # Should return None, not raise an error

            # Create a valid edge between two nodes
            node2 = Node(type="task", content="Another node")
            node2_id = client.add_node(node2)

            edge = client.add_edge(Edge(
                type="contains",
                source_id=node_id,
                target_id=node2_id
            ))
            assert edge is not None

        finally:
            client.disconnect()


class TestConcurrentOperations:
    """Test scenarios with multiple simultaneous operations."""

    def test_multiple_clients(self):
        """Test that multiple clients can coexist (though they share in-memory state)."""
        client1 = GraphitiClient()
        client2 = GraphitiClient()

        client1.connect()
        client2.connect()

        try:
            # Add a node with client1
            node1 = Node(type="project", content="Client 1 Project")
            node1_id = client1.add_node(node1)

            # Verify we can retrieve it (note: in real implementation with database,
            # both clients would see the same data)
            retrieved = client1.get_node(node1_id)
            assert retrieved is not None

        finally:
            client1.disconnect()
            client2.disconnect()

    def test_batch_operations(self):
        """Test adding multiple nodes and edges in batch."""
        client = GraphitiClient()
        client.connect()

        try:
            # Create multiple nodes
            nodes = []
            for i in range(10):
                node = Node(
                    type="task",
                    content=f"Batch Task {i}",
                    embedding=[float(i) / 10, 0.5, 0.5, 0.0, 0.0]
                )
                node_id = client.add_node(node)
                nodes.append((node_id, node))

            # Create edges between sequential nodes
            edges = []
            for i in range(len(nodes) - 1):
                edge = client.add_edge(Edge(
                    type="preceded_by",
                    source_id=nodes[i + 1][0],
                    target_id=nodes[i][0]
                ))
                edges.append(edge)

            # Verify all nodes were created
            assert len(nodes) == 10

            # Verify all edges were created
            assert len(edges) == 9

            # Perform a semantic search across batch
            results = search_semantic("batch", limit=20, client=client)
            result_nodes = [node for node, _ in results]

            # Should find our batch tasks
            assert any("Batch Task" in node.content for node in result_nodes)

        finally:
            client.disconnect()
