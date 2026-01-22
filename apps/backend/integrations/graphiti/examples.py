"""
Graphiti Integration Examples

Demonstrates common usage patterns and capabilities of the Graphiti knowledge
graph integration. Run this file to see examples in action.

Usage:
    python apps/backend/integrations/graphiti/examples.py
"""

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


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def example_1_basic_crud():
    """
    Example 1: Basic CRUD Operations

    Demonstrates creating, reading, updating, and deleting nodes and edges.
    """
    print_header("Example 1: Basic CRUD Operations")

    client = GraphitiClient()
    client.connect()

    try:
        # Create a node
        print("\n1. Creating a project node...")
        project = Node(
            type="project",
            content="AIOS Authentication System",
            embedding=[0.9, 0.3, 0.0, 0.0, 0.0],
            metadata={"priority": "high", "status": "active"}
        )
        project_id = client.add_node(project)
        print(f"   Created project with ID: {project_id}")

        # Create another node
        print("\n2. Creating a task node...")
        task = Node(
            type="task",
            content="Implement JWT token generation",
            embedding=[0.85, 0.35, 0.05, 0.0, 0.0],
            metadata={"assignee": "agent-001", "estimated_hours": 8}
        )
        task_id = client.add_node(task)
        print(f"   Created task with ID: {task_id}")

        # Create an edge
        print("\n3. Creating a 'contains' edge...")
        edge = Edge(
            type="contains",
            source_id=project_id,
            target_id=task_id,
            metadata={"created_by": "example_script"}
        )
        edge_id = client.add_edge(edge)
        print(f"   Created edge with ID: {edge_id}")

        # Read the node
        print("\n4. Reading the project node...")
        retrieved_project = client.get_node(project_id)
        print(f"   Retrieved: {retrieved_project.type} - {retrieved_project.content}")

        # Read the edge
        print("\n5. Reading the edge...")
        retrieved_edge = client.get_edge(edge_id)
        print(f"   Retrieved edge: {retrieved_edge.type} connecting {retrieved_edge.source_id[:8]}... -> {retrieved_edge.target_id[:8]}...")

        # Update the edge
        print("\n6. Updating the edge metadata...")
        updated_edge = client.update_edge(edge_id, {
            "metadata": {"updated_by": "example_script", "version": 2}
        })
        print(f"   Updated edge metadata: {updated_edge.metadata}")

        # Query edges
        print("\n7. Querying edges by type...")
        edges = client.query_edges(filters={"type": "contains"})
        print(f"   Found {len(edges)} 'contains' edges")

        # Delete the edge
        print("\n8. Deleting the edge...")
        deleted = client.delete_edge(edge_id)
        print(f"   Edge deleted: {deleted}")

        print("\n✓ Basic CRUD operations completed successfully!")

    finally:
        client.disconnect()


def example_2_context_manager():
    """
    Example 2: Using Context Manager

    Demonstrates the recommended pattern using context managers for
    automatic connection and disconnection.
    """
    print_header("Example 2: Using Context Manager")

    print("\n1. Creating nodes using context manager...")

    with GraphitiClient() as client:
        # Create multiple nodes in one session
        idea = Node(
            type="idea",
            content="Add Redis caching for improved performance",
            embedding=[0.6, 0.4, 0.5, 0.0, 0.0]
        )
        idea_id = client.add_node(idea)
        print(f"   Created idea: {idea_id}")

        discovery = Node(
            type="discovery",
            content="Current API response time averages 200ms",
            embedding=[0.65, 0.45, 0.48, 0.0, 0.0]
        )
        discovery_id = client.add_node(discovery)
        print(f"   Created discovery: {discovery_id}")

        # Link them
        edge = Edge(type="spawned", source_id=discovery_id, target_id=idea_id)
        client.add_edge(edge)
        print(f"   Linked discovery -> idea")

    print("\n✓ Context manager automatically handled connection cleanup!")


def example_3_semantic_search():
    """
    Example 3: Semantic Search

    Demonstrates semantic search using vector embeddings to find
    conceptually similar nodes.
    """
    print_header("Example 3: Semantic Search")

    client = GraphitiClient()
    client.connect()

    try:
        # Create nodes with different topics
        print("\n1. Creating nodes with various topics...")

        nodes_data = [
            ("task", "Implement user authentication with OAuth2", [0.9, 0.3, 0.0, 0.0, 0.0]),
            ("task", "Add unit tests for login functionality", [0.0, 0.0, 0.8, 0.6, 0.0]),
            ("task", "Set up Redis for session caching", [0.6, 0.4, 0.2, 0.0, 0.0]),
            ("decision", "Use JWT tokens for stateless auth", [0.85, 0.35, 0.05, 0.0, 0.0]),
            ("decision", "Implement integration tests with pytest", [0.0, 0.0, 0.85, 0.65, 0.0]),
            ("idea", "Add two-factor authentication option", [0.88, 0.32, 0.02, 0.0, 0.0]),
        ]

        for node_type, content, embedding in nodes_data:
            node = Node(type=node_type, content=content, embedding=embedding)
            client.add_node(node)
            print(f"   Added {node_type}: {content[:50]}...")

        # Perform semantic searches
        print("\n2. Searching for 'authentication'...")
        results = search_semantic("authentication", limit=3, client=client)
        for i, (node, score) in enumerate(results, 1):
            print(f"   {i}. [{score:.3f}] {node.type}: {node.content}")

        print("\n3. Searching for 'testing'...")
        results = search_semantic("testing", limit=3, client=client)
        for i, (node, score) in enumerate(results, 1):
            print(f"   {i}. [{score:.3f}] {node.type}: {node.content}")

        print("\n✓ Semantic search finds conceptually similar nodes!")

    finally:
        client.disconnect()


def example_4_hierarchical_scoping():
    """
    Example 4: Hierarchical Scoping

    Demonstrates creating hierarchies and performing scoped searches
    within specific contexts (projects, sessions, etc.).
    """
    print_header("Example 4: Hierarchical Scoping")

    client = GraphitiClient()
    client.connect()

    try:
        print("\n1. Creating project hierarchy...")

        # Create a project
        project = Node(
            type="project",
            content="E-commerce Platform",
            embedding=[0.7, 0.5, 0.0, 0.0, 0.0]
        )
        project_id = client.add_node(project)
        print(f"   Created project: {project_id[:8]}...")

        # Create a session
        session = Node(
            type="session",
            content="Sprint 1 Planning",
            embedding=[0.68, 0.52, 0.1, 0.0, 0.0]
        )
        session_id = client.add_node(session)
        client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
        print(f"   Created session: {session_id[:8]}...")

        # Create tasks
        tasks_data = [
            ("Set up payment gateway integration", [0.75, 0.45, 0.0, 0.0, 0.0]),
            ("Implement shopping cart functionality", [0.72, 0.48, 0.05, 0.0, 0.0]),
            ("Add product search with filters", [0.8, 0.4, 0.0, 0.0, 0.0]),
        ]

        for content, embedding in tasks_data:
            task = Node(type="task", content=content, embedding=embedding)
            task_id = client.add_node(task)
            client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))
            print(f"   Added task: {content}")

        # Perform scoped search
        print("\n2. Searching for 'payment' within project scope...")
        results = search_scoped(project_id, "payment", limit=5, client=client)
        print(f"   Found {len(results)} results within project:")
        for node, score in results:
            print(f"   - [{score:.3f}] {node.type}: {node.content}")

        print("\n3. Searching for 'search' across all nodes...")
        global_results = search_semantic("search", limit=5, client=client)
        print(f"   Found {len(global_results)} results globally:")
        for node, score in global_results:
            print(f"   - [{score:.3f}] {node.type}: {node.content}")

        print("\n✓ Scoped search limits results to specific hierarchies!")

    finally:
        client.disconnect()


def example_5_graph_traversal():
    """
    Example 5: Graph Traversal

    Demonstrates traversing the graph to explore connections and discover
    multi-hop relationships.
    """
    print_header("Example 5: Graph Traversal")

    client = GraphitiClient()
    client.connect()

    try:
        print("\n1. Building a knowledge graph...")

        # Create a central concept
        concept = Node(
            type="discovery",
            content="Microservices improve scalability",
            embedding=[0.8, 0.2, 0.0, 0.0, 0.0]
        )
        concept_id = client.add_node(concept)
        print(f"   Created central concept: {concept_id[:8]}...")

        # Create directly related nodes (depth 1)
        related_1_data = [
            ("idea", "Split monolith into user service", [0.78, 0.22, 0.0, 0.0, 0.0]),
            ("idea", "Split monolith into order service", [0.75, 0.25, 0.0, 0.0, 0.0]),
            ("decision", "Use API gateway pattern", [0.82, 0.18, 0.0, 0.0, 0.0]),
        ]

        depth_1_ids = []
        for node_type, content, embedding in related_1_data:
            node = Node(type=node_type, content=content, embedding=embedding)
            node_id = client.add_node(node)
            client.add_edge(Edge(type="related_to", source_id=concept_id, target_id=node_id))
            depth_1_ids.append(node_id)
            print(f"   Added depth-1 {node_type}: {content[:40]}...")

        # Create nodes related to depth-1 nodes (depth 2)
        task = Node(
            type="task",
            content="Implement user service API endpoints",
            embedding=[0.76, 0.24, 0.0, 0.0, 0.0]
        )
        task_id = client.add_node(task)
        client.add_edge(Edge(type="spawned", source_id=depth_1_ids[0], target_id=task_id))
        print(f"   Added depth-2 task: {task.content[:40]}...")

        # Traverse from the central concept
        print("\n2. Traversing graph with depth=1...")
        results = traverse(concept_id, depth=1, client=client)
        print(f"   Depth 0 (start): {len(results['0'])} nodes")
        print(f"   Depth 1 (neighbors): {len(results['1'])} nodes")
        for node in results['1']:
            print(f"     - {node.type}: {node.content[:50]}...")

        print("\n3. Traversing graph with depth=2...")
        results = traverse(concept_id, depth=2, client=client)
        print(f"   Depth 0 (start): {len(results['0'])} nodes")
        print(f"   Depth 1 (neighbors): {len(results['1'])} nodes")
        print(f"   Depth 2 (2-hop neighbors): {len(results.get('2', []))} nodes")
        for node in results.get('2', []):
            print(f"     - {node.type}: {node.content[:50]}...")

        print("\n✓ Graph traversal discovers multi-hop relationships!")

    finally:
        client.disconnect()


def example_6_related_nodes():
    """
    Example 6: Querying Related Nodes

    Demonstrates finding nodes directly connected via specific edge types
    and directions.
    """
    print_header("Example 6: Querying Related Nodes")

    client = GraphitiClient()
    client.connect()

    try:
        print("\n1. Creating a project with multiple tasks...")

        # Create project
        project = Node(
            type="project",
            content="API Redesign Project",
            embedding=[0.7, 0.3, 0.0, 0.0, 0.0]
        )
        project_id = client.add_node(project)

        # Create and link tasks
        task_contents = [
            "Design new REST API endpoints",
            "Update API documentation",
            "Implement rate limiting",
            "Add API versioning support",
        ]

        for content in task_contents:
            task = Node(type="task", content=content, embedding=[0.68, 0.32, 0.0, 0.0, 0.0])
            task_id = client.add_node(task)
            client.add_edge(Edge(type="contains", source_id=project_id, target_id=task_id))
            print(f"   Added task: {content}")

        # Create a decision and link it to the project
        decision = Node(
            type="decision",
            content="Use GraphQL instead of REST",
            embedding=[0.72, 0.28, 0.0, 0.0, 0.0]
        )
        decision_id = client.add_node(decision)
        client.add_edge(Edge(type="decided_in", source_id=decision_id, target_id=project_id))
        print(f"   Added decision: {decision.content}")

        # Query related nodes
        print("\n2. Finding all tasks in the project (outgoing 'contains')...")
        related = get_related(
            node_id=project_id,
            edge_type="contains",
            direction="outgoing",
            client=client
        )
        print(f"   Found {len(related)} tasks:")
        for node, edge in related:
            print(f"   - {node.content}")

        print("\n3. Finding what the decision was decided in (incoming 'decided_in')...")
        related = get_related(
            node_id=project_id,
            edge_type="decided_in",
            direction="incoming",
            client=client
        )
        print(f"   Found {len(related)} decisions:")
        for node, edge in related:
            print(f"   - {node.content}")

        print("\n4. Finding all related nodes (any edge type, both directions)...")
        related = get_related(
            node_id=project_id,
            edge_type=None,
            direction="both",
            client=client
        )
        print(f"   Found {len(related)} related nodes:")
        for node, edge in related:
            print(f"   - [{edge.type}] {node.type}: {node.content[:50]}...")

        print("\n✓ Related nodes query provides targeted relationship exploration!")

    finally:
        client.disconnect()


def example_7_temporal_queries():
    """
    Example 7: Temporal Queries

    Demonstrates querying nodes and edges by time ranges to analyze
    historical activity.
    """
    print_header("Example 7: Temporal Queries")

    client = GraphitiClient()
    client.connect()

    try:
        print("\n1. Creating nodes at the current time...")

        # Create some nodes
        now = datetime.utcnow()
        for i in range(5):
            node = Node(
                type="task",
                content=f"Task created at {now.strftime('%H:%M:%S')}",
                embedding=[0.5, 0.5, 0.0, 0.0, 0.0]
            )
            client.add_node(node)

        print(f"   Created 5 tasks at {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Query by time range
        print("\n2. Querying nodes created in the last 5 minutes...")
        start = now - timedelta(minutes=5)
        end = now + timedelta(minutes=5)

        results = query_temporal(start, end, include_edges=False, client=client)
        print(f"   Found {len(results['nodes'])} nodes in time range:")
        for node in results['nodes'][:3]:  # Show first 3
            print(f"   - {node.type}: {node.content[:50]}...")

        print("\n3. Querying only 'task' nodes...")
        task_results = query_temporal_nodes(
            start=start,
            end=end,
            node_type="task",
            client=client
        )
        print(f"   Found {len(task_results)} task nodes")

        print("\n4. Querying with edge inclusion...")
        results_with_edges = query_temporal(start, end, include_edges=True, client=client)
        print(f"   Found {len(results_with_edges['nodes'])} nodes and {len(results_with_edges['edges'])} edges")

        print("\n✓ Temporal queries enable time-based analysis!")

    finally:
        client.disconnect()


def example_8_complete_workflow():
    """
    Example 8: Complete Project Management Workflow

    Demonstrates a realistic end-to-end workflow combining multiple
    features for project management.
    """
    print_header("Example 8: Complete Project Management Workflow")

    client = GraphitiClient()
    client.connect()

    try:
        print("\n1. Creating a new project...")
        project = Node(
            type="project",
            content="AI Agent Communication System",
            embedding=[0.8, 0.4, 0.0, 0.0, 0.0],
            metadata={"status": "active", "priority": "high"}
        )
        project_id = client.add_node(project)
        print(f"   Project created: {project.content}")

        print("\n2. Starting a planning session...")
        session = Node(
            type="session",
            content="Architecture Planning Session",
            embedding=[0.78, 0.42, 0.05, 0.0, 0.0]
        )
        session_id = client.add_node(session)
        client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
        print(f"   Session started: {session.content}")

        print("\n3. Recording decisions made during session...")
        decisions_data = [
            "Use WebSocket for real-time communication",
            "Implement message queue for reliability",
            "Store conversation history in knowledge graph",
        ]

        for content in decisions_data:
            decision = Node(
                type="decision",
                content=content,
                embedding=[0.75, 0.45, 0.1, 0.0, 0.0]
            )
            decision_id = client.add_node(decision)
            client.add_edge(Edge(type="decided_in", source_id=decision_id, target_id=session_id))
            print(f"   Decision recorded: {content}")

        print("\n4. Creating tasks based on decisions...")
        tasks_data = [
            "Implement WebSocket server",
            "Set up RabbitMQ message queue",
            "Design conversation storage schema",
            "Build message routing logic",
        ]

        task_ids = []
        for content in tasks_data:
            task = Node(
                type="task",
                content=content,
                embedding=[0.72, 0.48, 0.08, 0.0, 0.0]
            )
            task_id = client.add_node(task)
            client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))
            task_ids.append(task_id)
            print(f"   Task created: {content}")

        print("\n5. Recording a discovery during implementation...")
        discovery = Node(
            type="discovery",
            content="WebSocket connections scale better with connection pooling",
            embedding=[0.77, 0.43, 0.12, 0.0, 0.0]
        )
        discovery_id = client.add_node(discovery)
        client.add_edge(Edge(type="related_to", source_id=discovery_id, target_id=task_ids[0]))
        print(f"   Discovery recorded: {discovery.content}")

        print("\n6. Searching for all WebSocket-related items in project...")
        results = search_scoped(project_id, "WebSocket", limit=10, client=client)
        print(f"   Found {len(results)} WebSocket-related items:")
        for node, score in results:
            print(f"   - [{score:.3f}] {node.type}: {node.content[:60]}...")

        print("\n7. Exploring project structure via traversal...")
        structure = traverse(project_id, depth=2, client=client)
        print(f"   Project structure:")
        print(f"   - Level 0: {len(structure['0'])} node (project)")
        print(f"   - Level 1: {len(structure['1'])} nodes (session, etc.)")
        print(f"   - Level 2: {len(structure.get('2', []))} nodes (tasks, decisions, etc.)")

        print("\n8. Analyzing recent activity...")
        now = datetime.utcnow()
        start = now - timedelta(minutes=10)
        recent = query_temporal_nodes(start, now, client=client)
        print(f"   Recent activity (last 10 min): {len(recent)} nodes")

        # Group by type
        by_type = {}
        for node in recent:
            by_type[node.type] = by_type.get(node.type, 0) + 1

        print(f"   Activity breakdown:")
        for node_type, count in sorted(by_type.items()):
            print(f"   - {node_type}: {count}")

        print("\n✓ Complete workflow demonstrates integrated features!")

    finally:
        client.disconnect()


def main():
    """
    Run all examples in sequence.
    """
    print("\n" + "=" * 70)
    print("  Graphiti Integration Examples")
    print("  Demonstrating knowledge graph capabilities")
    print("=" * 70)

    examples = [
        example_1_basic_crud,
        example_2_context_manager,
        example_3_semantic_search,
        example_4_hierarchical_scoping,
        example_5_graph_traversal,
        example_6_related_nodes,
        example_7_temporal_queries,
        example_8_complete_workflow,
    ]

    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example {i} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("  All examples completed!")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - README.md: Complete documentation")
    print("  - tests/test_integration.py: Integration tests")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
