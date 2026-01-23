"""
Context management tools for the knowledge graph.

Provides tools for managing the current working context (active project, active task)
which enables hierarchical task management and context-aware task creation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.models import Node, Edge

logger = logging.getLogger(__name__)

# Context node type identifier
CONTEXT_NODE_TYPE = "context"
CONTEXT_NODE_CONTENT = "Current working context"

# Project node type identifier
PROJECT_NODE_TYPE = "project"


async def get_context(
    client: GraphitiClient,
) -> Dict[str, Any]:
    """
    Get the current working context.

    Returns the active project and task that Claude is currently working within.
    New tasks created will automatically be linked to this context.

    Args:
        client: The GraphitiClient instance

    Returns:
        Dictionary with current context:
        - active_project_id: UUID of the active project (or null)
        - active_project_name: Name of the active project (or null)
        - active_task_id: UUID of the active task (or null)
        - active_task_subject: Subject of the active task (or null)
        - inferred_from: How the context was set (explicit, cwd, conversation)
        - updated_at: When the context was last updated
    """
    logger.info("get_context: Retrieving current context")

    # Find the context node
    context_nodes = client.query_nodes(filters={"type": CONTEXT_NODE_TYPE}, limit=1)

    if not context_nodes:
        logger.info("get_context: No context set")
        return {
            "active_project_id": None,
            "active_project_name": None,
            "active_task_id": None,
            "active_task_subject": None,
            "inferred_from": None,
            "updated_at": None,
            "has_context": False,
        }

    context_node = context_nodes[0]
    metadata = context_node.metadata or {}

    return {
        "active_project_id": metadata.get("active_project_id"),
        "active_project_name": metadata.get("active_project_name"),
        "active_task_id": metadata.get("active_task_id"),
        "active_task_subject": metadata.get("active_task_subject"),
        "inferred_from": metadata.get("inferred_from"),
        "updated_at": context_node.updated_at.isoformat() if context_node.updated_at else None,
        "has_context": True,
    }


async def set_context(
    client: GraphitiClient,
    project: Optional[str] = None,
    task_id: Optional[str] = None,
    inferred_from: str = "explicit",
) -> Dict[str, Any]:
    """
    Set the current working context.

    Updates the active project and/or task. When a project is set, new tasks
    will be created under that project. When a task is set, new subtasks
    will be created under that task.

    Args:
        client: The GraphitiClient instance
        project: Project name or ID to set as active (or None to clear)
        task_id: Task ID to set as active (or None to clear)
        inferred_from: How the context was determined:
            - "explicit": User explicitly set it
            - "conversation": Inferred from conversation content
            - "cwd": Inferred from working directory

    Returns:
        Dictionary with the updated context
    """
    logger.info(f"set_context: project={project}, task_id={task_id}, inferred_from={inferred_from}")

    # Resolve project - could be name or ID
    active_project_id = None
    active_project_name = None

    if project:
        # First try to find by ID
        project_node = client.get_node(project)
        if project_node and project_node.type == PROJECT_NODE_TYPE:
            active_project_id = project_node.uuid
            active_project_name = project_node.metadata.get("name") if project_node.metadata else project
        else:
            # Try to find by name
            project_nodes = client.query_nodes(filters={"type": PROJECT_NODE_TYPE}, limit=100)
            for pn in project_nodes:
                if pn.metadata and pn.metadata.get("name") == project:
                    active_project_id = pn.uuid
                    active_project_name = project
                    break

            if not active_project_id:
                logger.warning(f"set_context: Project not found: {project}")
                return {
                    "success": False,
                    "error": f"Project not found: {project}. Use create_project to create it first.",
                }

    # Resolve task if provided
    active_task_id = None
    active_task_subject = None

    if task_id:
        task_node = client.get_node(task_id)
        if task_node and task_node.type == "task":
            active_task_id = task_node.uuid
            active_task_subject = task_node.metadata.get("subject") if task_node.metadata else None

            # If task has a project_id, use that as the active project
            if task_node.metadata and task_node.metadata.get("project_id"):
                task_project_id = task_node.metadata.get("project_id")
                task_project_node = client.get_node(task_project_id)
                if task_project_node and task_project_node.type == PROJECT_NODE_TYPE:
                    active_project_id = task_project_id
                    active_project_name = task_project_node.metadata.get("name") if task_project_node.metadata else None
        else:
            logger.warning(f"set_context: Task not found: {task_id}")
            return {
                "success": False,
                "error": f"Task not found: {task_id}",
            }

    # Find or create the context node
    context_nodes = client.query_nodes(filters={"type": CONTEXT_NODE_TYPE}, limit=1)

    if context_nodes:
        # Update existing context node
        context_node = context_nodes[0]
        context_node.metadata = {
            "active_project_id": active_project_id,
            "active_project_name": active_project_name,
            "active_task_id": active_task_id,
            "active_task_subject": active_task_subject,
            "inferred_from": inferred_from,
        }
        context_node.updated_at = datetime.utcnow()
        client.update_node(context_node.uuid, {
            "metadata": context_node.metadata,
            "updated_at": context_node.updated_at,
        })
        logger.info(f"set_context: Updated existing context node: {context_node.uuid}")
    else:
        # Create new context node
        context_node = Node(
            type=CONTEXT_NODE_TYPE,
            content=CONTEXT_NODE_CONTENT,
            metadata={
                "active_project_id": active_project_id,
                "active_project_name": active_project_name,
                "active_task_id": active_task_id,
                "active_task_subject": active_task_subject,
                "inferred_from": inferred_from,
            },
        )
        client.add_node(context_node)
        logger.info(f"set_context: Created new context node: {context_node.uuid}")

    return {
        "success": True,
        "active_project_id": active_project_id,
        "active_project_name": active_project_name,
        "active_task_id": active_task_id,
        "active_task_subject": active_task_subject,
        "inferred_from": inferred_from,
        "updated_at": context_node.updated_at.isoformat(),
    }


async def create_project(
    client: GraphitiClient,
    name: str,
    description: str = "",
) -> Dict[str, Any]:
    """
    Create a new project node.

    Projects are the top-level containers for tasks, decisions, and discoveries.
    Each project has a name and optional description.

    Args:
        client: The GraphitiClient instance
        name: The project name (must be unique)
        description: Optional project description

    Returns:
        Dictionary with the created project ID and details
    """
    logger.info(f"create_project: name='{name}'")

    # Check if project with this name already exists
    existing_projects = client.query_nodes(filters={"type": PROJECT_NODE_TYPE}, limit=100)
    for p in existing_projects:
        if p.metadata and p.metadata.get("name") == name:
            logger.warning(f"create_project: Project already exists: {name}")
            return {
                "success": False,
                "error": f"Project '{name}' already exists",
                "existing_project_id": p.uuid,
            }

    # Create the project node
    project_node = Node(
        type=PROJECT_NODE_TYPE,
        content=f"{name}\n\n{description}" if description else name,
        metadata={
            "name": name,
            "description": description,
        },
    )

    project_id = client.add_node(project_node)
    logger.info(f"create_project: Created project: {project_id}")

    return {
        "success": True,
        "project_id": project_id,
        "name": name,
        "description": description,
        "created_at": project_node.created_at.isoformat(),
    }


async def list_projects(
    client: GraphitiClient,
) -> Dict[str, Any]:
    """
    List all projects with summary stats.

    Returns all projects in the knowledge graph with counts of tasks,
    decisions, and discoveries under each project.

    Args:
        client: The GraphitiClient instance

    Returns:
        Dictionary with projects array, each containing:
        - id: Project UUID
        - name: Project name
        - description: Project description
        - task_count: Number of tasks under this project
        - created_at: When the project was created
    """
    logger.info("list_projects: Listing all projects")

    # Get all project nodes
    project_nodes = client.query_nodes(filters={"type": PROJECT_NODE_TYPE}, limit=100)

    # Get all tasks to count per project
    all_tasks = client.query_nodes(filters={"type": "task"}, limit=1000)

    # Build project summaries
    projects = []
    for p in project_nodes:
        metadata = p.metadata or {}
        project_id = p.uuid

        # Count tasks for this project
        task_count = sum(
            1 for t in all_tasks
            if t.metadata and t.metadata.get("project_id") == project_id
        )

        projects.append({
            "id": project_id,
            "name": metadata.get("name", "Unnamed"),
            "description": metadata.get("description", ""),
            "task_count": task_count,
            "created_at": p.created_at.isoformat(),
        })

    # Sort by name
    projects.sort(key=lambda p: p["name"].lower())

    return {
        "projects": projects,
        "count": len(projects),
    }


async def get_task_tree(
    client: GraphitiClient,
    root_id: str,
    max_depth: int = 3,
) -> Dict[str, Any]:
    """
    Get hierarchical task tree under a node.

    Returns tasks organized in a tree structure, showing parent-child
    relationships. Can start from a project or a task.

    Args:
        client: The GraphitiClient instance
        root_id: Project or task ID to start from
        max_depth: Maximum depth to traverse (default: 3)

    Returns:
        Dictionary with the task tree structure
    """
    logger.info(f"get_task_tree: root_id={root_id}, max_depth={max_depth}")

    # Get the root node
    root_node = client.get_node(root_id)
    if not root_node:
        return {
            "success": False,
            "error": f"Node not found: {root_id}",
        }

    def build_tree(node_id: str, current_depth: int) -> Dict[str, Any]:
        """Recursively build the task tree."""
        node = client.get_node(node_id)
        if not node:
            return None

        metadata = node.metadata or {}

        tree_node = {
            "id": node.uuid,
            "type": node.type,
            "subject": metadata.get("subject") or metadata.get("name") or node.content[:50],
            "status": metadata.get("status"),
            "depth": current_depth,
            "children": [],
        }

        if current_depth >= max_depth:
            return tree_node

        # Find children via CONTAINS edges
        edges = client.query_edges(filters={"source_id": node_id, "type": "contains"}, limit=100)

        for edge in edges:
            child_tree = build_tree(edge.target_id, current_depth + 1)
            if child_tree:
                tree_node["children"].append(child_tree)

        # Also find tasks by parent_id metadata (for backward compatibility)
        all_tasks = client.query_nodes(filters={"type": "task"}, limit=500)
        for task in all_tasks:
            if task.metadata and task.metadata.get("parent_id") == node_id:
                # Check if already in children (via edge)
                if not any(c["id"] == task.uuid for c in tree_node["children"]):
                    child_tree = build_tree(task.uuid, current_depth + 1)
                    if child_tree:
                        tree_node["children"].append(child_tree)

        # Sort children by subject
        tree_node["children"].sort(key=lambda c: c.get("subject", "").lower())

        return tree_node

    tree = build_tree(root_id, 0)

    # Count total tasks in tree
    def count_tasks(node: Dict[str, Any]) -> int:
        count = 1 if node["type"] == "task" else 0
        for child in node.get("children", []):
            count += count_tasks(child)
        return count

    total_tasks = count_tasks(tree) if tree else 0

    return {
        "success": True,
        "tree": tree,
        "total_tasks": total_tasks,
        "max_depth": max_depth,
    }
