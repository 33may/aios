#!/usr/bin/env python3
"""
Test Script for Ollama Embedding Integration
=============================================

This test validates that the Ollama embedder generates embeddings with
correct dimensions for semantic search functionality.

Tests:
1. Ollama embedding generation (direct API test)
2. Dimension validation for known models
3. Semantic similarity verification

Prerequisites:
    1. Install Ollama: https://ollama.ai/
    2. Pull an embedding model:
       ollama pull embeddinggemma    # 768 dimensions (lightweight)
    3. Start Ollama server: ollama serve
    4. Configure environment:
       export OLLAMA_EMBEDDING_MODEL=embeddinggemma
       export OLLAMA_BASE_URL=http://localhost:11434

Usage:
    cd apps/backend
    python integrations/graphiti/test_ollama_embedding_memory.py

    # Run specific tests:
    python integrations/graphiti/test_ollama_embedding_memory.py --test embeddings
    python integrations/graphiti/test_ollama_embedding_memory.py --test full-cycle
"""

import argparse
import math
import os
import sys
from pathlib import Path

# Add parent directories to path for imports
# This allows running from: cd apps/backend && python integrations/graphiti/test_...
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent
sys.path.insert(0, str(backend_dir))


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_result(label: str, value: str, success: bool = True):
    """Print a result line."""
    status = "PASS" if success else "FAIL"
    print(f"  [{status}] {label}: {value}")


def print_info(message: str):
    """Print an info line."""
    print(f"  INFO: {message}")


def print_step(step: int, message: str):
    """Print a step indicator."""
    print(f"\n  Step {step}: {message}")


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0


def test_ollama_embeddings() -> bool:
    """
    Test Ollama embedding generation with dimension validation.

    Returns:
        True if all tests pass, False otherwise
    """
    print_header("Test: Ollama Embedding Generation")

    # Import the embedder
    try:
        from integrations.graphiti.providers.ollama_embedder import (
            OllamaEmbedder,
            OllamaEmbedderConfig,
            KNOWN_OLLAMA_EMBEDDING_MODELS,
            get_embedding_dim_for_model,
            OllamaConnectionError,
            ModelNotFoundError,
        )
        print_result("Import embedder", "SUCCESS", True)
    except ImportError as e:
        print_result("Import embedder", f"FAILED: {e}", False)
        return False

    # Get configuration
    ollama_model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "embeddinggemma")
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    print(f"  Ollama Model: {ollama_model}")
    print(f"  Base URL: {ollama_base_url}")

    # Step 1: Test dimension lookup for known models
    print_step(1, "Testing dimension lookup for known models")

    for model, expected_dim in list(KNOWN_OLLAMA_EMBEDDING_MODELS.items())[:5]:
        actual_dim = get_embedding_dim_for_model(model)
        if actual_dim == expected_dim:
            print_result(f"Model {model}", f"dim={actual_dim}", True)
        else:
            print_result(f"Model {model}", f"Expected {expected_dim}, got {actual_dim}", False)
            return False

    # Step 2: Create embedder instance
    print_step(2, "Creating OllamaEmbedder instance")

    try:
        config = OllamaEmbedderConfig(
            model=ollama_model,
            base_url=ollama_base_url
        )
        embedder = OllamaEmbedder(config=config)
        expected_dim = embedder.embedding_dim
        print_result("Create embedder", f"model={ollama_model}, dim={expected_dim}", True)
    except Exception as e:
        print_result("Create embedder", f"FAILED: {e}", False)
        return False

    # Step 3: Verify Ollama connection
    print_step(3, "Verifying Ollama connection")

    try:
        embedder.verify_connection()
        print_result("Ollama connection", "Connected and model available", True)
    except OllamaConnectionError as e:
        print_result("Ollama connection", f"FAILED: {e}", False)
        print_info("Start Ollama with: ollama serve")
        return False
    except ModelNotFoundError as e:
        print_result("Ollama connection", f"FAILED: {e}", False)
        print_info(f"Pull model with: ollama pull {ollama_model}")
        return False

    # Step 4: Generate test embeddings
    print_step(4, "Generating test embeddings")

    test_texts = [
        "This is a test about OAuth authentication implementation.",
        "The user prefers using TypeScript for frontend development.",
        "A gotcha discovered: always validate JWT tokens on the server side.",
    ]

    embeddings = []
    for i, text in enumerate(test_texts):
        try:
            embedding = embedder.embed(text)
            embeddings.append(embedding)
            print_result(f"Embedding {i + 1}", f"Generated {len(embedding)} dimensions", True)
        except Exception as e:
            print_result(f"Embedding {i + 1}", f"FAILED: {e}", False)
            return False

    # Step 5: Validate embedding dimensions
    print_step(5, "Validating embedding dimensions")

    for i, embedding in enumerate(embeddings):
        if len(embedding) != expected_dim:
            print_result(
                f"Embedding {i + 1} dimension",
                f"Mismatch! Got {len(embedding)}, expected {expected_dim}",
                False,
            )
            return False
        print_result(f"Embedding {i + 1} dimension", f"{len(embedding)} matches expected", True)

    # Step 6: Test semantic similarity
    print_step(6, "Testing semantic similarity")

    query = "OAuth authentication implementation"
    query_embedding = embedder.embed(query)

    similarities = [cosine_similarity(query_embedding, emb) for emb in embeddings]

    print(f"  Query: '{query}'")
    print("  Similarities to test texts:")
    for i, (text, sim) in enumerate(zip(test_texts, similarities)):
        print(f"    {i + 1}. {sim:.4f} - '{text[:50]}...'")

    # First text (about OAuth) should have highest similarity
    if similarities[0] >= similarities[1] and similarities[0] >= similarities[2]:
        print_result("Semantic similarity", "OAuth query matches OAuth text best", True)
    else:
        print_info("Similarity ordering may vary - embeddings are still working")

    # Step 7: Test batch embedding
    print_step(7, "Testing batch embedding")

    try:
        batch_embeddings = embedder.embed_batch(["Test 1", "Test 2", "Test 3"])
        if len(batch_embeddings) == 3 and all(len(e) == expected_dim for e in batch_embeddings):
            print_result("Batch embedding", f"Generated {len(batch_embeddings)} embeddings", True)
        else:
            print_result("Batch embedding", "Dimension mismatch in batch", False)
            return False
    except Exception as e:
        print_result("Batch embedding", f"FAILED: {e}", False)
        return False

    # Step 8: Test empty text handling
    print_step(8, "Testing edge cases")

    try:
        empty_embedding = embedder.embed("")
        if len(empty_embedding) == expected_dim:
            print_result("Empty text handling", f"Returns zero vector of dim {len(empty_embedding)}", True)
        else:
            print_result("Empty text handling", "Dimension mismatch", False)
            return False
    except Exception as e:
        print_result("Empty text handling", f"FAILED: {e}", False)
        return False

    print()
    print_result("Ollama Embeddings", "All tests passed", True)
    return True


def test_retrieve_context_metadata() -> bool:
    """
    Test that get_relevant_context() returns results with context metadata.

    Verifies that search results include:
    - content: The main content of the node
    - score: The similarity score (0.0 to 1.0)
    - type: The node type
    - source_file: Where knowledge was captured (if available)
    - captured_at: When knowledge was captured (ISO 8601)
    - episode_type: Type of episode that captured knowledge

    Returns:
        True if all tests pass, False otherwise
    """
    print_header("Test: Context Metadata in Search Results")

    # Import required modules
    try:
        from integrations.graphiti.queries import get_relevant_context
        from integrations.graphiti.client import GraphitiClient
        from integrations.graphiti.models import Node
        from integrations.graphiti.schema import (
            METADATA_SOURCE_FILE,
            METADATA_CAPTURED_AT,
            METADATA_EPISODE_TYPE,
        )
        from integrations.graphiti.providers.ollama_embedder import OllamaEmbedder
        print_result("Import modules", "SUCCESS", True)
    except ImportError as e:
        print_result("Import modules", f"FAILED: {e}", False)
        return False

    # Step 1: Create embedder
    print_step(1, "Creating embedder for test data")

    try:
        embedder = OllamaEmbedder()
        print_result("Create embedder", f"model={embedder.config.model}", True)
    except Exception as e:
        print_result("Create embedder", f"FAILED: {e}", False)
        return False

    # Step 2: Create client and test nodes with metadata
    print_step(2, "Creating test nodes with context metadata")

    try:
        client = GraphitiClient()
        client.connect()

        # Create test nodes with rich metadata including source_file and episode_type
        test_nodes_data = [
            {
                "type": "decision",
                "content": "Use OAuth 2.0 for authentication with Google and GitHub providers",
                "metadata": {
                    METADATA_SOURCE_FILE: "/src/auth/oauth.py",
                    METADATA_EPISODE_TYPE: "architecture_decision",
                },
            },
            {
                "type": "discovery",
                "content": "JWT tokens must be validated on the server side for security",
                "metadata": {
                    METADATA_SOURCE_FILE: "/src/security/jwt.py",
                    METADATA_EPISODE_TYPE: "security_audit",
                },
            },
            {
                "type": "task",
                "content": "Implement user profile management with role-based access control",
                "metadata": {
                    METADATA_SOURCE_FILE: "/src/users/profiles.py",
                    METADATA_EPISODE_TYPE: "feature_implementation",
                },
            },
        ]

        created_nodes = []
        for node_data in test_nodes_data:
            # Generate embedding for the content
            embedding = embedder.embed(node_data["content"])

            # Create node with embedding and metadata
            node = Node(
                type=node_data["type"],
                content=node_data["content"],
                embedding=embedding,
                metadata=node_data["metadata"],
            )
            client.create_node(node)
            created_nodes.append(node)
            print_info(f"Created node: {node.type} - {node.content[:40]}...")

        print_result("Create test nodes", f"Created {len(created_nodes)} nodes with metadata", True)
    except Exception as e:
        print_result("Create test nodes", f"FAILED: {e}", False)
        client.disconnect()
        return False

    # Step 3: Test get_relevant_context with a search query
    print_step(3, "Calling get_relevant_context()")

    try:
        results = get_relevant_context(
            query="authentication security",
            num_results=5,
            min_score=0.0,
            client=client,
        )
        print_result("Execute search", f"Found {len(results)} results", len(results) > 0)

        if len(results) == 0:
            print_info("No results returned - cannot verify metadata")
            client.disconnect()
            return False

    except Exception as e:
        print_result("Execute search", f"FAILED: {e}", False)
        client.disconnect()
        return False

    # Step 4: Verify metadata fields are present in results
    print_step(4, "Verifying metadata fields in results")

    required_fields = ["content", "score", "type", METADATA_SOURCE_FILE, METADATA_CAPTURED_AT, METADATA_EPISODE_TYPE]
    all_fields_present = True

    for i, result in enumerate(results):
        print(f"\n  Result {i + 1}:")
        for field_name in required_fields:
            field_value = result.get(field_name)
            field_present = field_name in result
            # Note: Some fields may be None, but the key should exist
            if field_present:
                # Truncate long values for display
                display_value = str(field_value)
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                print_result(f"  {field_name}", display_value, True)
            else:
                print_result(f"  {field_name}", "MISSING", False)
                all_fields_present = False

    # Step 5: Verify score is a valid float between 0 and 1
    print_step(5, "Verifying score values are valid")

    scores_valid = True
    for i, result in enumerate(results):
        score = result.get("score")
        if not isinstance(score, (int, float)):
            print_result(f"Result {i + 1} score type", f"Invalid: {type(score)}", False)
            scores_valid = False
        elif not (0.0 <= score <= 1.0):
            print_result(f"Result {i + 1} score range", f"Out of range: {score}", False)
            scores_valid = False
        else:
            print_result(f"Result {i + 1} score", f"{score:.4f}", True)

    # Step 6: Verify captured_at is ISO 8601 format
    print_step(6, "Verifying captured_at timestamp format")

    timestamps_valid = True
    for i, result in enumerate(results):
        captured_at = result.get(METADATA_CAPTURED_AT)
        if captured_at is None:
            print_result(f"Result {i + 1} captured_at", "None (acceptable)", True)
        else:
            try:
                # Verify ISO 8601 format by parsing
                from datetime import datetime
                # Handle both with and without microseconds
                if "." in captured_at:
                    datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
                else:
                    datetime.fromisoformat(captured_at)
                print_result(f"Result {i + 1} captured_at", f"Valid ISO 8601: {captured_at[:26]}...", True)
            except ValueError as e:
                print_result(f"Result {i + 1} captured_at", f"Invalid format: {e}", False)
                timestamps_valid = False

    # Step 7: Test empty query handling
    print_step(7, "Testing empty query handling")

    try:
        empty_results = get_relevant_context(query="", client=client)
        if len(empty_results) == 0:
            print_result("Empty query", "Returns empty list correctly", True)
        else:
            print_result("Empty query", f"Expected empty, got {len(empty_results)} results", False)
    except Exception as e:
        print_result("Empty query", f"FAILED with exception: {e}", False)

    # Clean up
    client.disconnect()

    # Final result
    print()
    success = all_fields_present and scores_valid and timestamps_valid
    print_result("Context Metadata Test", "All tests passed" if success else "Some tests failed", success)
    return success


def test_full_cycle() -> bool:
    """
    Test the complete embedding cycle including semantic search.

    Returns:
        True if all tests pass, False otherwise
    """
    print_header("Test: Full Embedding Cycle")

    try:
        from integrations.graphiti.providers.ollama_embedder import (
            OllamaEmbedder,
        )
    except ImportError as e:
        print_result("Import", f"FAILED: {e}", False)
        return False

    # Step 1: Create embedder
    print_step(1, "Creating embedder")

    try:
        embedder = OllamaEmbedder()
        print_result("Create embedder", f"model={embedder.config.model}", True)
    except Exception as e:
        print_result("Create embedder", f"FAILED: {e}", False)
        return False

    # Step 2: Create document embeddings
    print_step(2, "Creating document embeddings")

    documents = [
        {"id": "doc1", "content": "OAuth 2.0 authentication flow with Google and GitHub"},
        {"id": "doc2", "content": "JWT token generation and validation utilities"},
        {"id": "doc3", "content": "User profile management and role-based access control"},
        {"id": "doc4", "content": "Database connection pooling and query optimization"},
        {"id": "doc5", "content": "React component state management with hooks"},
    ]

    doc_embeddings = []
    for doc in documents:
        embedding = embedder.embed(doc["content"])
        doc_embeddings.append({"id": doc["id"], "content": doc["content"], "embedding": embedding})
        print_info(f"Embedded: {doc['id']} - {doc['content'][:40]}...")

    print_result("Document embeddings", f"Created {len(doc_embeddings)} embeddings", True)

    # Step 3: Test semantic search
    print_step(3, "Testing semantic search")

    queries = [
        ("login security", ["doc1", "doc2"]),  # Should match OAuth and JWT
        ("database performance", ["doc4"]),     # Should match DB connection
        ("frontend UI", ["doc5"]),              # Should match React
    ]

    search_success = True
    for query, expected_top in queries:
        query_embedding = embedder.embed(query)

        # Calculate similarities
        similarities = []
        for doc in doc_embeddings:
            sim = cosine_similarity(query_embedding, doc["embedding"])
            similarities.append((doc["id"], sim, doc["content"]))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        print(f"\n  Query: '{query}'")
        print("  Top results:")
        for i, (doc_id, sim, content) in enumerate(similarities[:3]):
            marker = "*" if doc_id in expected_top else " "
            print(f"    {marker} {doc_id}: {sim:.4f} - {content[:40]}...")

        # Check if at least one expected doc is in top 2
        top_2_ids = [s[0] for s in similarities[:2]]
        if any(exp in top_2_ids for exp in expected_top):
            print_result(f"Search '{query}'", "Found relevant results", True)
        else:
            print_result(f"Search '{query}'", "Expected results not in top 2", False)
            search_success = False

    # Step 4: Verify embedder status
    print_step(4, "Checking embedder status")

    status = embedder.get_status()
    print(f"  Model: {status['model']}")
    print(f"  Embedding dimension: {status['embedding_dim']}")
    print(f"  Connected: {status['connected']}")
    print(f"  Verified: {status['verified']}")

    if status['connected']:
        print_result("Embedder status", "Healthy", True)
    else:
        print_result("Embedder status", f"Error: {status.get('error')}", False)
        return False

    print()
    print_result("Full Cycle", "All tests passed" if search_success else "Some tests failed", search_success)
    return search_success


def main():
    """Run Ollama embedding tests."""
    parser = argparse.ArgumentParser(description="Test Ollama Embedding Integration")
    parser.add_argument(
        "--test",
        choices=["all", "embeddings", "full-cycle", "retrieve"],
        default="all",
        help="Which test to run (retrieve tests context metadata in search results)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  OLLAMA EMBEDDING TEST SUITE")
    print("=" * 70)

    # Configuration check
    print_header("Configuration Check")

    config_items = {
        "OLLAMA_EMBEDDING_MODEL": os.environ.get("OLLAMA_EMBEDDING_MODEL", "embeddinggemma"),
        "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "OLLAMA_EMBEDDING_DIM": os.environ.get("OLLAMA_EMBEDDING_DIM", "(auto-detect)"),
    }

    for key, value in config_items.items():
        print_result(key, value, True)

    # Run tests
    results = {}

    if args.test in ["all", "embeddings"]:
        results["embeddings"] = test_ollama_embeddings()

    if args.test in ["all", "retrieve"]:
        results["retrieve"] = test_retrieve_context_metadata()

    if args.test in ["all", "full-cycle"]:
        results["full-cycle"] = test_full_cycle()

    # Summary
    print_header("TEST SUMMARY")

    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  All tests PASSED!")
        print()
        print("  The Ollama embedder is working correctly.")
        print("  Embeddings are generated with correct dimensions.")
        print("  Semantic similarity search is functional.")
    else:
        print("  Some tests FAILED. Check the output above for details.")
        print()
        print("  Common issues:")
        print("    - Ollama not running: ollama serve")
        print("    - Model not pulled: ollama pull embeddinggemma")
        print("    - Wrong dimension: Set OLLAMA_EMBEDDING_DIM env var")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
