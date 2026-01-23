# Knowledge Graph Persistence Architecture

## Goal
Persistent knowledge graph that works seamlessly across laptop and PC, with home PC as the server.

## Architecture

```
┌─────────────┐         ┌─────────────────────────────┐
│   Laptop    │         │     Home PC (Server)        │
│             │  LAN/   │                             │
│ Claude Code │◄──────► │  PostgreSQL + pgvector      │
│ + MCP       │  VPN    │  (port 5432)                │
│             │         │                             │
└─────────────┘         └─────────────────────────────┘
        │                           ▲
        │                           │
        ▼                           │
┌─────────────┐                     │
│     PC      │─────────────────────┘
│             │  localhost
│ Claude Code │
│ + MCP       │
│             │
└─────────────┘
```

## Why PostgreSQL + pgvector

| Option | Pros | Cons |
|--------|------|------|
| **PostgreSQL + pgvector** | Simple deployment, vector search, proven, single DB for all | Not native graph |
| Neo4j | Native graph queries | Heavier, separate service |
| SQLite | Zero deployment | Single machine only |
| MongoDB | Flexible schema | No native vectors |

**Decision: PostgreSQL with pgvector**
- Single database for nodes, edges, and vector embeddings
- Native vector similarity search via pgvector
- Easy to deploy on home server
- Standard SQL for simple queries
- Can add graph extensions (Apache AGE) later if needed

## Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Nodes table
CREATE TABLE nodes (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- For semantic search (OpenAI ada-002 size)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    project_id VARCHAR(255)  -- For multi-project support
);

-- Indexes
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_nodes_project ON nodes(project_id);
CREATE INDEX idx_nodes_created ON nodes(created_at DESC);
CREATE INDEX idx_nodes_metadata ON nodes USING GIN(metadata);

-- Vector similarity index (IVFFlat for faster search)
CREATE INDEX idx_nodes_embedding ON nodes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Edges table
CREATE TABLE edges (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT no_self_loops CHECK (source_id != target_id)
);

-- Indexes
CREATE INDEX idx_edges_type ON edges(type);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_source_type ON edges(source_id, type);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER nodes_updated_at
    BEFORE UPDATE ON nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER edges_updated_at
    BEFORE UPDATE ON edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

## Configuration

Environment variables for connection:

```bash
# On laptop (remote connection)
KNOWLEDGE_DB_HOST=192.168.1.100  # Home PC IP or hostname
KNOWLEDGE_DB_PORT=5432
KNOWLEDGE_DB_NAME=knowledge_graph
KNOWLEDGE_DB_USER=knowledge
KNOWLEDGE_DB_PASSWORD=<secure-password>

# On home PC (localhost)
KNOWLEDGE_DB_HOST=localhost
KNOWLEDGE_DB_PORT=5432
KNOWLEDGE_DB_NAME=knowledge_graph
KNOWLEDGE_DB_USER=knowledge
KNOWLEDGE_DB_PASSWORD=<secure-password>
```

## Deployment (Home PC Server)

### 1. Install PostgreSQL + pgvector

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Install pgvector
sudo apt install postgresql-16-pgvector  # or build from source

# Or via Docker (recommended)
docker run -d \
  --name knowledge-pg \
  -e POSTGRES_USER=knowledge \
  -e POSTGRES_PASSWORD=<secure-password> \
  -e POSTGRES_DB=knowledge_graph \
  -p 5432:5432 \
  -v knowledge_data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16
```

### 2. Configure Remote Access

```bash
# Edit pg_hba.conf to allow connections from local network
# Add line:
host    knowledge_graph    knowledge    192.168.1.0/24    scram-sha-256

# Edit postgresql.conf
listen_addresses = '*'

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. Initialize Schema

```bash
psql -h localhost -U knowledge -d knowledge_graph -f schema.sql
```

## Offline Support (Future)

For working offline on laptop:
1. Local SQLite cache of recent data
2. Sync queue for writes when offline
3. Sync on reconnection

Not implementing now - can add later if needed.

## File Structure

```
apps/backend/integrations/graphiti/
├── client.py           # Updated with PostgreSQL backend
├── backends/
│   ├── __init__.py
│   ├── base.py         # Abstract backend interface
│   ├── memory.py       # In-memory (current, for testing)
│   └── postgres.py     # PostgreSQL + pgvector
├── config.py           # Database configuration
├── models.py           # Unchanged
├── queries.py          # Unchanged (uses client abstraction)
└── schema.sql          # Database schema
```
