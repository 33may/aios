"""
Session initialization tool for manager mode.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.queries import query_temporal_nodes, get_relevant_context

logger = logging.getLogger(__name__)


async def initialize_session(
    client: GraphitiClient,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize a manager session by gathering comprehensive project context.

    This tool performs a deep exploration of the knowledge graph to build
    context for Claude to act as a project manager. It retrieves:
    - Recent decisions and their rationale
    - Active and blocked tasks
    - Recent discoveries and learnings
    - Project history and patterns

    Args:
        client: The GraphitiClient instance
        project_id: Optional project ID to scope the initialization

    Returns:
        Comprehensive session context for manager mode
    """
    logger.info(f"initialize_session: project_id={project_id}")

    now = datetime.now(timezone.utc)

    # Gather context from multiple time windows
    context = {
        "initialized_at": now.isoformat(),
        "project_id": project_id,
        "summary": "",
        "recent_decisions": [],
        "active_tasks": [],
        "blocked_tasks": [],
        "recent_discoveries": [],
        "recent_activity_summary": {},
        "suggested_focus_areas": [],
        "open_questions": [],
    }

    # 1. Get recent decisions (last 30 days for active context)
    decisions_start = now - timedelta(days=30)
    decision_nodes = query_temporal_nodes(
        start=decisions_start,
        end=now,
        node_type="decision",
        client=client,
    )

    for node in decision_nodes[:10]:  # Top 10 recent decisions
        metadata = node.metadata or {}
        context["recent_decisions"].append({
            "id": node.uuid,
            "title": metadata.get("title", node.content[:50]),
            "rationale": metadata.get("rationale", ""),
            "alternatives": metadata.get("alternatives", []),
            "date": node.created_at.isoformat(),
            "content": node.content[:300] if len(node.content) > 300 else node.content,
        })

    # 2. Get active tasks (last 60 days)
    tasks_start = now - timedelta(days=60)
    task_nodes = query_temporal_nodes(
        start=tasks_start,
        end=now,
        node_type="task",
        client=client,
    )

    for node in task_nodes:
        metadata = node.metadata or {}
        status = metadata.get("status", "pending")

        task_info = {
            "id": node.uuid,
            "subject": metadata.get("subject", node.content[:50]),
            "description": node.content[:200] if len(node.content) > 200 else node.content,
            "status": status,
            "created_at": node.created_at.isoformat(),
            "blocked_by": metadata.get("blocked_by", []),
        }

        if status == "blocked":
            context["blocked_tasks"].append(task_info)
        elif status in ("pending", "in_progress"):
            context["active_tasks"].append(task_info)

    # Limit to most relevant
    context["active_tasks"] = context["active_tasks"][:15]
    context["blocked_tasks"] = context["blocked_tasks"][:5]

    # 3. Get recent discoveries (last 14 days)
    discoveries_start = now - timedelta(days=14)
    discovery_nodes = query_temporal_nodes(
        start=discoveries_start,
        end=now,
        node_type="discovery",
        client=client,
    )

    for node in discovery_nodes[:10]:
        metadata = node.metadata or {}
        context["recent_discoveries"].append({
            "id": node.uuid,
            "content": node.content[:300] if len(node.content) > 300 else node.content,
            "context": metadata.get("context", ""),
            "tags": metadata.get("tags", []),
            "date": node.created_at.isoformat(),
        })

    # 4. Activity summary (last 48 hours)
    activity_start = now - timedelta(hours=48)
    all_recent = query_temporal_nodes(
        start=activity_start,
        end=now,
        client=client,
    )

    activity_by_type = {}
    for node in all_recent:
        node_type = node.type
        if node_type not in activity_by_type:
            activity_by_type[node_type] = 0
        activity_by_type[node_type] += 1

    context["recent_activity_summary"] = {
        "period_hours": 48,
        "counts_by_type": activity_by_type,
        "total_items": len(all_recent),
    }

    # 5. Generate suggested focus areas based on context
    focus_areas = []

    if context["blocked_tasks"]:
        focus_areas.append({
            "area": "Unblock tasks",
            "reason": f"{len(context['blocked_tasks'])} tasks are currently blocked",
            "items": [t["subject"] for t in context["blocked_tasks"][:3]],
        })

    if context["active_tasks"]:
        in_progress = [t for t in context["active_tasks"] if t["status"] == "in_progress"]
        if in_progress:
            focus_areas.append({
                "area": "Continue in-progress work",
                "reason": f"{len(in_progress)} tasks are in progress",
                "items": [t["subject"] for t in in_progress[:3]],
            })

    if context["recent_decisions"]:
        focus_areas.append({
            "area": "Review recent decisions",
            "reason": "Ensure alignment with recent architectural choices",
            "items": [d["title"] for d in context["recent_decisions"][:3]],
        })

    context["suggested_focus_areas"] = focus_areas

    # 6. Generate summary
    summary_parts = []

    if context["recent_decisions"]:
        summary_parts.append(f"{len(context['recent_decisions'])} recent decisions")

    if context["active_tasks"]:
        summary_parts.append(f"{len(context['active_tasks'])} active tasks")

    if context["blocked_tasks"]:
        summary_parts.append(f"{len(context['blocked_tasks'])} blocked tasks")

    if context["recent_discoveries"]:
        summary_parts.append(f"{len(context['recent_discoveries'])} recent discoveries")

    context["summary"] = f"Session initialized with: {', '.join(summary_parts) if summary_parts else 'empty knowledge graph'}"

    # 7. Add manager mode instructions
    context["manager_instructions"] = """
You are now in MANAGER MODE. You have access to the project's knowledge graph.

Your role:
1. Track decisions - Record important choices with rationale using record_decision
2. Manage tasks - Track work items, update status, identify blockers
3. Preserve discoveries - Capture learnings and insights with add_discovery
4. Provide continuity - Reference past decisions when relevant
5. Ask clarifying questions - Understand context before diving into implementation

When the user asks to work on something:
1. First search for related past decisions/context
2. Remind them of relevant history if applicable
3. Then proceed with the work
4. Record any new decisions or discoveries made

Use search_knowledge proactively to find relevant context.
"""

    logger.info(f"Session initialized: {context['summary']}")

    return context
