"""
Nodes Router

CRUD endpoints for knowledge graph nodes.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.integrations.graphiti.models import Node
from apps.backend.integrations.graphiti.schema import NodeType

router = APIRouter()


# Pydantic models for request/response
class NodeCreate(BaseModel):
    """Request model for creating a node."""
    type: str = Field(..., description="Node type (project, task, decision, etc.)")
    content: str = Field(..., description="Node content/description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NodeUpdate(BaseModel):
    """Request model for updating a node."""
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NodeResponse(BaseModel):
    """Response model for a node."""
    uuid: str
    type: str
    content: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class NodeListResponse(BaseModel):
    """Response model for a list of nodes."""
    nodes: List[NodeResponse]
    total: int


def _node_to_response(node: Node) -> NodeResponse:
    """Convert a Node to NodeResponse."""
    return NodeResponse(
        uuid=node.uuid,
        type=node.type,
        content=node.content,
        created_at=node.created_at.isoformat(),
        updated_at=node.updated_at.isoformat(),
        metadata=node.metadata or {},
    )


def _get_client():
    """Get the client from main module."""
    from apps.api.main import get_client
    return get_client()


@router.get("", response_model=NodeListResponse)
async def list_nodes(
    type: Optional[str] = Query(None, description="Filter by node type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum nodes to return"),
):
    """List all nodes with optional type filter."""
    client = _get_client()

    filters = {}
    if type:
        filters["type"] = type

    nodes = client.query_nodes(filters=filters if filters else None, limit=limit)

    return NodeListResponse(
        nodes=[_node_to_response(n) for n in nodes],
        total=len(nodes),
    )


@router.get("/types")
async def list_node_types():
    """List all available node types."""
    return {
        "types": [t.value for t in NodeType],
    }


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str):
    """Get a node by UUID."""
    client = _get_client()

    node = client.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    return _node_to_response(node)


@router.post("", response_model=NodeResponse, status_code=201)
async def create_node(node_data: NodeCreate):
    """Create a new node."""
    client = _get_client()

    # Validate node type
    valid_types = [t.value for t in NodeType]
    if node_data.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node type: {node_data.type}. Valid types: {valid_types}"
        )

    node = Node(
        type=node_data.type,
        content=node_data.content,
        metadata=node_data.metadata or {},
    )

    client.add_node(node)
    return _node_to_response(node)


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(node_id: str, node_data: NodeUpdate):
    """Update a node."""
    client = _get_client()

    # Check if node exists
    existing = client.get_node(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    # Build updates
    updates = {}
    if node_data.content is not None:
        updates["content"] = node_data.content
    if node_data.metadata is not None:
        updates["metadata"] = node_data.metadata

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = client.update_node(node_id, updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update node")

    # Fetch and return updated node
    updated = client.get_node(node_id)
    return _node_to_response(updated)


@router.delete("/{node_id}")
async def delete_node(node_id: str):
    """Delete a node and its connected edges."""
    client = _get_client()

    # Check if node exists
    existing = client.get_node(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    success = client.delete_node(node_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete node")

    return {"message": "Node deleted", "uuid": node_id}
