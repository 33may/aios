"""
Projects Router

Endpoints for project management and hierarchical views.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.integrations.graphiti.models import Node

router = APIRouter()


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectResponse(BaseModel):
    """Response model for a project."""
    uuid: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    task_count: int = 0
    decision_count: int = 0
    discovery_count: int = 0


class TreeNode(BaseModel):
    """Node in a hierarchical tree view."""
    uuid: str
    type: str
    content: str
    created_at: str
    children: List["TreeNode"] = []
    status: Optional[str] = None


class ProjectTree(BaseModel):
    """Project with its task tree."""
    project: ProjectResponse
    tree: List[TreeNode]


def _get_client():
    """Get the client from main module."""
    from apps.api.main import get_client
    return get_client()


def _build_tree(node_id: str, client, visited: set, max_depth: int = 5, current_depth: int = 0) -> Optional[TreeNode]:
    """Recursively build tree from a node."""
    if current_depth >= max_depth or node_id in visited:
        return None

    visited.add(node_id)
    node = client.get_node(node_id)
    if not node:
        return None

    # Get children via 'contains' edges
    children_edges = client.query_edges(filters={"source_id": node_id, "type": "contains"}, limit=100)
    children = []
    for edge in children_edges:
        child_tree = _build_tree(edge.target_id, client, visited, max_depth, current_depth + 1)
        if child_tree:
            children.append(child_tree)

    # Sort children by created_at
    children.sort(key=lambda c: c.created_at)

    # Get status from metadata if it's a task
    status = None
    if node.type == "task" and node.metadata:
        status = node.metadata.get("status")

    return TreeNode(
        uuid=node.uuid,
        type=node.type,
        content=node.content[:200] + "..." if len(node.content) > 200 else node.content,
        created_at=node.created_at.isoformat(),
        children=children,
        status=status,
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects():
    """List all projects with stats."""
    client = _get_client()

    # Get all project nodes
    projects = client.query_nodes(filters={"type": "project"}, limit=1000)

    result = []
    for project in projects:
        # Count child nodes by type
        edges = client.query_edges(filters={"source_id": project.uuid, "type": "contains"}, limit=1000)
        child_ids = [e.target_id for e in edges]

        task_count = 0
        decision_count = 0
        discovery_count = 0

        for child_id in child_ids:
            child = client.get_node(child_id)
            if child:
                if child.type == "task":
                    task_count += 1
                elif child.type == "decision":
                    decision_count += 1
                elif child.type == "discovery":
                    discovery_count += 1

        # Extract name from content or metadata
        name = project.metadata.get("name", project.content[:50]) if project.metadata else project.content[:50]
        description = project.metadata.get("description") if project.metadata else None

        result.append(ProjectResponse(
            uuid=project.uuid,
            name=name,
            description=description,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            task_count=task_count,
            decision_count=decision_count,
            discovery_count=discovery_count,
        ))

    return result


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by UUID."""
    client = _get_client()

    project = client.get_node(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    if project.type != "project":
        raise HTTPException(status_code=400, detail=f"Node is not a project: {project_id}")

    # Count children
    edges = client.query_edges(filters={"source_id": project_id, "type": "contains"}, limit=1000)
    child_ids = [e.target_id for e in edges]

    task_count = 0
    decision_count = 0
    discovery_count = 0

    for child_id in child_ids:
        child = client.get_node(child_id)
        if child:
            if child.type == "task":
                task_count += 1
            elif child.type == "decision":
                decision_count += 1
            elif child.type == "discovery":
                discovery_count += 1

    name = project.metadata.get("name", project.content[:50]) if project.metadata else project.content[:50]
    description = project.metadata.get("description") if project.metadata else None

    return ProjectResponse(
        uuid=project.uuid,
        name=name,
        description=description,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        task_count=task_count,
        decision_count=decision_count,
        discovery_count=discovery_count,
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project."""
    client = _get_client()

    node = Node(
        type="project",
        content=data.name,
        metadata={
            "name": data.name,
            "description": data.description,
        }
    )

    client.add_node(node)

    return ProjectResponse(
        uuid=node.uuid,
        name=data.name,
        description=data.description,
        created_at=node.created_at.isoformat(),
        updated_at=node.updated_at.isoformat(),
        task_count=0,
        decision_count=0,
        discovery_count=0,
    )


@router.get("/{project_id}/tree", response_model=ProjectTree)
async def get_project_tree(
    project_id: str,
    max_depth: int = Query(5, ge=1, le=10, description="Maximum tree depth"),
):
    """Get project with its hierarchical task tree."""
    client = _get_client()

    project = client.get_node(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    if project.type != "project":
        raise HTTPException(status_code=400, detail=f"Node is not a project: {project_id}")

    # Build the tree
    visited = set()
    tree_root = _build_tree(project_id, client, visited, max_depth)

    # Get stats
    edges = client.query_edges(filters={"source_id": project_id, "type": "contains"}, limit=1000)
    child_ids = [e.target_id for e in edges]

    task_count = 0
    decision_count = 0
    discovery_count = 0

    for child_id in child_ids:
        child = client.get_node(child_id)
        if child:
            if child.type == "task":
                task_count += 1
            elif child.type == "decision":
                decision_count += 1
            elif child.type == "discovery":
                discovery_count += 1

    name = project.metadata.get("name", project.content[:50]) if project.metadata else project.content[:50]
    description = project.metadata.get("description") if project.metadata else None

    project_response = ProjectResponse(
        uuid=project.uuid,
        name=name,
        description=description,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        task_count=task_count,
        decision_count=decision_count,
        discovery_count=discovery_count,
    )

    return ProjectTree(
        project=project_response,
        tree=tree_root.children if tree_root else [],
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, cascade: bool = Query(False, description="Delete all children")):
    """Delete a project."""
    client = _get_client()

    project = client.get_node(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    if project.type != "project":
        raise HTTPException(status_code=400, detail=f"Node is not a project: {project_id}")

    if cascade:
        # Delete all children recursively
        def delete_children(node_id):
            edges = client.query_edges(filters={"source_id": node_id, "type": "contains"}, limit=1000)
            for edge in edges:
                delete_children(edge.target_id)
                client.delete_node(edge.target_id)

        delete_children(project_id)

    client.delete_node(project_id)
    return {"message": "Project deleted", "uuid": project_id, "cascade": cascade}
