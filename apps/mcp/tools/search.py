"""
Search and context retrieval tools for the knowledge graph.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging
import os

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.queries import (
    get_relevant_context,
    search_semantic,
    query_temporal_nodes,
)

logger = logging.getLogger(__name__)


async def search_knowledge(
    client: GraphitiClient,
    query: str,
    limit: int = 10,
    min_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Perform semantic search across all knowledge in the graph.

    Args:
        client: The GraphitiClient instance
        query: Natural language search query
        limit: Maximum number of results
        min_score: Minimum relevance score threshold

    Returns:
        Dictionary with results array
    """
    logger.info(f"search_knowledge: query='{query}', limit={limit}, min_score={min_score}")

    results = get_relevant_context(
        query=query,
        num_results=limit,
        min_score=min_score,
        client=client,
    )

    return {
        "results": results,
        "query": query,
        "count": len(results),
    }


async def get_project_context(
    client: GraphitiClient,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get comprehensive context for a project.

    Args:
        client: The GraphitiClient instance
        project_id: Optional project ID (auto-detects from cwd if not provided)

    Returns:
        Dictionary with project context including decisions, tasks, discoveries
    """
    # Auto-detect project from current working directory
    if not project_id:
        cwd = os.getcwd()
        # Look for .git or .aios directory to identify project
        project_name = os.path.basename(cwd)
        logger.info(f"Auto-detected project: {project_name}")
    else:
        project_name = project_id

    now = datetime.utcnow()

    # Get recent decisions (last 90 days)
    decisions_start = now - timedelta(days=90)
    recent_decisions = query_temporal_nodes(
        start=decisions_start,
        end=now,
        node_type="decision",
        client=client,
    )

    # Get active tasks (last 30 days)
    tasks_start = now - timedelta(days=30)
    active_tasks = query_temporal_nodes(
        start=tasks_start,
        end=now,
        node_type="task",
        client=client,
    )

    # Get recent discoveries (last 30 days)
    recent_discoveries = query_temporal_nodes(
        start=tasks_start,
        end=now,
        node_type="discovery",
        client=client,
    )

    return {
        "project": {
            "name": project_name,
            "id": project_id,
        },
        "recent_decisions": [
            {
                "id": d.uuid,
                "content": d.content,
                "date": d.created_at.isoformat(),
                "metadata": d.metadata,
            }
            for d in recent_decisions[:10]
        ],
        "active_tasks": [
            {
                "id": t.uuid,
                "content": t.content,
                "status": t.metadata.get("status", "unknown") if t.metadata else "unknown",
                "date": t.created_at.isoformat(),
            }
            for t in active_tasks[:10]
        ],
        "key_discoveries": [
            {
                "id": d.uuid,
                "content": d.content,
                "date": d.created_at.isoformat(),
            }
            for d in recent_discoveries[:5]
        ],
        "summary": {
            "total_decisions": len(recent_decisions),
            "total_tasks": len(active_tasks),
            "total_discoveries": len(recent_discoveries),
        },
    }
