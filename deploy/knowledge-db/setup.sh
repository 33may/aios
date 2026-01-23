#!/bin/bash
# Knowledge Graph Database Setup
#
# Run this on your home server to set up the PostgreSQL database.
#
# Usage:
#   ./setup.sh                    # Uses default password
#   KNOWLEDGE_DB_PASSWORD=secret ./setup.sh  # Custom password

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default password (change in production!)
export KNOWLEDGE_DB_PASSWORD="${KNOWLEDGE_DB_PASSWORD:-changeme}"

echo "=== Knowledge Graph Database Setup ==="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Use docker compose v2 if available
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

echo "1. Starting PostgreSQL container..."
$COMPOSE up -d db

echo ""
echo "2. Waiting for database to be ready..."
sleep 5

# Wait for healthy
for i in {1..30}; do
    if $COMPOSE exec -T db pg_isready -U knowledge -d knowledge_graph &> /dev/null; then
        echo "   Database is ready!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "3. Initializing schema..."
$COMPOSE exec -T db psql -U knowledge -d knowledge_graph -f /schema/schema.sql

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Database is running at: localhost:5432"
echo "  Database: knowledge_graph"
echo "  User: knowledge"
echo "  Password: $KNOWLEDGE_DB_PASSWORD"
echo ""
echo "To connect from another machine, update your .env:"
echo "  KNOWLEDGE_BACKEND=postgres"
echo "  KNOWLEDGE_DB_HOST=<this-server-ip>"
echo "  KNOWLEDGE_DB_PORT=5432"
echo "  KNOWLEDGE_DB_NAME=knowledge_graph"
echo "  KNOWLEDGE_DB_USER=knowledge"
echo "  KNOWLEDGE_DB_PASSWORD=$KNOWLEDGE_DB_PASSWORD"
echo ""
echo "To stop: $COMPOSE down"
echo "To view logs: $COMPOSE logs -f db"
