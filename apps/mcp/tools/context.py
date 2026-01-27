"""
Context management tools for the knowledge graph.

Provides tools for managing the current working context (active project, active task)
which enables hierarchical task management and context-aware task creation.

Also provides reasoning context tracking for automatic parent-based linking of
reasoning nodes (thoughts, discoveries, problems, fixes, constraints, decisions).
"""

from typing import Any, Dict, List, Optional, Tuple
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


# =============================================================================
# Reasoning Context Helpers
# =============================================================================
# These helpers manage the "focus node" - whatever the agent is currently
# working on. New reasoning nodes automatically link to the focus.


def _get_reasoning_context(client: GraphitiClient) -> Dict[str, Any]:
    """
    Get the reasoning context from the context node.

    Returns:
        Dictionary with reasoning context:
        - focus_node_id: Current focus node (any node type)
        - focus_node_type: Type of the focus node
        - focus_started_at: When focus was set
        - active_problem_id: Problem being investigated (persists until fixed)
        - constraints_collected: Constraint IDs for pending decision
    """
    context_nodes = client.query_nodes(filters={"type": CONTEXT_NODE_TYPE}, limit=1)

    if not context_nodes:
        return {
            "focus_node_id": None,
            "focus_node_type": None,
            "focus_started_at": None,
            "active_problem_id": None,
            "constraints_collected": [],
        }

    metadata = context_nodes[0].metadata or {}
    reasoning = metadata.get("reasoning_context", {})

    return {
        "focus_node_id": reasoning.get("focus_node_id"),
        "focus_node_type": reasoning.get("focus_node_type"),
        "focus_started_at": reasoning.get("focus_started_at"),
        "active_problem_id": reasoning.get("active_problem_id"),
        "constraints_collected": reasoning.get("constraints_collected", []),
    }


def _update_reasoning_context(client: GraphitiClient, updates: Dict[str, Any]) -> None:
    """
    Update specific fields in the reasoning context.

    Args:
        client: The GraphitiClient instance
        updates: Dictionary of fields to update
    """
    context_nodes = client.query_nodes(filters={"type": CONTEXT_NODE_TYPE}, limit=1)

    if not context_nodes:
        # Create context node with reasoning context
        context_node = Node(
            type=CONTEXT_NODE_TYPE,
            content=CONTEXT_NODE_CONTENT,
            metadata={
                "reasoning_context": updates,
            },
        )
        client.add_node(context_node)
        logger.info(f"Created context node with reasoning context: {updates}")
        return

    context_node = context_nodes[0]
    metadata = context_node.metadata or {}

    # Merge updates into existing reasoning context
    reasoning = metadata.get("reasoning_context", {})
    reasoning.update(updates)
    metadata["reasoning_context"] = reasoning

    context_node.metadata = metadata
    context_node.updated_at = datetime.utcnow()

    client.update_node(context_node.uuid, {
        "metadata": metadata,
        "updated_at": context_node.updated_at,
    })
    logger.debug(f"Updated reasoning context: {updates}")


def _get_focus(client: GraphitiClient) -> Optional[Tuple[str, str]]:
    """
    Get the current focus node.

    Returns:
        Tuple of (node_id, node_type) or None if no focus set
    """
    ctx = _get_reasoning_context(client)
    if ctx.get("focus_node_id"):
        return (ctx["focus_node_id"], ctx["focus_node_type"])
    return None


def _set_focus(client: GraphitiClient, node_id: str, node_type: str) -> None:
    """
    Set the current focus to a node.

    Args:
        client: The GraphitiClient instance
        node_id: UUID of the node to focus on
        node_type: Type of the node
    """
    _update_reasoning_context(client, {
        "focus_node_id": node_id,
        "focus_node_type": node_type,
        "focus_started_at": datetime.utcnow().isoformat(),
    })
    logger.info(f"Set focus to {node_type}: {node_id}")


def _clear_focus(client: GraphitiClient, keep_problem: bool = False) -> None:
    """
    Clear the current focus.

    Args:
        client: The GraphitiClient instance
        keep_problem: If True, keep active_problem_id set
    """
    updates = {
        "focus_node_id": None,
        "focus_node_type": None,
        "focus_started_at": None,
    }
    if not keep_problem:
        updates["active_problem_id"] = None
        updates["constraints_collected"] = []

    _update_reasoning_context(client, updates)
    logger.info(f"Cleared focus (keep_problem={keep_problem})")


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


async def add_constraint(
    client: GraphitiClient,
    content: str,
    source: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    use_context: bool = True,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a user preference or requirement that shapes decisions.

    Use this to capture constraints that must be considered when
    making choices, such as user preferences, technical requirements,
    or environmental limitations.

    When use_context=True, the constraint will:
    - Link to the current focus node via 'spawned' edge
    - Become the new focus for subsequent nodes
    - Be collected for automatic linking when a decision is made

    Args:
        client: The GraphitiClient instance
        content: The constraint (e.g., "User prefers desktop app")
        source: Where this constraint came from (e.g., "user", "requirement", "technical")
        priority: Optional priority (low, medium, high, must-have)
        tags: Optional tags (e.g., ["user-preference", "technical", "budget"])
        project_id: Optional project ID to associate with
        use_context: If True (default), auto-link to focus and become new focus
        parent_id: Explicit parent node ID (overrides focus if provided)

    Returns:
        Dictionary with the created constraint ID and parent link info
    """
    logger.info(f"add_constraint: content='{content[:50]}...'")

    node = Node(
        type="constraint",
        content=content,
        metadata={
            "source": source or "user",
            "priority": priority,
            "active": True,
            "tags": tags or [],
            "project_id": project_id,
        },
    )

    constraint_id = client.add_node(node)
    logger.info(f"Created constraint node: {constraint_id}")

    result = {
        "constraint_id": constraint_id,
        "content": content[:100],
        "source": source or "user",
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
            # Create edge: parent --spawned--> constraint
            edge = Edge(
                type="spawned",
                source_id=parent[0],
                target_id=constraint_id,
            )
            edge_id = client.add_edge(edge)
            logger.info(f"Created spawned edge from {parent[0]} to constraint: {edge_id}")
            result["parent_id"] = parent[0]
            result["parent_type"] = parent[1]
            result["edge_id"] = edge_id

        # Collect constraint for future decision linking
        ctx = _get_reasoning_context(client)
        constraints = ctx.get("constraints_collected", [])
        constraints.append(constraint_id)
        _update_reasoning_context(client, {"constraints_collected": constraints})
        result["constraints_collected_count"] = len(constraints)

        # Set this constraint as the new focus
        _set_focus(client, constraint_id, "constraint")
        result["is_focus"] = True

    return result


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


async def set_focus(
    client: GraphitiClient,
    node_id: str,
) -> Dict[str, Any]:
    """
    Set focus to a specific node for automatic parent-based linking.

    When focus is set, subsequent reasoning nodes (thoughts, discoveries, etc.)
    will automatically link to this node as their parent, creating traversable
    reasoning trees.

    Args:
        client: The GraphitiClient instance
        node_id: UUID of the node to focus on (task, problem, thought, etc.)

    Returns:
        Dictionary with success status and focus details
    """
    logger.info(f"set_focus: node_id={node_id}")

    # Verify node exists
    node = client.get_node(node_id)
    if not node:
        return {
            "success": False,
            "error": f"Node not found: {node_id}",
        }

    _set_focus(client, node_id, node.type)

    return {
        "success": True,
        "focus_node_id": node_id,
        "focus_node_type": node.type,
        "message": f"Focus set to {node.type}. New reasoning nodes will link to this as parent.",
    }


async def clear_focus(
    client: GraphitiClient,
    keep_problem: bool = False,
) -> Dict[str, Any]:
    """
    Clear the current focus to stop automatic parent-based linking.

    Args:
        client: The GraphitiClient instance
        keep_problem: If True, keep active_problem_id set for fix linking

    Returns:
        Dictionary with success status
    """
    logger.info(f"clear_focus: keep_problem={keep_problem}")

    _clear_focus(client, keep_problem=keep_problem)

    return {
        "success": True,
        "message": "Focus cleared. New reasoning nodes will not auto-link.",
        "kept_problem": keep_problem,
    }


async def get_reasoning_context(
    client: GraphitiClient,
) -> Dict[str, Any]:
    """
    Get the current reasoning context including focus and active problem.

    Returns:
        Dictionary with reasoning context:
        - focus_node_id: Current focus node
        - focus_node_type: Type of the focus node
        - focus_started_at: When focus was set
        - active_problem_id: Problem being investigated
        - constraints_collected: Constraint IDs for pending decision
    """
    logger.info("get_reasoning_context: Retrieving reasoning context")

    ctx = _get_reasoning_context(client)

    # Optionally fetch node details for better display
    focus_details = None
    if ctx.get("focus_node_id"):
        focus_node = client.get_node(ctx["focus_node_id"])
        if focus_node:
            focus_details = {
                "id": focus_node.uuid,
                "type": focus_node.type,
                "content": focus_node.content[:100] if focus_node.content else None,
            }

    problem_details = None
    if ctx.get("active_problem_id"):
        problem_node = client.get_node(ctx["active_problem_id"])
        if problem_node:
            problem_details = {
                "id": problem_node.uuid,
                "content": problem_node.content[:100] if problem_node.content else None,
            }

    return {
        "focus_node_id": ctx.get("focus_node_id"),
        "focus_node_type": ctx.get("focus_node_type"),
        "focus_started_at": ctx.get("focus_started_at"),
        "focus_details": focus_details,
        "active_problem_id": ctx.get("active_problem_id"),
        "active_problem_details": problem_details,
        "constraints_collected": ctx.get("constraints_collected", []),
        "constraints_count": len(ctx.get("constraints_collected", [])),
    }
