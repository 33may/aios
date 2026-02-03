"""
Edges Router

CRUD endpoints for knowledge graph edges.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.integrations.graphiti.models import Edge
from apps.backend.integrations.graphiti.schema import EdgeType

router = APIRouter()


# Pydantic models for request/response
class EdgeCreate(BaseModel):
    """Request model for creating an edge."""
    type: str = Field(..., description="Edge type (contains, references, led_to, etc.)")
    source_id: str = Field(..., description="Source node UUID")
    target_id: str = Field(..., description="Target node UUID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EdgeResponse(BaseModel):
    """Response model for an edge."""
    uuid: str
    type: str
    source_id: str
    target_id: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class EdgeListResponse(BaseModel):
    """Response model for a list of edges."""
    edges: List[EdgeResponse]
    total: int


def _edge_to_response(edge: Edge) -> EdgeResponse:
    """Convert an Edge to EdgeResponse."""
    return EdgeResponse(
        uuid=edge.uuid,
        type=edge.type,
        source_id=edge.source_id,
        target_id=edge.target_id,
        created_at=edge.created_at.isoformat(),
        updated_at=edge.updated_at.isoformat(),
        metadata=edge.metadata or {},
    )


def _get_client():
    """Get the client from main module."""
    from apps.api.main import get_client
    return get_client()


@router.get("", response_model=EdgeListResponse)
async def list_edges(
    type: Optional[str] = Query(None, description="Filter by edge type"),
    source_id: Optional[str] = Query(None, description="Filter by source node"),
    target_id: Optional[str] = Query(None, description="Filter by target node"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum edges to return"),
):
    """List all edges with optional filters."""
    client = _get_client()

    filters = {}
    if type:
        filters["type"] = type
    if source_id:
        filters["source_id"] = source_id
    if target_id:
        filters["target_id"] = target_id

    edges = client.query_edges(filters=filters if filters else None, limit=limit)

    return EdgeListResponse(
        edges=[_edge_to_response(e) for e in edges],
        total=len(edges),
    )


@router.get("/types")
async def list_edge_types():
    """List all available edge types."""
    return {
        "types": [t.value for t in EdgeType],
    }


@router.get("/{edge_id}", response_model=EdgeResponse)
async def get_edge(edge_id: str):
    """Get an edge by UUID."""
    client = _get_client()

    edge = client.get_edge(edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge not found: {edge_id}")

    return _edge_to_response(edge)


@router.post("", response_model=EdgeResponse, status_code=201)
async def create_edge(edge_data: EdgeCreate):
    """Create a new edge between two nodes."""
    client = _get_client()

    # Validate edge type
    valid_types = [t.value for t in EdgeType]
    if edge_data.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid edge type: {edge_data.type}. Valid types: {valid_types}"
        )

    # Check source node exists
    source = client.get_node(edge_data.source_id)
    if not source:
        raise HTTPException(
            status_code=400,
            detail=f"Source node not found: {edge_data.source_id}"
        )

    # Check target node exists
    target = client.get_node(edge_data.target_id)
    if not target:
        raise HTTPException(
            status_code=400,
            detail=f"Target node not found: {edge_data.target_id}"
        )

    edge = Edge(
        type=edge_data.type,
        source_id=edge_data.source_id,
        target_id=edge_data.target_id,
        metadata=edge_data.metadata or {},
    )

    try:
        client.add_edge(edge)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _edge_to_response(edge)


@router.delete("/{edge_id}")
async def delete_edge(edge_id: str):
    """Delete an edge."""
    client = _get_client()

    # Check if edge exists
    existing = client.get_edge(edge_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Edge not found: {edge_id}")

    success = client.delete_edge(edge_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete edge")

    return {"message": "Edge deleted", "uuid": edge_id}


@router.get("/node/{node_id}", response_model=EdgeListResponse)
async def get_node_edges(
    node_id: str,
    direction: str = Query("both", description="Direction: incoming, outgoing, or both"),
):
    """Get all edges connected to a node."""
    client = _get_client()

    # Check node exists
    node = client.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    edges = []

    if direction in ("outgoing", "both"):
        outgoing = client.query_edges(filters={"source_id": node_id}, limit=1000)
        edges.extend(outgoing)

    if direction in ("incoming", "both"):
        incoming = client.query_edges(filters={"target_id": node_id}, limit=1000)
        edges.extend(incoming)

    return EdgeListResponse(
        edges=[_edge_to_response(e) for e in edges],
        total=len(edges),
    )
