# Graphiti Knowledge Graph Integration

A powerful Python client for interacting with the AIOS knowledge graph backend. This integration provides semantic search, hierarchical scoping, temporal queries, and graph traversal capabilities for managing agent memory and context.

## Overview

The Graphiti integration enables agents to:
- **Store and retrieve knowledge** as nodes and edges in a graph structure
- **Search semantically** using vector embeddings for conceptual queries
- **Organize hierarchically** using scoped searches within projects/sessions
- **Traverse relationships** to discover connected information
- **Query temporally** to find activities within time ranges

## Installation

The Graphiti integration is part of the AIOS backend and requires no additional installation beyond the main project dependencies.

```bash
# From the project root
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge

# Create and connect a client
client = GraphitiClient()
client.connect()

# Create a node
project = Node(
    type="project",
    content="My AIOS Project",
    embedding=[0.8, 0.6, 0.2, 0.0, 0.0]
)
project_id = client.add_node(project)

# Create a related node
task = Node(
    type="task",
    content="Implement authentication",
    embedding=[0.7, 0.5, 0.3, 0.0, 0.0]
)
task_id = client.add_node(task)

# Link them with an edge
edge = Edge(
    type="contains",
    source_id=project_id,
    target_id=task_id
)
client.add_edge(edge)

# Disconnect when done
client.disconnect()
```

### Context Manager Pattern

```python
from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node

# Using context manager (automatically connects/disconnects)
with GraphitiClient() as client:
    node = Node(type="idea", content="Add caching layer")
    node_id = client.add_node(node)
    print(f"Created node: {node_id}")
```

## Core Concepts

### Nodes

Nodes represent entities in the knowledge graph. Common node types:
- `project`: Top-level projects or initiatives
- `session`: Work sessions or conversations
- `task`: Action items or work units
- `decision`: Choices made and their rationale
- `idea`: Potential features or improvements
- `discovery`: Learnings or insights

Each node has:
- `type`: Classification of the node
- `content`: Main text content
- `uuid`: Unique identifier (auto-generated)
- `created_at`: Creation timestamp (auto-generated)
- `updated_at`: Last update timestamp (auto-generated)
- `embedding`: Optional vector for semantic search
- `metadata`: Optional custom fields

### Edges

Edges represent relationships between nodes. Common edge types:
- `contains`: Hierarchical parent-child relationship
- `references`: Bidirectional reference or citation
- `spawned`: Temporal sequence (one led to another)
- `related_to`: General association
- `decided_in`: Decision made in a specific context

Each edge has:
- `type`: Classification of the relationship
- `source_id`: UUID of the source node
- `target_id`: UUID of the target node
- `uuid`: Unique identifier (auto-generated)
- `created_at`: Creation timestamp (auto-generated)
- `updated_at`: Last update timestamp (auto-generated)
- `metadata`: Optional custom fields

## API Reference

### GraphitiClient

#### Connection Management

```python
client = GraphitiClient(config=None)  # Optional custom config
client.connect()                       # Establish connection
client.disconnect()                    # Close connection
client.is_connected()                  # Check connection status
```

#### Node Operations

```python
# Create nodes
node_id = client.add_node(node)        # Returns UUID
node = client.create_node(node)        # Returns Node object

# Retrieve nodes
node = client.get_node(node_id)        # Get by UUID
nodes = client.query_nodes(filters)    # Query with filters
```

#### Edge Operations

```python
# Create edges
edge_id = client.add_edge(edge)        # Returns UUID
edge = client.create_edge(edge)        # Returns Edge object

# Retrieve edges
edge = client.get_edge(edge_id)        # Get by UUID
edges = client.query_edges(filters)    # Query with filters

# Update edges
edge = client.update_edge(edge_id, updates)

# Delete edges
success = client.delete_edge(edge_id)  # Returns bool
```

### Query Utilities

#### Semantic Search

Search across all nodes using vector similarity:

```python
from apps.backend.integrations.graphiti.queries import search_semantic

results = search_semantic(
    query="authentication implementation",
    limit=10,
    client=client  # Optional, creates new client if not provided
)

for node, score in results:
    print(f"{node.type}: {node.content} (similarity: {score:.2f})")
```

#### Scoped Search

Search within a hierarchical scope (project, session, etc.):

```python
from apps.backend.integrations.graphiti.queries import search_scoped

results = search_scoped(
    scope_node_id=project_id,
    query="authentication",
    limit=10,
    client=client
)

for node, score in results:
    print(f"{node.type}: {node.content} (similarity: {score:.2f})")
```

#### Graph Traversal

Explore the graph from a starting node:

```python
from apps.backend.integrations.graphiti.queries import traverse

results = traverse(
    node_id=project_id,
    depth=2,
    client=client
)

print(f"Direct neighbors: {len(results['1'])}")
print(f"Second-level neighbors: {len(results.get('2', []))}")
```

#### Related Nodes

Get nodes directly connected to a node:

```python
from apps.backend.integrations.graphiti.queries import get_related

# Get all tasks in a project
related = get_related(
    node_id=project_id,
    edge_type="contains",
    direction="outgoing",
    client=client
)

for node, edge in related:
    print(f"Task: {node.content}")
```

#### Temporal Queries

Query nodes and edges by time range:

```python
from datetime import datetime, timedelta
from apps.backend.integrations.graphiti.queries import query_temporal, query_temporal_nodes

# Get all activity in the last 24 hours
end = datetime.utcnow()
start = end - timedelta(hours=24)

results = query_temporal(start, end, include_edges=True, client=client)
print(f"Nodes: {len(results['nodes'])}, Edges: {len(results['edges'])}")

# Get only decision nodes from last week
decisions = query_temporal_nodes(
    start=end - timedelta(days=7),
    end=end,
    node_type="decision",
    client=client
)
print(f"Decisions made this week: {len(decisions)}")
```

## Usage Patterns

### Pattern 1: Project Management

Organize work hierarchically with projects containing sessions and tasks:

```python
# Create project
project = Node(type="project", content="Authentication System")
project_id = client.add_node(project)

# Create session
session = Node(type="session", content="Sprint Planning")
session_id = client.add_node(session)
client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))

# Add tasks
task = Node(type="task", content="Implement JWT tokens")
task_id = client.add_node(task)
client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))

# Find all tasks in project
tasks = search_scoped(project_id, "implement", limit=20, client=client)
```

### Pattern 2: Decision Tracking

Track decisions and their context:

```python
# Create a decision
decision = Node(
    type="decision",
    content="Use JWT for authentication",
    metadata={"rationale": "Stateless, scalable, widely supported"}
)
decision_id = client.add_node(decision)

# Link to the session where it was decided
client.add_edge(Edge(type="decided_in", source_id=decision_id, target_id=session_id))

# Link to related task
client.add_edge(Edge(type="related_to", source_id=decision_id, target_id=task_id))

# Later, find all decisions in a project
decisions = query_temporal_nodes(
    start=project_start_date,
    end=datetime.utcnow(),
    node_type="decision",
    client=client
)
```

### Pattern 3: Knowledge Discovery

Build a knowledge graph of ideas and discoveries:

```python
# Record a discovery
discovery = Node(
    type="discovery",
    content="Redis significantly improves API response time",
    embedding=[0.8, 0.4, 0.1, 0.0, 0.0]
)
discovery_id = client.add_node(discovery)

# Link to related project
client.add_edge(Edge(type="related_to", source_id=discovery_id, target_id=project_id))

# Later, find related discoveries
results = search_semantic("performance optimization", limit=10, client=client)
discoveries = [node for node, score in results if node.type == "discovery"]
```

### Pattern 4: Temporal Analysis

Analyze activity over time:

```python
from datetime import datetime, timedelta

# Get all activity in the last 7 days
end = datetime.utcnow()
start = end - timedelta(days=7)

results = query_temporal(start, end, include_edges=True, client=client)

# Group by day
from collections import defaultdict
by_day = defaultdict(list)
for node in results['nodes']:
    day = node.created_at.date()
    by_day[day].append(node)

for day, nodes in sorted(by_day.items()):
    print(f"{day}: {len(nodes)} activities")
```

## Configuration

Configure the client using environment variables or a config object:

```python
from apps.backend.integrations.graphiti.config import GraphitiConfig

config = GraphitiConfig(
    host="localhost",
    port=7687,
    username="neo4j",
    password="your-password"
)

client = GraphitiClient(config=config)
```

Environment variables:
- `GRAPHITI_HOST`: Database host (default: "localhost")
- `GRAPHITI_PORT`: Database port (default: 7687)
- `GRAPHITI_USERNAME`: Database username (default: "neo4j")
- `GRAPHITI_PASSWORD`: Database password (default: "password")

## Best Practices

### 1. Use Embeddings for Semantic Search

Always provide embeddings for nodes that you want to search semantically:

```python
# Good: Include embedding
node = Node(
    type="task",
    content="Implement caching layer",
    embedding=[0.8, 0.6, 0.2, 0.0, 0.0]  # From embedding service
)

# Limited: No embedding (won't appear in semantic search)
node = Node(type="task", content="Implement caching layer")
```

### 2. Organize Hierarchically

Use `contains` edges to create hierarchies that enable scoped searches:

```python
# Create hierarchy: project -> session -> task
client.add_edge(Edge(type="contains", source_id=project_id, target_id=session_id))
client.add_edge(Edge(type="contains", source_id=session_id, target_id=task_id))

# Now you can search within project scope
results = search_scoped(project_id, "task query", client=client)
```

### 3. Use Context Managers

Prefer context managers to ensure proper cleanup:

```python
# Good: Automatic cleanup
with GraphitiClient() as client:
    client.add_node(node)

# Works but requires manual cleanup
client = GraphitiClient()
client.connect()
try:
    client.add_node(node)
finally:
    client.disconnect()
```

### 4. Add Meaningful Metadata

Use metadata for custom fields and filtering:

```python
node = Node(
    type="task",
    content="Implement authentication",
    metadata={
        "priority": "high",
        "assignee": "agent-001",
        "estimated_hours": 8,
        "tags": ["security", "backend"]
    }
)
```

### 5. Link Related Concepts

Build rich knowledge graphs by linking related nodes:

```python
# Link decision to task
client.add_edge(Edge(type="related_to", source_id=decision_id, target_id=task_id))

# Link idea to discovery
client.add_edge(Edge(type="spawned", source_id=discovery_id, target_id=idea_id))

# Later, explore the graph
neighborhood = traverse(decision_id, depth=2, client=client)
```

## Examples

See `examples.py` for complete, runnable examples demonstrating:
- Basic CRUD operations
- Semantic and scoped search
- Graph traversal and relationship queries
- Temporal queries and analysis
- Complete project management workflow
- Knowledge discovery workflow

Run the examples:

```bash
python apps/backend/integrations/graphiti/examples.py
```

## Troubleshooting

### Connection Issues

```python
# Check connection status
if not client.is_connected():
    print("Not connected!")
    client.connect()
```

### Empty Search Results

```python
# Ensure nodes have embeddings for semantic search
results = search_semantic("query", limit=10, client=client)
if not results:
    print("No results - check that nodes have embeddings")
```

### Missing Nodes in Scoped Search

```python
# Verify hierarchy with traverse
hierarchy = traverse(scope_node_id, depth=3, client=client)
for level, nodes in hierarchy.items():
    print(f"Level {level}: {len(nodes)} nodes")
```

## Architecture

The Graphiti integration consists of:

- **`client.py`**: High-level client for connection and CRUD operations
- **`models.py`**: Data models for nodes and edges
- **`queries.py`**: Advanced query utilities (semantic, temporal, traversal)
- **`config.py`**: Configuration management
- **`schema.py`**: Schema definitions and validation

## Future Enhancements

Planned features:
- Real embedding service integration (OpenAI, sentence-transformers)
- Neo4j/LadybugDB driver integration
- Batch operations for performance
- Advanced query filters
- Graph analytics (PageRank, community detection)
- Subscription/watch patterns for real-time updates

## Contributing

When contributing to the Graphiti integration:
1. Follow existing code patterns
2. Add comprehensive docstrings
3. Include type hints
4. Write tests for new features
5. Update this README with new capabilities

## License

Part of the AIOS project.
