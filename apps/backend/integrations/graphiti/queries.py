"""
Query Utilities for Graphiti Knowledge Graph

Provides high-level query functions for semantic search, hierarchical scoping,
graph traversal, and temporal queries. These utilities build on the GraphitiClient
to enable powerful knowledge retrieval patterns.
"""

from typing import List, Optional, Tuple, Set, Dict, Any
import logging
import math
import time
from datetime import datetime

from .client import GraphitiClient
from .models import Node, Edge
from .schema import (
    METADATA_SOURCE_FILE,
    METADATA_CAPTURED_AT,
    METADATA_EPISODE_TYPE,
)

# Default maximum number of context results to return
MAX_CONTEXT_RESULTS = 10

# Default minimum score threshold for filtering results
DEFAULT_MIN_SCORE = 0.0

# Performance threshold for query timing warnings (in seconds)
QUERY_PERFORMANCE_THRESHOLD_SECONDS = 1.0

logger = logging.getLogger(__name__)


def _compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def _generate_query_embedding(query: str) -> List[float]:
    """
    Generate an embedding vector for a query string.

    This is a placeholder implementation that creates a simple embedding
    based on the query text. In production, this would call an actual
    embedding service (e.g., OpenAI embeddings, sentence-transformers).

    Args:
        query: The query text to embed

    Returns:
        A vector embedding of the query
    """
    # Simple placeholder: create a deterministic embedding based on query characteristics
    # In production, replace with actual embedding API call
    query_lower = query.lower()
    embedding = [
        float(len(query)),  # Length
        float(sum(ord(c) for c in query_lower[:10]) % 100) / 100,  # Character sum
        float(query_lower.count(' ')) / 10,  # Word count estimate
        float(query_lower.count('test')) * 10,  # Test keyword
        float(query_lower.count('project')) * 10,  # Project keyword
    ]

    # Normalize the embedding
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def search_semantic(
    query: str,
    limit: int = 10,
    client: Optional[GraphitiClient] = None
) -> List[Tuple[Node, float]]:
    """
    Perform semantic search across all nodes in the knowledge graph.

    Uses embedding-based similarity to find nodes that are semantically
    similar to the query, regardless of exact keyword matches. This enables
    natural language queries and conceptual search.

    Args:
        query: The search query (natural language or keywords)
        limit: Maximum number of results to return (default: 10)
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of (Node, score) tuples, sorted by relevance (highest first).
        Score is the cosine similarity between query and node embeddings.

    Example:
        >>> results = search_semantic("authentication implementation")
        >>> for node, score in results:
        ...     print(f"{node.type}: {node.content[:50]} (score: {score:.2f})")

    Notes:
        - Nodes without embeddings are excluded from results
        - Results are sorted by similarity score in descending order
        - In production, replace the placeholder embedding with actual embedding service
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(f"Performing semantic search for query: '{query}' (limit={limit})")

        # Start timing for performance measurement
        start_time = time.perf_counter()

        # Generate embedding for the query
        query_embedding = _generate_query_embedding(query)

        # Use the backend's search_similar method for efficient vector search
        results = client.search_similar(query_embedding, limit=limit, min_score=0.0)

        # End timing and log performance
        elapsed_time = time.perf_counter() - start_time

        if elapsed_time > QUERY_PERFORMANCE_THRESHOLD_SECONDS:
            logger.warning(
                f"Semantic search exceeded performance threshold: "
                f"{elapsed_time:.3f}s > {QUERY_PERFORMANCE_THRESHOLD_SECONDS}s "
                f"(query='{query[:50]}...', results={len(results)})"
            )
        else:
            logger.debug(
                f"Semantic search completed in {elapsed_time:.3f}s "
                f"(query='{query[:50]}...', results={len(results)})"
            )

        logger.info(f"Semantic search found {len(results)} results in {elapsed_time:.3f}s")
        return results

    finally:
        if should_disconnect:
            client.disconnect()


def get_relevant_context(
    query: str,
    num_results: int = MAX_CONTEXT_RESULTS,
    min_score: float = DEFAULT_MIN_SCORE,
    client: Optional[GraphitiClient] = None
) -> List[Dict[str, Any]]:
    """
    Get relevant context for a query with rich metadata.

    Performs semantic search and returns results enriched with context metadata
    including source file, capture timestamp, and episode type. This function
    is designed for use in context retrieval where the "where" and "when" of
    knowledge is as important as the content itself.

    Args:
        query: The search query (natural language or keywords)
        num_results: Maximum number of results to return (default: MAX_CONTEXT_RESULTS)
        min_score: Minimum similarity score threshold (default: 0.0).
                   Results below this score are filtered out.
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of dictionaries, each containing:
        - content: The main content of the node
        - score: The similarity score (0.0 to 1.0)
        - type: The node type (e.g., 'decision', 'task', 'discovery')
        - source_file: The file path where knowledge was captured (if available)
        - captured_at: ISO 8601 timestamp when knowledge was captured
        - episode_type: The type of episode that captured this knowledge (if available)

    Example:
        >>> results = get_relevant_context("authentication best practices")
        >>> for item in results:
        ...     print(f"[{item['type']}] {item['content'][:50]}")
        ...     print(f"  Score: {item['score']:.2f}")
        ...     print(f"  Source: {item['source_file']}")
        ...     print(f"  Captured: {item['captured_at']}")

    Notes:
        - Results are sorted by similarity score in descending order
        - Context metadata fields may be None if not present in the node
        - Empty queries return an empty list with no error
    """
    # Handle empty query
    if not query or not query.strip():
        logger.info("Empty query provided, returning empty results")
        return []

    # Start timing for end-to-end performance measurement
    start_time = time.perf_counter()

    # Perform semantic search
    search_results = search_semantic(
        query=query,
        limit=num_results,
        client=client
    )

    # Convert results to context items with metadata
    context_items: List[Dict[str, Any]] = []

    for node, score in search_results:
        # Filter by minimum score
        if score < min_score:
            continue

        # Extract metadata from node
        metadata = node.metadata or {}

        # Format captured_at timestamp as ISO 8601
        captured_at = None
        if node.created_at:
            captured_at = node.created_at.isoformat()

        # Build context item with all metadata
        context_item = {
            "content": node.content,
            "score": score,
            "type": node.type,
            METADATA_SOURCE_FILE: metadata.get(METADATA_SOURCE_FILE),
            METADATA_CAPTURED_AT: captured_at,
            METADATA_EPISODE_TYPE: metadata.get(METADATA_EPISODE_TYPE, node.type),
        }

        context_items.append(context_item)

    # End timing and log performance
    elapsed_time = time.perf_counter() - start_time

    if elapsed_time > QUERY_PERFORMANCE_THRESHOLD_SECONDS:
        logger.warning(
            f"get_relevant_context exceeded performance threshold: "
            f"{elapsed_time:.3f}s > {QUERY_PERFORMANCE_THRESHOLD_SECONDS}s "
            f"(query='{query[:50]}...', results={len(context_items)})"
        )

    logger.info(
        f"get_relevant_context: Found {len(context_items)} results "
        f"for query '{query[:50]}...' in {elapsed_time:.3f}s (min_score={min_score})"
    )

    return context_items


def _get_descendant_nodes(
    scope_node_id: str,
    client: GraphitiClient,
    visited: Optional[Set[str]] = None
) -> Set[str]:
    """
    Recursively get all descendant node IDs under a scope node.

    Traverses the graph following 'contains' edges to find all nodes
    hierarchically contained within the scope node.

    Args:
        scope_node_id: The UUID of the scope/parent node
        client: GraphitiClient instance to use for queries
        visited: Set of already visited node IDs (for cycle detection)

    Returns:
        Set of node UUIDs that are descendants of the scope node
    """
    if visited is None:
        visited = set()

    # Avoid infinite loops in case of cycles
    if scope_node_id in visited:
        return set()

    visited.add(scope_node_id)
    descendants = {scope_node_id}

    # Find all edges where this node is the source with type 'contains'
    edges = client.query_edges(filters={"source_id": scope_node_id, "type": "contains"})

    for edge in edges:
        # Recursively get descendants of each child
        child_descendants = _get_descendant_nodes(edge.target_id, client, visited)
        descendants.update(child_descendants)

    return descendants


def search_scoped(
    scope_node_id: str,
    query: str,
    limit: int = 10,
    client: Optional[GraphitiClient] = None
) -> List[Tuple[Node, float]]:
    """
    Perform semantic search within a hierarchical scope.

    Searches only within nodes that are hierarchically contained under
    the specified scope node. This enables scoped queries like "find tasks
    within this project" or "search decisions in this session".

    Args:
        scope_node_id: The UUID of the scope/parent node to search within
        query: The search query (natural language or keywords)
        limit: Maximum number of results to return (default: 10)
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of (Node, score) tuples, sorted by relevance (highest first).
        Only includes nodes within the specified scope.

    Example:
        >>> # Search for authentication tasks within a specific project
        >>> results = search_scoped(project_id, "authentication")
        >>> for node, score in results:
        ...     print(f"{node.type}: {node.content[:50]} (score: {score:.2f})")

    Notes:
        - Scope is determined by following 'contains' edges recursively
        - The scope node itself is included in the search
        - Nodes without embeddings are excluded from results
        - Results are sorted by similarity score in descending order
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(
            f"Performing scoped search for query: '{query}' "
            f"within scope={scope_node_id} (limit={limit})"
        )

        # Start timing for performance measurement
        start_time = time.perf_counter()

        # Get all descendant node IDs under the scope
        descendant_ids = _get_descendant_nodes(scope_node_id, client)
        logger.info(f"Found {len(descendant_ids)} nodes within scope")

        # Generate embedding for the query
        query_embedding = _generate_query_embedding(query)

        # Use backend's search_similar and filter by scope
        all_results = client.search_similar(query_embedding, limit=limit * 5, min_score=0.0)

        # Filter to only nodes within the scope
        results: List[Tuple[Node, float]] = []
        for node, similarity in all_results:
            if node.uuid in descendant_ids:
                results.append((node, similarity))
                if len(results) >= limit:
                    break

        # End timing and log performance
        elapsed_time = time.perf_counter() - start_time

        if elapsed_time > QUERY_PERFORMANCE_THRESHOLD_SECONDS:
            logger.warning(
                f"Scoped search exceeded performance threshold: "
                f"{elapsed_time:.3f}s > {QUERY_PERFORMANCE_THRESHOLD_SECONDS}s "
                f"(query='{query[:50]}...', scope={scope_node_id}, results={len(results)})"
            )
        else:
            logger.debug(
                f"Scoped search completed in {elapsed_time:.3f}s "
                f"(query='{query[:50]}...', scope={scope_node_id}, results={len(results)})"
            )

        logger.info(f"Scoped search found {len(results)} results in {elapsed_time:.3f}s")
        return results

    finally:
        if should_disconnect:
            client.disconnect()


def traverse(
    node_id: str,
    depth: int = 1,
    client: Optional[GraphitiClient] = None
) -> Dict[str, List[Node]]:
    """
    Traverse the knowledge graph from a starting node up to a specified depth.

    Performs a breadth-first traversal of the graph, following all edges from
    the starting node. Returns nodes organized by their distance (depth level)
    from the starting node. This enables exploration of the local graph structure
    and discovery of multi-hop relationships.

    Args:
        node_id: The UUID of the starting node for traversal
        depth: Maximum depth to traverse (default: 1). Depth of 1 returns direct
               neighbors, depth of 2 includes neighbors of neighbors, etc.
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        Dictionary mapping depth levels (as strings) to lists of nodes at that depth.
        Example: {"0": [start_node], "1": [neighbor1, neighbor2], "2": [...]}

    Example:
        >>> # Get all nodes within 2 hops of a project node
        >>> results = traverse(project_id, depth=2)
        >>> print(f"Direct neighbors: {len(results['1'])}")
        >>> print(f"Second-level neighbors: {len(results.get('2', []))}")

    Notes:
        - The starting node is included at depth 0
        - Uses breadth-first search to ensure minimal depth for each node
        - Prevents cycles by tracking visited nodes
        - Returns empty dict if the starting node doesn't exist
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(f"Traversing graph from node={node_id} with depth={depth}")

        # Check if starting node exists
        start_node = client.get_node(node_id)
        if not start_node:
            logger.warning(f"Starting node not found: {node_id}")
            return {}

        # Initialize result structure
        result: Dict[str, List[Node]] = {str(i): [] for i in range(depth + 1)}
        result["0"] = [start_node]

        # Track visited nodes to prevent cycles
        visited: Set[str] = {node_id}

        # Current level nodes to process
        current_level = [node_id]

        # Traverse level by level (BFS)
        for current_depth in range(1, depth + 1):
            next_level = []

            for current_node_id in current_level:
                # Find all edges from current node (outgoing)
                outgoing_edges = client.query_edges(filters={"source_id": current_node_id})
                for edge in outgoing_edges:
                    target_id = edge.target_id
                    if target_id not in visited:
                        target_node = client.get_node(target_id)
                        if target_node:
                            visited.add(target_id)
                            result[str(current_depth)].append(target_node)
                            next_level.append(target_id)

                # Find all edges to current node (incoming)
                incoming_edges = client.query_edges(filters={"target_id": current_node_id})
                for edge in incoming_edges:
                    source_id = edge.source_id
                    if source_id not in visited:
                        source_node = client.get_node(source_id)
                        if source_node:
                            visited.add(source_id)
                            result[str(current_depth)].append(source_node)
                            next_level.append(source_id)

            current_level = next_level

            # Stop early if no more nodes to explore
            if not current_level:
                break

        total_nodes = sum(len(nodes) for nodes in result.values())
        logger.info(f"Traversal found {total_nodes} nodes across {depth + 1} levels")
        return result

    finally:
        if should_disconnect:
            client.disconnect()


def get_related(
    node_id: str,
    edge_type: Optional[str] = None,
    direction: str = "both",
    client: Optional[GraphitiClient] = None
) -> List[Tuple[Node, Edge]]:
    """
    Get all nodes directly related to a given node.

    Retrieves nodes that are connected to the specified node via edges,
    optionally filtering by edge type and direction. Returns both the related
    nodes and the edges that connect them, enabling analysis of relationship types.

    Args:
        node_id: The UUID of the node to find relations for
        edge_type: Optional edge type filter (e.g., 'contains', 'references').
                   If None, returns all edge types.
        direction: Direction of edges to follow:
                   - "outgoing": Only follow edges from this node to others
                   - "incoming": Only follow edges from others to this node
                   - "both": Follow edges in both directions (default)
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of (Node, Edge) tuples where each tuple contains a related node
        and the edge connecting it to the source node.

    Example:
        >>> # Get all tasks contained in a project
        >>> related = get_related(project_id, edge_type="contains", direction="outgoing")
        >>> for node, edge in related:
        ...     print(f"Task: {node.content} (edge: {edge.type})")

        >>> # Get all nodes referencing a decision
        >>> refs = get_related(decision_id, edge_type="references", direction="incoming")
        >>> print(f"Decision referenced by {len(refs)} nodes")

    Notes:
        - Returns empty list if the node doesn't exist
        - Each result includes both the related node and the connecting edge
        - Direction "both" may include the same node twice if connected by
          edges in both directions
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(
            f"Getting related nodes for node={node_id}, "
            f"edge_type={edge_type}, direction={direction}"
        )

        # Check if node exists
        node = client.get_node(node_id)
        if not node:
            logger.warning(f"Node not found: {node_id}")
            return []

        results: List[Tuple[Node, Edge]] = []

        # Get outgoing edges (this node -> others)
        if direction in ("outgoing", "both"):
            filters = {"source_id": node_id}
            if edge_type:
                filters["type"] = edge_type

            outgoing_edges = client.query_edges(filters=filters)
            for edge in outgoing_edges:
                target_node = client.get_node(edge.target_id)
                if target_node:
                    results.append((target_node, edge))

        # Get incoming edges (others -> this node)
        if direction in ("incoming", "both"):
            filters = {"target_id": node_id}
            if edge_type:
                filters["type"] = edge_type

            incoming_edges = client.query_edges(filters=filters)
            for edge in incoming_edges:
                source_node = client.get_node(edge.source_id)
                if source_node:
                    results.append((source_node, edge))

        logger.info(f"Found {len(results)} related nodes")
        return results

    finally:
        if should_disconnect:
            client.disconnect()


def query_temporal(
    start: datetime,
    end: datetime,
    include_edges: bool = False,
    client: Optional[GraphitiClient] = None
) -> Dict[str, List]:
    """
    Query nodes and edges created or updated within a time range.

    Retrieves all nodes (and optionally edges) that were created or updated
    between the specified start and end timestamps. This enables temporal
    analysis, historical queries, and activity tracking over time periods.

    Args:
        start: Start of the time range (inclusive)
        end: End of the time range (inclusive)
        include_edges: If True, also returns edges within the time range (default: False)
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        Dictionary with keys:
        - "nodes": List of nodes created or updated within the time range
        - "edges": List of edges created or updated within the time range (if include_edges=True)

    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(days=7)
        >>> results = query_temporal(start, end)
        >>> print(f"Found {len(results['nodes'])} nodes in the last week")

        >>> # Include edges in the results
        >>> results = query_temporal(start, end, include_edges=True)
        >>> print(f"Found {len(results['nodes'])} nodes and {len(results['edges'])} edges")

    Notes:
        - A node/edge is included if either created_at OR updated_at falls within the range
        - Time range is inclusive on both ends
        - Results are sorted by created_at timestamp (newest first)
        - Returns empty lists if no nodes/edges exist in the time range
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(f"Querying temporal range: {start} to {end} (include_edges={include_edges})")

        # Use client's query_nodes_by_time method
        matching_nodes = client.query_nodes_by_time(start, end, node_type=None)

        # Sort by created_at (newest first)
        matching_nodes.sort(key=lambda n: n.created_at, reverse=True)

        logger.info(f"Found {len(matching_nodes)} nodes in temporal range")

        # Build result dictionary
        result: Dict[str, List] = {
            "nodes": matching_nodes,
            "edges": []
        }

        # Optionally include edges - query all edges and filter by time
        if include_edges:
            all_edges = client.query_edges(limit=10000)
            matching_edges: List[Edge] = []

            for edge in all_edges:
                # Check if edge falls within the time range (created or updated)
                if (start <= edge.created_at <= end) or (start <= edge.updated_at <= end):
                    matching_edges.append(edge)

            # Sort by created_at (newest first)
            matching_edges.sort(key=lambda e: e.created_at, reverse=True)

            result["edges"] = matching_edges
            logger.info(f"Found {len(matching_edges)} edges in temporal range")

        return result

    finally:
        if should_disconnect:
            client.disconnect()


def query_temporal_nodes(
    start: datetime,
    end: datetime,
    node_type: Optional[str] = None,
    client: Optional[GraphitiClient] = None
) -> List[Node]:
    """
    Query nodes within a time range, optionally filtered by node type.

    A convenience function that retrieves only nodes (not edges) within a
    time range, with optional filtering by node type. Useful for analyzing
    specific types of activities over time.

    Args:
        start: Start of the time range (inclusive)
        end: End of the time range (inclusive)
        node_type: Optional node type filter (e.g., 'decision', 'task', 'session').
                   If None, returns all node types.
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of nodes created or updated within the time range, sorted by
        created_at timestamp (newest first).

    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(hours=24)
        >>>
        >>> # Get all decisions made in the last 24 hours
        >>> decisions = query_temporal_nodes(start, end, node_type="decision")
        >>> print(f"Made {len(decisions)} decisions today")
        >>>
        >>> # Get all activity in the last hour
        >>> recent = query_temporal_nodes(
        ...     datetime.now() - timedelta(hours=1),
        ...     datetime.now()
        ... )

    Notes:
        - A node is included if either created_at OR updated_at falls within the range
        - Time range is inclusive on both ends
        - Results are sorted by created_at timestamp (newest first)
        - Returns empty list if no matching nodes exist
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(
            f"Querying temporal nodes: {start} to {end}, "
            f"node_type={node_type}"
        )

        # Use client's query_nodes_by_time method
        matching_nodes = client.query_nodes_by_time(start, end, node_type=node_type)

        # Sort by created_at (newest first)
        matching_nodes.sort(key=lambda n: n.created_at, reverse=True)

        logger.info(f"Found {len(matching_nodes)} nodes in temporal range")
        return matching_nodes

    finally:
        if should_disconnect:
            client.disconnect()
