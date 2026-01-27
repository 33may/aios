"""
Task management tools for the knowledge graph.

Supports hierarchical task management with:
- Projects as top-level containers
- Tasks with unlimited nesting via parent_id
- Context-aware task creation (auto-linking to active project/task)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge
from apps.backend.integrations.graphiti.queries import query_temporal_nodes

logger = logging.getLogger(__name__)

# Node type constants
CONTEXT_NODE_TYPE = "context"
PROJECT_NODE_TYPE = "project"


def _get_current_context(client: GraphitiClient) -> Dict[str, Any]:
    """
    Get the current working context (active project and task).

    Returns:
        Dictionary with active_project_id, active_task_id, etc.
    """
    context_nodes = client.query_nodes(filters={"type": CONTEXT_NODE_TYPE}, limit=1)
    if not context_nodes:
        return {}
    return context_nodes[0].metadata or {}


def _calculate_depth(client: GraphitiClient, parent_id: Optional[str], project_id: Optional[str]) -> int:
    """
    Calculate the depth level for a task.

    Args:
        client: The GraphitiClient instance
        parent_id: Parent task ID (if any)
        project_id: Project ID (if any)

    Returns:
        Depth level (0 = direct under project, 1+ = nested under tasks)
    """
    if not parent_id:
        return 0

    depth = 0
    current_id = parent_id

    # Walk up the parent chain
    while current_id:
        node = client.get_node(current_id)
        if not node:
            break

        if node.type == PROJECT_NODE_TYPE:
            # Reached project, stop counting
            break

        if node.type == "task":
            depth += 1
            current_id = node.metadata.get("parent_id") if node.metadata else None
        else:
            break

    return depth


async def get_tasks(
    client: GraphitiClient,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    top_level_only: bool = False,
    days: int = 30,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieve tasks from the knowledge graph.

    Args:
        client: The GraphitiClient instance
        status: Optional status filter (pending, in_progress, completed, blocked)
        project_id: Optional project ID for scoping
        parent_id: Optional parent task ID to get subtasks of
        top_level_only: If True, only return tasks without a parent (depth 0)
        days: How far back to look (default 30 days)
        limit: Maximum number of tasks to return

    Returns:
        Dictionary with tasks array
    """
    logger.info(f"get_tasks: status={status}, project_id={project_id}, parent_id={parent_id}, days={days}")

    now = datetime.utcnow()
    start = now - timedelta(days=days)

    tasks = query_temporal_nodes(
        start=start,
        end=now,
        node_type="task",
        client=client,
    )

    # Filter by status if specified
    if status:
        tasks = [
            t for t in tasks
            if t.metadata and t.metadata.get("status") == status
        ]

    # Filter by project if specified
    if project_id:
        tasks = [
            t for t in tasks
            if t.metadata and t.metadata.get("project_id") == project_id
        ]

    # Filter by parent if specified
    if parent_id:
        tasks = [
            t for t in tasks
            if t.metadata and t.metadata.get("parent_id") == parent_id
        ]

    # Filter to top-level only if requested
    if top_level_only:
        tasks = [
            t for t in tasks
            if not (t.metadata and t.metadata.get("parent_id"))
        ]

    # Format tasks
    formatted = []
    for t in tasks[:limit]:
        metadata = t.metadata or {}
        formatted.append({
            "id": t.uuid,
            "subject": metadata.get("subject", t.content[:100]),
            "description": metadata.get("description", t.content),
            "status": metadata.get("status", "pending"),
            "blockers": metadata.get("blocked_by", []),
            "parent_id": metadata.get("parent_id"),
            "project_id": metadata.get("project_id"),
            "depth": metadata.get("depth", 0),
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        })

    return {
        "tasks": formatted,
        "count": len(formatted),
        "period_days": days,
        "status_filter": status,
        "parent_id_filter": parent_id,
        "top_level_only": top_level_only,
    }


async def add_task(
    client: GraphitiClient,
    subject: str,
    description: str,
    status: str = "pending",
    blocked_by: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    use_context: bool = True,
) -> Dict[str, Any]:
    """
    Add a new task to the knowledge graph with hierarchy support.

    If use_context=True (default) and no explicit parent_id/project_id:
    - If there's an active task in context → becomes subtask of that task
    - If there's only an active project → becomes top-level task in project
    - Otherwise → creates a floating task (no hierarchy)

    Args:
        client: The GraphitiClient instance
        subject: Short subject/title for the task
        description: Detailed description
        status: Initial status (default: pending)
        blocked_by: Optional list of task IDs that block this task
        project_id: Optional project ID to associate with
        parent_id: Optional parent task ID (makes this a subtask)
        use_context: If True, auto-use current context when parent_id/project_id not set

    Returns:
        Dictionary with the created task ID and hierarchy info
    """
    logger.info(f"add_task: subject='{subject}', status={status}, parent_id={parent_id}, use_context={use_context}")

    # Resolve hierarchy from context if needed
    effective_parent_id = parent_id
    effective_project_id = project_id

    if use_context and not parent_id and not project_id:
        context = _get_current_context(client)
        if context:
            # If there's an active task, make this a subtask
            if context.get("active_task_id"):
                effective_parent_id = context.get("active_task_id")
                logger.info(f"add_task: Using context active_task_id={effective_parent_id}")
            # If there's an active project, link to it
            if context.get("active_project_id"):
                effective_project_id = context.get("active_project_id")
                logger.info(f"add_task: Using context active_project_id={effective_project_id}")

    # If parent_id is set but project_id isn't, inherit project from parent
    if effective_parent_id and not effective_project_id:
        parent_node = client.get_node(effective_parent_id)
        if parent_node and parent_node.metadata:
            effective_project_id = parent_node.metadata.get("project_id")
            logger.info(f"add_task: Inherited project_id={effective_project_id} from parent")

    # Calculate depth
    depth = _calculate_depth(client, effective_parent_id, effective_project_id)

    # Create the task node
    node = Node(
        type="task",
        content=f"{subject}\n\n{description}",
        metadata={
            "subject": subject,
            "description": description,
            "status": status,
            "blocked_by": blocked_by or [],
            "project_id": effective_project_id,
            "parent_id": effective_parent_id,
            "depth": depth,
        },
    )

    # Add to graph
    task_id = client.add_node(node)

    # Create CONTAINS edge from parent (project or task)
    if effective_parent_id:
        edge = Edge(
            type="contains",
            source_id=effective_parent_id,
            target_id=task_id,
        )
        client.add_edge(edge)
        logger.info(f"add_task: Created CONTAINS edge from parent {effective_parent_id}")
    elif effective_project_id:
        # Link directly to project
        edge = Edge(
            type="contains",
            source_id=effective_project_id,
            target_id=task_id,
        )
        client.add_edge(edge)
        logger.info(f"add_task: Created CONTAINS edge from project {effective_project_id}")

    # Create blocking edges if specified
    if blocked_by:
        for blocker_id in blocked_by:
            edge = Edge(
                type="blocks",
                source_id=blocker_id,
                target_id=task_id,
            )
            client.add_edge(edge)

    logger.info(f"Created task node: {task_id}")

    return {
        "task_id": task_id,
        "subject": subject,
        "status": status,
        "parent_id": effective_parent_id,
        "project_id": effective_project_id,
        "depth": depth,
        "created_at": node.created_at.isoformat(),
        "success": True,
    }


async def update_task(
    client: GraphitiClient,
    task_id: str,
    status: Optional[str] = None,
    description: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing task in the knowledge graph.

    Args:
        client: The GraphitiClient instance
        task_id: The ID of the task to update
        status: New status (optional)
        description: New description (optional)
        parent_id: New parent task/project ID to move under (optional)

    Returns:
        Dictionary with success status
    """
    logger.info(f"update_task: task_id={task_id}, status={status}, parent_id={parent_id}")

    # Get the existing task
    node = client.get_node(task_id)
    if not node:
        logger.warning(f"Task not found: {task_id}")
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    # Update metadata
    if node.metadata is None:
        node.metadata = {}

    if status:
        node.metadata["status"] = status

    if description:
        node.metadata["description"] = description
        node.content = f"{node.metadata.get('subject', '')}\n\n{description}"

    # Handle parent_id change (move task)
    old_parent_id = node.metadata.get("parent_id")
    if parent_id is not None and parent_id != old_parent_id:
        # Verify new parent exists
        new_parent = client.get_node(parent_id)
        if not new_parent:
            return {
                "success": False,
                "error": f"New parent not found: {parent_id}",
            }

        # Remove old CONTAINS edges pointing to this task
        all_edges = client.query_edges(filters={"type": "contains"}, limit=1000)
        for edge in all_edges:
            if edge.target_id == task_id:
                client.delete_edge(edge.uuid)
                logger.info(f"Deleted old CONTAINS edge {edge.uuid} from {edge.source_id}")

        # Update parent_id in metadata
        node.metadata["parent_id"] = parent_id

        # Inherit project_id from new parent if it has one
        if new_parent.metadata and new_parent.metadata.get("project_id"):
            node.metadata["project_id"] = new_parent.metadata.get("project_id")
        elif new_parent.type == "project":
            node.metadata["project_id"] = parent_id

        # Recalculate depth
        node.metadata["depth"] = _calculate_depth(client, parent_id, node.metadata.get("project_id"))

        # Create new CONTAINS edge from new parent
        from apps.backend.integrations.graphiti.models import Edge
        edge = Edge(
            type="contains",
            source_id=parent_id,
            target_id=task_id,
        )
        client.add_edge(edge)
        logger.info(f"Created CONTAINS edge from new parent {parent_id}")

    node.updated_at = datetime.utcnow()

    logger.info(f"Updated task: {task_id}")

    return {
        "task_id": task_id,
        "status": node.metadata.get("status"),
        "parent_id": node.metadata.get("parent_id"),
        "depth": node.metadata.get("depth"),
        "updated_at": node.updated_at.isoformat(),
        "success": True,
    }


async def delete_task(
    client: GraphitiClient,
    task_id: str,
    delete_subtasks: bool = False,
) -> Dict[str, Any]:
    """
    Delete a task from the knowledge graph.

    Args:
        client: The GraphitiClient instance
        task_id: The ID of the task to delete
        delete_subtasks: If True, also delete all subtasks (default: False)

    Returns:
        Dictionary with success status and deleted count
    """
    logger.info(f"delete_task: task_id={task_id}, delete_subtasks={delete_subtasks}")

    # Get the existing task
    node = client.get_node(task_id)
    if not node:
        logger.warning(f"Task not found: {task_id}")
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    if node.type != "task":
        logger.warning(f"Node is not a task: {task_id} (type={node.type})")
        return {
            "success": False,
            "error": f"Node is not a task: {task_id} (type={node.type})",
        }

    deleted_ids = []

    # If delete_subtasks, find and delete all children first
    if delete_subtasks:
        # Get all tasks and find subtasks
        all_tasks = client.query_nodes(filters={"type": "task"}, limit=1000)
        subtasks_to_delete = []

        def find_subtasks(parent_id: str):
            """Recursively find all subtasks."""
            for t in all_tasks:
                if t.metadata and t.metadata.get("parent_id") == parent_id:
                    subtasks_to_delete.append(t.uuid)
                    find_subtasks(t.uuid)

        find_subtasks(task_id)

        # Delete subtasks (deepest first to avoid orphans)
        for subtask_id in reversed(subtasks_to_delete):
            if client.delete_node(subtask_id):
                deleted_ids.append(subtask_id)
                logger.info(f"Deleted subtask: {subtask_id}")

    # Delete the main task
    subject = node.metadata.get("subject", "") if node.metadata else ""
    if client.delete_node(task_id):
        deleted_ids.append(task_id)
        logger.info(f"Deleted task: {task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "subject": subject,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
        }
    else:
        return {
            "success": False,
            "error": f"Failed to delete task: {task_id}",
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
        }
