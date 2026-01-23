"""
Decision management tools for the knowledge graph.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import query_temporal_nodes

logger = logging.getLogger(__name__)


async def get_decisions(
    client: GraphitiClient,
    project_id: Optional[str] = None,
    days: int = 90,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieve architectural/design decisions from the knowledge graph.

    Args:
        client: The GraphitiClient instance
        project_id: Optional project ID for scoping
        days: How far back to look (default 90 days)
        limit: Maximum number of decisions to return

    Returns:
        Dictionary with decisions array
    """
    logger.info(f"get_decisions: project_id={project_id}, days={days}, limit={limit}")

    now = datetime.utcnow()
    start = now - timedelta(days=days)

    decisions = query_temporal_nodes(
        start=start,
        end=now,
        node_type="decision",
        client=client,
    )

    # Filter by project if specified
    if project_id:
        decisions = [
            d for d in decisions
            if d.metadata and d.metadata.get("project_id") == project_id
        ]

    # Format decisions
    formatted = []
    for d in decisions[:limit]:
        metadata = d.metadata or {}
        formatted.append({
            "id": d.uuid,
            "title": metadata.get("title", d.content[:100]),
            "rationale": metadata.get("rationale", d.content),
            "alternatives": metadata.get("alternatives", []),
            "date": d.created_at.isoformat(),
            "context": metadata.get("context"),
            "related_tasks": metadata.get("related_tasks", []),
        })

    return {
        "decisions": formatted,
        "count": len(formatted),
        "period_days": days,
    }


async def record_decision(
    client: GraphitiClient,
    title: str,
    rationale: str,
    alternatives: Optional[List[str]] = None,
    context: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a new decision to the knowledge graph.

    Args:
        client: The GraphitiClient instance
        title: Short title for the decision
        rationale: Why this choice was made
        alternatives: What other options were considered
        context: What prompted this decision
        project_id: Optional project ID to associate with

    Returns:
        Dictionary with the created decision ID
    """
    logger.info(f"record_decision: title='{title}'")

    # Create the decision node
    node = Node(
        type="decision",
        content=f"{title}\n\n{rationale}",
        metadata={
            "title": title,
            "rationale": rationale,
            "alternatives": alternatives or [],
            "context": context,
            "project_id": project_id,
        },
    )

    # Add to graph
    decision_id = client.add_node(node)

    logger.info(f"Created decision node: {decision_id}")

    return {
        "decision_id": decision_id,
        "title": title,
        "created_at": node.created_at.isoformat(),
        "success": True,
    }
