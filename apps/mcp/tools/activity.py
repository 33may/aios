"""
Activity and discovery tools for the knowledge graph.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node
from apps.backend.integrations.graphiti.queries import query_temporal

logger = logging.getLogger(__name__)


async def get_recent_activity(
    client: GraphitiClient,
    hours: int = 24,
    types: Optional[List[str]] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Get recent activity across all node types.

    Args:
        client: The GraphitiClient instance
        hours: How far back to look (default 24 hours)
        types: Optional list of node types to filter (e.g., ["decision", "task"])
        limit: Maximum number of results

    Returns:
        Dictionary with activity array
    """
    logger.info(f"get_recent_activity: hours={hours}, types={types}")

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    # Query all nodes in time range
    result = query_temporal(
        start=start,
        end=now,
        include_edges=False,
        client=client,
    )

    nodes = result.get("nodes", [])

    # Filter by types if specified
    if types:
        nodes = [n for n in nodes if n.type in types]

    # Sort by created_at (newest first)
    nodes.sort(key=lambda n: n.created_at, reverse=True)

    # Format activity
    activity = []
    for n in nodes[:limit]:
        metadata = n.metadata or {}
        activity.append({
            "id": n.uuid,
            "type": n.type,
            "content": n.content[:500] if len(n.content) > 500 else n.content,
            "timestamp": n.created_at.isoformat(),
            "title": metadata.get("title") or metadata.get("subject"),
        })

    return {
        "activity": activity,
        "count": len(activity),
        "period_hours": hours,
        "types_filter": types,
    }


async def add_discovery(
    client: GraphitiClient,
    content: str,
    context: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a learning or insight to the knowledge graph.

    Args:
        client: The GraphitiClient instance
        content: What was learned or discovered
        context: Where/how it was discovered (optional)
        tags: Optional tags for categorization
        project_id: Optional project ID to associate with

    Returns:
        Dictionary with the created discovery ID
    """
    logger.info(f"add_discovery: content='{content[:50]}...'")

    # Create the discovery node
    node = Node(
        type="discovery",
        content=content,
        metadata={
            "context": context,
            "tags": tags or [],
            "project_id": project_id,
        },
    )

    # Add to graph
    discovery_id = client.add_node(node)

    logger.info(f"Created discovery node: {discovery_id}")

    return {
        "discovery_id": discovery_id,
        "content": content[:100],
        "created_at": node.created_at.isoformat(),
        "success": True,
    }
