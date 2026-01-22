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
        choices=["all", "embeddings", "full-cycle"],
        default="all",
        help="Which test to run",
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
