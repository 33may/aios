"""
Graph traversal and linking tools for the knowledge graph.

Supports optimized traversal for Neo4j backend using native Cypher queries,
and creating edges between existing nodes.
"""

from typing import Any, Dict, List, Optional
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Edge
from apps.backend.integrations.graphiti.queries import traverse, get_related
from apps.backend.integrations.graphiti.config import BackendType
from apps.backend.integrations.graphiti.schema import EdgeType

logger = logging.getLogger(__name__)

# Valid edge types for link_nodes
VALID_EDGE_TYPES = [e.value for e in EdgeType]


def _truncate_content(content: str, max_length: int = 200) -> str:
    """Truncate content to max length."""
    return content[:max_length] if len(content) > max_length else content


async def traverse_related(
    client: GraphitiClient,
    node_id: str,
    depth: int = 1,
    edge_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Explore relationships from a node in the knowledge graph.

    Uses native Neo4j traversal when available for optimal performance.

    Args:
        client: The GraphitiClient instance
        node_id: The starting node ID
        depth: How many hops to traverse (default 1)
        edge_types: Optional filter for edge types (e.g., ["contains", "references"])

    Returns:
        Dictionary with related nodes organized by depth
    """
    logger.info(f"traverse_related: node_id={node_id}, depth={depth}, edge_types={edge_types}")

    # Get the starting node to verify it exists
    start_node = client.get_node(node_id)
    if not start_node:
        return {
            "error": f"Node not found: {node_id}",
            "success": False,
        }

    # Check if using Neo4j backend for optimized traversal
    if client.config.backend == BackendType.NEO4J and hasattr(client._backend, 'traverse_from_node'):
        return await _traverse_neo4j(client, node_id, start_node, depth, edge_types)

    # Fall back to generic traversal for other backends
    return await _traverse_generic(client, node_id, start_node, depth, edge_types)


async def _traverse_neo4j(
    client: GraphitiClient,
    node_id: str,
    start_node: Any,
    depth: int,
    edge_types: Optional[List[str]],
) -> Dict[str, Any]:
    """Use Neo4j native traversal for optimal performance."""
    logger.info(f"Using Neo4j native traversal for node {node_id}")

    # Use Neo4j backend's native traversal
    traversal_results = client._backend.traverse_from_node(
        start_uuid=node_id,
        edge_types=edge_types,
        max_depth=depth,
        limit=100,
    )

    # Organize results by depth
    nodes_by_depth = {"0": [{
        "id": start_node.uuid,
        "type": start_node.type,
        "content": _truncate_content(start_node.content),
        "created_at": start_node.created_at.isoformat(),
    }]}

    relationships = []
    for item in traversal_results:
        node = item["node"]
        depth_level = str(item["depth"])

        if depth_level not in nodes_by_depth:
            nodes_by_depth[depth_level] = []

        nodes_by_depth[depth_level].append({
            "id": node.uuid,
            "type": node.type,
            "content": _truncate_content(node.content),
            "created_at": node.created_at.isoformat(),
        })

        # For depth 1, include in relationships
        if item["depth"] == 1:
            path = item.get("path", [])
            edge_type = path[0] if path else "unknown"
            relationships.append({
                "node": {
                    "id": node.uuid,
                    "type": node.type,
                    "content": _truncate_content(node.content),
                },
                "edge": {
                    "type": edge_type.lower(),
                    "direction": "connected",  # Neo4j traversal is bidirectional
                },
            })

    return {
        "start_node": {
            "id": start_node.uuid,
            "type": start_node.type,
            "content": _truncate_content(start_node.content),
        },
        "nodes_by_depth": nodes_by_depth,
        "direct_relationships": relationships,
        "traversal_depth": depth,
        "backend": "neo4j",
        "success": True,
    }


async def _traverse_generic(
    client: GraphitiClient,
    node_id: str,
    start_node: Any,
    depth: int,
    edge_types: Optional[List[str]],
) -> Dict[str, Any]:
    """Generic traversal using standard client methods."""
    # Perform traversal
    traversal_result = traverse(
        node_id=node_id,
        depth=depth,
        client=client,
    )

    # Format results
    nodes_by_depth = {}
    for depth_level, nodes in traversal_result.items():
        nodes_by_depth[depth_level] = []
        for node in nodes:
            nodes_by_depth[depth_level].append({
                "id": node.uuid,
                "type": node.type,
                "content": _truncate_content(node.content),
                "created_at": node.created_at.isoformat(),
            })

    # Get direct relationships with edge info
    direct_relations = get_related(
        node_id=node_id,
        edge_type=edge_types[0] if edge_types and len(edge_types) == 1 else None,
        direction="both",
        client=client,
    )

    relationships = []
    for related_node, edge in direct_relations:
        # Filter by edge types if specified
        if edge_types and edge.type not in edge_types:
            continue

        relationships.append({
            "node": {
                "id": related_node.uuid,
                "type": related_node.type,
                "content": _truncate_content(related_node.content),
            },
            "edge": {
                "type": edge.type,
                "direction": "outgoing" if edge.source_id == node_id else "incoming",
            },
        })

    return {
        "start_node": {
            "id": start_node.uuid,
            "type": start_node.type,
            "content": _truncate_content(start_node.content),
        },
        "nodes_by_depth": nodes_by_depth,
        "direct_relationships": relationships,
        "traversal_depth": depth,
        "success": True,
    }


async def link_nodes(
    client: GraphitiClient,
    source_id: str,
    target_id: str,
    edge_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an edge between two existing nodes.

    Use this to establish relationships in reasoning chains:
    - thought --led_to--> decision
    - discovery --supports--> decision
    - constraint --constrained_by--> decision
    - problem --fixed_by--> fix
    - thought --refined_by--> thought

    Args:
        client: The GraphitiClient instance
        source_id: UUID of the source node
        target_id: UUID of the target node
        edge_type: Type of edge (led_to, supports, contradicts, refined_by,
                   constrained_by, fixed_by, contains, references, related_to, etc.)
        metadata: Optional additional properties for the edge

    Returns:
        Dictionary with the created edge ID and details
    """
    logger.info(f"link_nodes: {source_id} --{edge_type}--> {target_id}")

    # Validate edge type
    if edge_type not in VALID_EDGE_TYPES:
        return {
            "success": False,
            "error": f"Invalid edge type: {edge_type}. Valid types: {VALID_EDGE_TYPES}",
        }

    # Validate source node exists
    source_node = client.get_node(source_id)
    if not source_node:
        return {
            "success": False,
            "error": f"Source node not found: {source_id}",
        }

    # Validate target node exists
    target_node = client.get_node(target_id)
    if not target_node:
        return {
            "success": False,
            "error": f"Target node not found: {target_id}",
        }

    # Create the edge
    edge = Edge(
        type=edge_type,
        source_id=source_id,
        target_id=target_id,
        metadata=metadata or {},
    )

    edge_id = client.add_edge(edge)
    logger.info(f"Created edge: {edge_id}")

    return {
        "success": True,
        "edge_id": edge_id,
        "edge_type": edge_type,
        "source": {
            "id": source_node.uuid,
            "type": source_node.type,
            "content": _truncate_content(source_node.content),
        },
        "target": {
            "id": target_node.uuid,
            "type": target_node.type,
            "content": _truncate_content(target_node.content),
        },
        "created_at": edge.created_at.isoformat(),
    }
