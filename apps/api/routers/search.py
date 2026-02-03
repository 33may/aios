"""
Search Router

Semantic search and graph traversal endpoints.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.integrations.graphiti.queries import (
    get_relevant_context,
    traverse,
    get_related,
)

router = APIRouter()


# Pydantic models for request/response
class SearchRequest(BaseModel):
    """Request model for search."""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum score")


class SearchResult(BaseModel):
    """Individual search result."""
    content: str
    score: float
    type: str
    source_file: Optional[str] = None
    captured_at: Optional[str] = None
    episode_type: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: List[SearchResult]
    total: int
    query: str


class TraverseRequest(BaseModel):
    """Request model for traversal."""
    node_id: str = Field(..., description="Starting node UUID")
    depth: int = Field(default=2, ge=1, le=5, description="Maximum traversal depth")
    edge_types: Optional[List[str]] = Field(None, description="Edge types to follow")


class NodeSummary(BaseModel):
    """Summarized node for traversal results."""
    uuid: str
    type: str
    content: str
    created_at: str


class TraverseResponse(BaseModel):
    """Response model for traversal."""
    start_node: NodeSummary
    levels: Dict[str, List[NodeSummary]]
    total_nodes: int


class RelatedResponse(BaseModel):
    """Response model for related nodes."""
    node_id: str
    related: List[Dict[str, Any]]
    total: int


def _get_client():
    """Get the client from main module."""
    from apps.api.main import get_client
    return get_client()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform semantic search across the knowledge graph."""
    client = _get_client()

    results = get_relevant_context(
        query=request.query,
        num_results=request.limit,
        min_score=request.min_score,
        client=client,
    )

    search_results = [
        SearchResult(
            content=r["content"],
            score=r["score"],
            type=r["type"],
            source_file=r.get("source_file"),
            captured_at=r.get("captured_at"),
            episode_type=r.get("episode_type"),
        )
        for r in results
    ]

    return SearchResponse(
        results=search_results,
        total=len(search_results),
        query=request.query,
    )


@router.get("")
async def search_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score"),
):
    """Perform semantic search (GET endpoint for convenience)."""
    request = SearchRequest(query=q, limit=limit, min_score=min_score)
    return await search(request)


@router.post("/traverse", response_model=TraverseResponse)
async def traverse_graph(request: TraverseRequest):
    """Traverse the graph from a starting node."""
    client = _get_client()

    # Check node exists
    start = client.get_node(request.node_id)
    if not start:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {request.node_id}"
        )

    # Perform traversal
    levels = traverse(
        node_id=request.node_id,
        depth=request.depth,
        client=client,
    )

    # Convert to response format
    response_levels = {}
    total = 0
    for level, nodes in levels.items():
        response_levels[level] = [
            NodeSummary(
                uuid=n.uuid,
                type=n.type,
                content=n.content[:200] + "..." if len(n.content) > 200 else n.content,
                created_at=n.created_at.isoformat(),
            )
            for n in nodes
        ]
        total += len(nodes)

    return TraverseResponse(
        start_node=NodeSummary(
            uuid=start.uuid,
            type=start.type,
            content=start.content[:200] + "..." if len(start.content) > 200 else start.content,
            created_at=start.created_at.isoformat(),
        ),
        levels=response_levels,
        total_nodes=total,
    )


@router.get("/related/{node_id}", response_model=RelatedResponse)
async def get_related_nodes(
    node_id: str,
    edge_type: Optional[str] = Query(None, description="Filter by edge type"),
    direction: str = Query("both", description="Direction: incoming, outgoing, or both"),
):
    """Get nodes related to a given node."""
    client = _get_client()

    # Check node exists
    node = client.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    # Get related
    related = get_related(
        node_id=node_id,
        edge_type=edge_type,
        direction=direction,
        client=client,
    )

    # Format response
    related_items = []
    for rel_node, edge in related:
        related_items.append({
            "node": {
                "uuid": rel_node.uuid,
                "type": rel_node.type,
                "content": rel_node.content[:200] + "..." if len(rel_node.content) > 200 else rel_node.content,
                "created_at": rel_node.created_at.isoformat(),
            },
            "edge": {
                "uuid": edge.uuid,
                "type": edge.type,
                "direction": "outgoing" if edge.source_id == node_id else "incoming",
            }
        })

    return RelatedResponse(
        node_id=node_id,
        related=related_items,
        total=len(related_items),
    )
