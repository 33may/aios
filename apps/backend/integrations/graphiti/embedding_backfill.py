"""
Embedding Backfill for Knowledge Graph
=======================================

Processes all existing nodes that don't have embeddings and generates
embeddings for them using Ollama. Can be run on startup or manually.

Usage:
    # As a module
    python -m apps.backend.integrations.graphiti.embedding_backfill

    # Programmatically
    from apps.backend.integrations.graphiti.embedding_backfill import backfill_embeddings
    stats = backfill_embeddings()
"""

import logging
import time
from typing import Dict, Any, Optional

from .client import GraphitiClient
from .embedder import embed_text, get_embedder
from .providers.ollama_embedder import OllamaConnectionError, EmbedderError

logger = logging.getLogger(__name__)

# Node types that should have embeddings for semantic search
EMBEDDABLE_NODE_TYPES = {
    "task",
    "decision",
    "discovery",
    "thought",
    "problem",
    "fix",
    "constraint",
    "project",
}

# Node types to skip (internal system nodes)
SKIP_NODE_TYPES = {
    "context",
    "session",
}


def check_ollama_available() -> bool:
    """
    Check if Ollama is running and the embedding model is available.

    Returns:
        True if Ollama is ready for embedding generation
    """
    try:
        embedder = get_embedder()
        embedder.verify_connection()
        return True
    except (OllamaConnectionError, EmbedderError) as e:
        logger.warning(f"Ollama not available: {e}")
        return False


def backfill_embeddings(
    client: Optional[GraphitiClient] = None,
    batch_size: int = 50,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Process all nodes without embeddings and generate embeddings for them.

    Args:
        client: Optional GraphitiClient instance. Creates one if not provided.
        batch_size: Number of nodes to process before logging progress.
        dry_run: If True, only report what would be done without making changes.

    Returns:
        Dictionary with statistics:
        - total_nodes: Total number of nodes in the graph
        - nodes_without_embedding: Nodes that needed embeddings
        - nodes_processed: Nodes successfully processed
        - nodes_skipped: Nodes skipped (empty content, system types)
        - nodes_failed: Nodes that failed to get embeddings
        - duration_seconds: Time taken
    """
    start_time = time.time()

    # Check Ollama availability first
    if not dry_run and not check_ollama_available():
        return {
            "error": "Ollama is not available. Please start Ollama and ensure the embedding model is pulled.",
            "success": False,
        }

    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    stats = {
        "total_nodes": 0,
        "nodes_without_embedding": 0,
        "nodes_processed": 0,
        "nodes_skipped": 0,
        "nodes_failed": 0,
        "by_type": {},
        "dry_run": dry_run,
    }

    try:
        # Get all nodes
        all_nodes = client.query_nodes(filters={}, limit=10000)
        stats["total_nodes"] = len(all_nodes)

        logger.info(f"Backfill: Found {len(all_nodes)} total nodes")

        # Filter to nodes that need embeddings
        nodes_to_process = []
        for node in all_nodes:
            # Skip system node types
            if node.type in SKIP_NODE_TYPES:
                stats["nodes_skipped"] += 1
                continue

            # Check if node already has embedding
            if node.embedding and len(node.embedding) > 0:
                continue

            # Check if node type is embeddable
            if node.type not in EMBEDDABLE_NODE_TYPES:
                stats["nodes_skipped"] += 1
                continue

            # Skip nodes with empty content
            if not node.content or not node.content.strip():
                stats["nodes_skipped"] += 1
                continue

            nodes_to_process.append(node)

        stats["nodes_without_embedding"] = len(nodes_to_process)

        if dry_run:
            logger.info(f"Backfill (dry run): Would process {len(nodes_to_process)} nodes")
            for node in nodes_to_process:
                node_type = node.type
                stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1
            stats["duration_seconds"] = time.time() - start_time
            stats["success"] = True
            return stats

        logger.info(f"Backfill: Processing {len(nodes_to_process)} nodes without embeddings")

        # Process nodes
        for i, node in enumerate(nodes_to_process):
            try:
                # Generate embedding
                embedding = embed_text(node.content)

                if embedding is None:
                    stats["nodes_failed"] += 1
                    logger.warning(f"Failed to generate embedding for node {node.uuid}")
                    continue

                # Update node with embedding
                client.update_node(node.uuid, {"embedding": embedding})

                stats["nodes_processed"] += 1
                node_type = node.type
                stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1

                # Log progress
                if (i + 1) % batch_size == 0:
                    logger.info(f"Backfill progress: {i + 1}/{len(nodes_to_process)} nodes processed")

            except Exception as e:
                stats["nodes_failed"] += 1
                logger.error(f"Error processing node {node.uuid}: {e}")

        stats["duration_seconds"] = time.time() - start_time
        stats["success"] = True

        logger.info(
            f"Backfill complete: {stats['nodes_processed']} processed, "
            f"{stats['nodes_failed']} failed, {stats['nodes_skipped']} skipped "
            f"in {stats['duration_seconds']:.2f}s"
        )

        return stats

    finally:
        if should_disconnect:
            client.disconnect()


def ensure_embeddings_on_startup(client: Optional[GraphitiClient] = None) -> Dict[str, Any]:
    """
    Check and backfill embeddings on server startup.

    This is a lightweight version that:
    1. Checks if Ollama is available
    2. If available, runs backfill for any nodes missing embeddings
    3. Returns status without blocking if Ollama is unavailable

    Args:
        client: Optional GraphitiClient instance

    Returns:
        Dictionary with startup status
    """
    logger.info("Checking embeddings on startup...")

    # Check Ollama availability
    if not check_ollama_available():
        logger.warning(
            "Ollama not available on startup. Embeddings will be skipped. "
            "Start Ollama and run backfill manually: "
            "python -m apps.backend.integrations.graphiti.embedding_backfill"
        )
        return {
            "success": True,
            "ollama_available": False,
            "message": "Ollama not available - embeddings disabled",
        }

    # Run backfill
    stats = backfill_embeddings(client=client)

    if stats.get("nodes_processed", 0) > 0:
        logger.info(f"Startup backfill: Generated embeddings for {stats['nodes_processed']} nodes")
    else:
        logger.info("Startup check: All nodes already have embeddings")

    return {
        "success": True,
        "ollama_available": True,
        "backfill_stats": stats,
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Load environment
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Knowledge Graph Embedding Backfill")
    print("=" * 60)

    if dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    else:
        print("Mode: LIVE (embeddings will be generated)")

    print()

    # Run backfill
    stats = backfill_embeddings(dry_run=dry_run)

    # Print results
    if stats.get("error"):
        print(f"ERROR: {stats['error']}")
        sys.exit(1)

    print(f"Total nodes:              {stats['total_nodes']}")
    print(f"Nodes without embedding:  {stats['nodes_without_embedding']}")
    print(f"Nodes processed:          {stats['nodes_processed']}")
    print(f"Nodes skipped:            {stats['nodes_skipped']}")
    print(f"Nodes failed:             {stats['nodes_failed']}")
    print(f"Duration:                 {stats['duration_seconds']:.2f}s")

    if stats.get("by_type"):
        print("\nBy node type:")
        for node_type, count in sorted(stats["by_type"].items()):
            print(f"  {node_type}: {count}")

    print("\nDone!")
