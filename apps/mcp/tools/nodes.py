"""
Generic node management tools for the knowledge graph.

Supports operations on any node type (project, task, thought, decision, etc.)
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Edge

logger = logging.getLogger(__name__)


def _collect_children_recursive(
    client: GraphitiClient,
    node_id: str,
    collected: List[str],
    visited: set,
) -> None:
    """
    Recursively collect all child node IDs following CONTAINS edges.

    Args:
        client: The GraphitiClient instance
        node_id: Current node to find children of
        collected: List to append child IDs to
        visited: Set of already visited node IDs (to prevent cycles)
    """
    if node_id in visited:
        return
    visited.add(node_id)

    # Query edges where this node is the source of a CONTAINS relationship
    edges = client.query_edges(filters={"type": "contains", "source_id": node_id}, limit=1000)

    for edge in edges:
        child_id = edge.target_id
        if child_id not in visited:
            collected.append(child_id)
            # Recurse to find children of this child
            _collect_children_recursive(client, child_id, collected, visited)


async def delete_node(
    client: GraphitiClient,
    node_id: str,
    recursive: bool = False,
) -> Dict[str, Any]:
    """
    Delete a node from the knowledge graph.

    Works on any node type (project, task, thought, decision, discovery, etc.)

    Args:
        client: The GraphitiClient instance
        node_id: The ID of the node to delete
        recursive: If True, delete all child nodes (following CONTAINS edges)

    Returns:
        Dictionary with success status and deleted info
    """
    logger.info(f"delete_node: node_id={node_id}, recursive={recursive}")

    # Get the node to verify it exists and get info
    node = client.get_node(node_id)
    if not node:
        logger.warning(f"Node not found: {node_id}")
        return {
            "success": False,
            "error": f"Node not found: {node_id}",
        }

    node_type = node.type
    node_content = node.content[:100] if node.content else ""
    node_name = ""
    if node.metadata:
        node_name = node.metadata.get("name") or node.metadata.get("subject") or ""

    deleted_ids = []
    deleted_by_type: Dict[str, int] = {}

    # If recursive, collect and delete all children first
    if recursive:
        children_to_delete: List[str] = []
        _collect_children_recursive(client, node_id, children_to_delete, set())

        # Delete children in reverse order (deepest first)
        for child_id in reversed(children_to_delete):
            child_node = client.get_node(child_id)
            if child_node:
                child_type = child_node.type
                if client.delete_node(child_id):
                    deleted_ids.append(child_id)
                    deleted_by_type[child_type] = deleted_by_type.get(child_type, 0) + 1
                    logger.info(f"Deleted child node: {child_id} ({child_type})")

    # Delete the main node
    if client.delete_node(node_id):
        deleted_ids.append(node_id)
        deleted_by_type[node_type] = deleted_by_type.get(node_type, 0) + 1
        logger.info(f"Deleted node: {node_id} ({node_type})")

        return {
            "success": True,
            "node_id": node_id,
            "node_type": node_type,
            "node_name": node_name,
            "node_content_preview": node_content,
            "recursive": recursive,
            "deleted_count": len(deleted_ids),
            "deleted_by_type": deleted_by_type,
            "deleted_ids": deleted_ids,
        }
    else:
        return {
            "success": False,
            "error": f"Failed to delete node: {node_id}",
            "deleted_count": len(deleted_ids),
            "deleted_by_type": deleted_by_type,
            "deleted_ids": deleted_ids,
        }


async def move_node(
    client: GraphitiClient,
    node_id: str,
    new_parent_id: str,
) -> Dict[str, Any]:
    """
    Move a node under a different parent by updating CONTAINS edges.

    Works on any node type (task, thought, decision, discovery, etc.)

    Args:
        client: The GraphitiClient instance
        node_id: The ID of the node to move
        new_parent_id: The ID of the new parent node

    Returns:
        Dictionary with success status and move info
    """
    logger.info(f"move_node: node_id={node_id}, new_parent_id={new_parent_id}")

    # Get the node to move
    node = client.get_node(node_id)
    if not node:
        return {
            "success": False,
            "error": f"Node not found: {node_id}",
        }

    # Get the new parent node
    new_parent = client.get_node(new_parent_id)
    if not new_parent:
        return {
            "success": False,
            "error": f"New parent not found: {new_parent_id}",
        }

    node_type = node.type
    node_name = ""
    if node.metadata:
        node_name = node.metadata.get("name") or node.metadata.get("subject") or node.content[:50]

    # Find and remove old CONTAINS edges pointing to this node
    old_parent_id = None
    all_edges = client.query_edges(filters={"type": "contains"}, limit=1000)
    for edge in all_edges:
        if edge.target_id == node_id:
            old_parent_id = edge.source_id
            client.delete_edge(edge.uuid)
            logger.info(f"Removed old CONTAINS edge from {edge.source_id}")

    # Update parent_id in node metadata if it exists
    if node.metadata is None:
        node.metadata = {}
    node.metadata["parent_id"] = new_parent_id

    # If new parent has a project_id, inherit it
    if new_parent.metadata and new_parent.metadata.get("project_id"):
        node.metadata["project_id"] = new_parent.metadata.get("project_id")
    elif new_parent.type == "project":
        node.metadata["project_id"] = new_parent_id

    node.updated_at = datetime.utcnow()

    # Create new CONTAINS edge from new parent
    edge = Edge(
        type="contains",
        source_id=new_parent_id,
        target_id=node_id,
    )
    client.add_edge(edge)
    logger.info(f"Created CONTAINS edge from {new_parent_id} to {node_id}")

    return {
        "success": True,
        "node_id": node_id,
        "node_type": node_type,
        "node_name": node_name,
        "old_parent_id": old_parent_id,
        "new_parent_id": new_parent_id,
        "new_parent_type": new_parent.type,
        "updated_at": node.updated_at.isoformat(),
    }
