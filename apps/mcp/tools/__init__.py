"""
MCP Tool implementations for knowledge graph operations.
"""

from .search import search_knowledge, get_project_context
from .decisions import get_decisions, record_decision
from .tasks import get_tasks, add_task, update_task
from .activity import get_recent_activity, add_discovery
from .traversal import traverse_related
from .context import (
    get_context,
    set_context,
    create_project,
    list_projects,
    get_task_tree,
)

__all__ = [
    "search_knowledge",
    "get_project_context",
    "get_decisions",
    "record_decision",
    "get_tasks",
    "add_task",
    "update_task",
    "get_recent_activity",
    "add_discovery",
    "traverse_related",
    # Context management tools
    "get_context",
    "set_context",
    "create_project",
    "list_projects",
    "get_task_tree",
]
