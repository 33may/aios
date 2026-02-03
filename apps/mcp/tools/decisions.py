"""
Decision management tools for the knowledge graph.

Provides context-aware decision recording that automatically links to
collected constraints and the current focus node.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.embedder import embed_text
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import query_temporal_nodes
from apps.mcp.tools.context import (
    _get_focus,
    _set_focus,
    _get_reasoning_context,
    _update_reasoning_context,
)

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
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a new decision to the knowledge graph.

    When use_context=True, the decision will:
    - Link to the current focus node via 'led_to' edge (reasoning led to decision)
    - Auto-link to all collected constraints via 'constrained_by' edges
    - Clear the constraints_collected list after linking
    - Become the new focus for subsequent nodes

    This creates rich reasoning chains like:
    Thought -> Thought -> Constraint -> Decision

    Args:
        client: The GraphitiClient instance
        title: Short title for the decision
        rationale: Why this choice was made
        alternatives: What other options were considered
        context: What prompted this decision
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus, constraints, and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created decision ID and link info
    """
    logger.info(f"record_decision: title='{title}'")

    # Create the decision node
    decision_content = f"{title}\n\n{rationale}"
    node = Node(
        type="decision",
        content=decision_content,
        embedding=embed_text(decision_content),
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

    result = {
        "decision_id": decision_id,
        "title": title,
        "created_at": node.created_at.isoformat(),
        "success": True,
    }

    if use_context:
        # Get parent (explicit or from focus)
        parent = None
        if parent_id:
            parent_node = client.get_node(parent_id)
            if parent_node:
                parent = (parent_id, parent_node.type)
        else:
            parent = _get_focus(client)

        if parent:
            # Create edge: parent --led_to--> decision
            edge = Edge(
                type="led_to",
                source_id=parent[0],
                target_id=decision_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created led_to edge from {parent[0]} to decision: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["led_to_edge_id"] = edge_id

        # Link all collected constraints
        ctx = _get_reasoning_context(client)
        constraints = ctx.get("constraints_collected", [])
        constraint_edges = []

        for constraint_id in constraints:
            # Verify constraint exists
            constraint_node = client.get_node(constraint_id)
            if constraint_node:
                # Create edge: decision --constrained_by--> constraint
                edge = Edge(
                    type="constrained_by",
                    source_id=decision_id,
                    target_id=constraint_id,
                )
                edge_id = client.add_edge(edge)
                constraint_edges.append({
                    "constraint_id": constraint_id,
                    "edge_id": edge_id,
                })
                logger.info(f"Created constrained_by edge to constraint {constraint_id}: {edge_id}")

        if constraint_edges:
            result["constrained_by_edges"] = constraint_edges
            result["constraints_linked"] = len(constraint_edges)

        # Clear collected constraints
        _update_reasoning_context(client, {"constraints_collected": []})

        # Set decision as the new focus
        _set_focus(client, decision_id, "decision")
        result["is_focus"] = True

    return result
