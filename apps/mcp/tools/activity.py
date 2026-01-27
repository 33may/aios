"""
Activity and discovery tools for the knowledge graph.

Provides context-aware reasoning tools that automatically link to the current
focus node, creating traversable reasoning trees in the graph.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import query_temporal
from apps.mcp.tools.context import (
    _get_focus,
    _set_focus,
    _get_reasoning_context,
    _update_reasoning_context,
)

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
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a learning or insight to the knowledge graph.

    When use_context=True, the discovery will:
    - Link to the current focus node via 'led_to' edge (something led to this discovery)
    - Become the new focus for subsequent nodes

    Args:
        client: The GraphitiClient instance
        content: What was learned or discovered
        context: Where/how it was discovered (optional)
        tags: Optional tags for categorization
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created discovery ID and parent link info
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

    result = {
        "discovery_id": discovery_id,
        "content": content[:100],
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
            # Create edge: parent --led_to--> discovery
            edge = Edge(
                type="led_to",
                source_id=parent[0],
                target_id=discovery_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created led_to edge from {parent[0]} to discovery: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["edge_id"] = edge_id

        # Set this discovery as the new focus
        _set_focus(client, discovery_id, "discovery")
        result["is_focus"] = True

    return result


async def add_thought(
    client: GraphitiClient,
    content: str,
    context: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a reasoning step or observation to the knowledge graph.

    Use this to capture chain-of-thought reasoning, analysis of options,
    observations during exploration, or any intermediate thinking.

    When use_context=True, the thought will:
    - Link to the current focus node via 'spawned' edge
    - Become the new focus for subsequent nodes

    This creates traversable reasoning trees:
    Task -> Thought -> Thought -> Discovery -> Decision

    Args:
        client: The GraphitiClient instance
        content: The thought, observation, or reasoning step
        context: What prompted this thought (optional)
        tags: Optional tags (e.g., ["reasoning", "option-analysis"])
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created thought ID and parent link info
    """
    logger.info(f"add_thought: content='{content[:50]}...'")

    node = Node(
        type="thought",
        content=content,
        metadata={
            "context": context,
            "tags": tags or [],
            "project_id": project_id,
        },
    )

    thought_id = client.add_node(node)
    logger.info(f"Created thought node: {thought_id}")

    result = {
        "thought_id": thought_id,
        "content": content[:100],
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
            # Create edge: parent --spawned--> thought
            edge = Edge(
                type="spawned",
                source_id=parent[0],
                target_id=thought_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created spawned edge from {parent[0]} to thought: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["edge_id"] = edge_id

        # Set this thought as the new focus
        _set_focus(client, thought_id, "thought")
        result["is_focus"] = True

    return result


async def add_problem(
    client: GraphitiClient,
    content: str,
    context: Optional[str] = None,
    severity: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a problem or issue encountered during work.

    Use this to capture bugs, errors, blockers, or any issues
    that need to be resolved.

    When use_context=True, the problem will:
    - Link to the current focus node via 'led_to' edge (something led to finding this problem)
    - Become the new focus for subsequent nodes
    - Be tracked as active_problem_id (auto-linked when add_fix is called)

    Args:
        client: The GraphitiClient instance
        content: Description of the problem
        context: Where/when the problem was encountered (optional)
        severity: Optional severity level (low, medium, high, critical)
        tags: Optional tags (e.g., ["bug", "blocker", "debugging"])
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created problem ID and parent link info
    """
    logger.info(f"add_problem: content='{content[:50]}...'")

    node = Node(
        type="problem",
        content=content,
        metadata={
            "context": context,
            "severity": severity,
            "status": "open",
            "tags": tags or [],
            "project_id": project_id,
        },
    )

    problem_id = client.add_node(node)
    logger.info(f"Created problem node: {problem_id}")

    result = {
        "problem_id": problem_id,
        "content": content[:100],
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
            # Create edge: parent --led_to--> problem (something led us to find this)
            edge = Edge(
                type="led_to",
                source_id=parent[0],
                target_id=problem_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created led_to edge from {parent[0]} to problem: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["edge_id"] = edge_id

        # Set as both focus and active problem
        _set_focus(client, problem_id, "problem")
        _update_reasoning_context(client, {"active_problem_id": problem_id})
        result["is_focus"] = True
        result["is_active_problem"] = True

    return result


async def add_fix(
    client: GraphitiClient,
    content: str,
    problem_id: Optional[str] = None,
    context: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a fix or solution to a problem.

    Use this to capture how a problem was resolved.

    When use_context=True, the fix will:
    - Link to the current focus node via 'spawned' edge (if different from problem)
    - Auto-link to active_problem_id if no explicit problem_id provided
    - Become the new focus for subsequent nodes
    - Clear active_problem_id after linking

    Args:
        client: The GraphitiClient instance
        content: Description of the fix/solution
        problem_id: Optional ID of the problem this fixes (creates fixed_by edge)
        context: Additional context about the fix (optional)
        tags: Optional tags (e.g., ["workaround", "permanent-fix"])
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created fix ID and edge info
    """
    logger.info(f"add_fix: content='{content[:50]}...'")

    node = Node(
        type="fix",
        content=content,
        metadata={
            "context": context,
            "problem_id": problem_id,
            "tags": tags or [],
            "project_id": project_id,
        },
    )

    fix_id = client.add_node(node)
    logger.info(f"Created fix node: {fix_id}")

    result = {
        "fix_id": fix_id,
        "content": content[:100],
        "created_at": node.created_at.isoformat(),
        "success": True,
    }

    # Determine effective problem_id
    effective_problem = problem_id
    if use_context and not effective_problem:
        ctx = _get_reasoning_context(client)
        effective_problem = ctx.get("active_problem_id")

    # Create fixed_by edge if we have a problem
    if effective_problem:
        edge = Edge(
            type="fixed_by",
            source_id=effective_problem,
            target_id=fix_id,
        )
        edge_id = client.add_edge(edge)
        logger.info(f"Created fixed_by edge: {edge_id}")
        result["fixed_by_edge_id"] = edge_id
        result["linked_problem_id"] = effective_problem

        # Update problem status to resolved
        problem_node = client.get_node(effective_problem)
        if problem_node:
            metadata = problem_node.metadata or {}
            metadata["status"] = "resolved"
            client.update_node(effective_problem, {"metadata": metadata})

        # Clear active problem
        if use_context:
            _update_reasoning_context(client, {"active_problem_id": None})
            result["active_problem_cleared"] = True

    if use_context:
        # Get parent (explicit or from focus)
        parent = None
        if parent_id:
            parent_node = client.get_node(parent_id)
            if parent_node:
                parent = (parent_id, parent_node.type)
        else:
            parent = _get_focus(client)

        # Create spawned edge to parent if different from problem
        if parent and parent[0] != effective_problem:
            edge = Edge(
                type="spawned",
                source_id=parent[0],
                target_id=fix_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created spawned edge from {parent[0]} to fix: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["spawned_edge_id"] = edge_id

        # Set this fix as the new focus
        _set_focus(client, fix_id, "fix")
        result["is_focus"] = True

    return result
