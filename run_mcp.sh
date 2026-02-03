#!/bin/bash
#
# Knowledge Graph MCP Server Startup Script
#
# Ensures all dependencies (Neo4j, Ollama) are running before starting
# the MCP server. Ollama provides local embeddings for semantic search.
#

set -e

cd /home/may33/projects/aios

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if Ollama is running, start if not
check_ollama() {
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

ensure_ollama() {
    echo "Checking Ollama..." >&2

    if check_ollama; then
        echo "Ollama is running" >&2
    else
        echo "Starting Ollama..." >&2
        # Try to start Ollama in the background
        if command -v ollama &> /dev/null; then
            ollama serve &> /tmp/ollama.log &
            OLLAMA_PID=$!

            # Wait for Ollama to be ready (max 30 seconds)
            for i in {1..30}; do
                if check_ollama; then
                    echo "Ollama started successfully" >&2
                    break
                fi
                sleep 1
            done

            if ! check_ollama; then
                echo "Warning: Ollama failed to start. Semantic search will be limited." >&2
            fi
        else
            echo "Warning: Ollama not installed. Semantic search will be limited." >&2
            echo "Install with: curl -fsSL https://ollama.com/install.sh | sh" >&2
        fi
    fi

    # Ensure embedding model is available
    if check_ollama; then
        MODEL=${OLLAMA_EMBEDDING_MODEL:-embeddinggemma}
        echo "Checking embedding model: $MODEL" >&2

        # Check if model exists
        if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
            echo "Pulling embedding model: $MODEL (this may take a while)..." >&2
            ollama pull "$MODEL" >&2
        fi
    fi
}

# Ensure Neo4j is running (via docker-compose)
check_neo4j() {
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

ensure_neo4j() {
    echo "Checking Neo4j..." >&2

    if check_neo4j; then
        echo "Neo4j is running" >&2
    else
        echo "Starting Neo4j via docker-compose..." >&2
        if [ -f deploy/neo4j/docker-compose.yml ]; then
            docker-compose -f deploy/neo4j/docker-compose.yml up -d neo4j

            # Wait for Neo4j to be ready (max 60 seconds)
            for i in {1..60}; do
                if check_neo4j; then
                    echo "Neo4j started successfully" >&2
                    break
                fi
                sleep 1
            done

            if ! check_neo4j; then
                echo "Error: Neo4j failed to start" >&2
                exit 1
            fi
        else
            echo "Error: docker-compose.yml not found" >&2
            exit 1
        fi
    fi
}

# Main startup
ensure_neo4j
ensure_ollama

# Start the MCP server
exec /home/may33/miniconda3/envs/aios/bin/python -m apps.mcp.knowledge_server
