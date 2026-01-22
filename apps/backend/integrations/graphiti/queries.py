"""
Query Utilities for Graphiti Knowledge Graph

Provides high-level query functions for semantic search, hierarchical scoping,
graph traversal, and temporal queries. These utilities build on the GraphitiClient
to enable powerful knowledge retrieval patterns.
"""

from typing import List, Optional, Tuple
import logging
import math

from .client import GraphitiClient
from .models import Node

logger = logging.getLogger(__name__)


def _compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def _generate_query_embedding(query: str) -> List[float]:
    """
    Generate an embedding vector for a query string.

    This is a placeholder implementation that creates a simple embedding
    based on the query text. In production, this would call an actual
    embedding service (e.g., OpenAI embeddings, sentence-transformers).

    Args:
        query: The query text to embed

    Returns:
        A vector embedding of the query
    """
    # Simple placeholder: create a deterministic embedding based on query characteristics
    # In production, replace with actual embedding API call
    query_lower = query.lower()
    embedding = [
        float(len(query)),  # Length
        float(sum(ord(c) for c in query_lower[:10]) % 100) / 100,  # Character sum
        float(query_lower.count(' ')) / 10,  # Word count estimate
        float(query_lower.count('test')) * 10,  # Test keyword
        float(query_lower.count('project')) * 10,  # Project keyword
    ]

    # Normalize the embedding
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


def search_semantic(
    query: str,
    limit: int = 10,
    client: Optional[GraphitiClient] = None
) -> List[Tuple[Node, float]]:
    """
    Perform semantic search across all nodes in the knowledge graph.

    Uses embedding-based similarity to find nodes that are semantically
    similar to the query, regardless of exact keyword matches. This enables
    natural language queries and conceptual search.

    Args:
        query: The search query (natural language or keywords)
        limit: Maximum number of results to return (default: 10)
        client: Optional GraphitiClient instance. If not provided, creates a new one.

    Returns:
        List of (Node, score) tuples, sorted by relevance (highest first).
        Score is the cosine similarity between query and node embeddings.

    Example:
        >>> results = search_semantic("authentication implementation")
        >>> for node, score in results:
        ...     print(f"{node.type}: {node.content[:50]} (score: {score:.2f})")

    Notes:
        - Nodes without embeddings are excluded from results
        - Results are sorted by similarity score in descending order
        - In production, replace the placeholder embedding with actual embedding service
    """
    # Create or use provided client
    should_disconnect = False
    if client is None:
        client = GraphitiClient()
        client.connect()
        should_disconnect = True

    try:
        logger.info(f"Performing semantic search for query: '{query}' (limit={limit})")

        # Generate embedding for the query
        query_embedding = _generate_query_embedding(query)

        # Compute similarity scores for all nodes with embeddings
        results: List[Tuple[Node, float]] = []

        for node in client._nodes.values():
            if node.embedding is None:
                continue

            # Compute cosine similarity
            similarity = _compute_cosine_similarity(query_embedding, node.embedding)
            results.append((node, similarity))

        # Sort by similarity score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Apply limit
        results = results[:limit]

        logger.info(f"Semantic search found {len(results)} results")
        return results

    finally:
        if should_disconnect:
            client.disconnect()
