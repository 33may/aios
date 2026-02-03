"""
Knowledge Graph REST API

FastAPI server providing REST endpoints for the knowledge graph.
Wraps GraphitiClient to provide HTTP access to nodes, edges, search, and projects.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.integrations.graphiti.client import GraphitiClient
from apps.backend.integrations.graphiti.config import GraphitiConfig

from apps.api.routers import nodes, edges, search, projects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client instance
client: Optional[GraphitiClient] = None


def get_client() -> GraphitiClient:
    """Get the global GraphitiClient instance."""
    global client
    if client is None:
        raise RuntimeError("Client not initialized")
    return client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - connect/disconnect from database."""
    global client

    # Initialize client with Neo4j backend
    config = GraphitiConfig.for_neo4j()
    client = GraphitiClient(config)
    client.connect()
    logger.info("Connected to knowledge graph backend")

    yield

    # Cleanup
    if client:
        client.disconnect()
        logger.info("Disconnected from knowledge graph backend")


app = FastAPI(
    title="Knowledge Graph API",
    description="REST API for the AIOS knowledge graph",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(edges.router, prefix="/edges", tags=["edges"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Knowledge Graph API",
        "version": "1.0.0",
        "endpoints": {
            "nodes": "/nodes",
            "edges": "/edges",
            "search": "/search",
            "projects": "/projects",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    global client
    connected = client.is_connected() if client else False
    return {
        "status": "healthy" if connected else "unhealthy",
        "database": "connected" if connected else "disconnected",
    }


@app.get("/stats")
async def stats():
    """Get knowledge graph statistics."""
    global client
    if not client or not client.is_connected():
        return {"error": "Not connected to database"}

    nodes = client.query_nodes(limit=10000)
    edges = client.query_edges(limit=10000)

    # Count by type
    node_counts = {}
    for node in nodes:
        node_type = node.type
        node_counts[node_type] = node_counts.get(node_type, 0) + 1

    edge_counts = {}
    for edge in edges:
        edge_type = edge.type
        edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "nodes_by_type": node_counts,
        "edges_by_type": edge_counts,
    }
