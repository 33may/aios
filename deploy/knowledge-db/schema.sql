-- Knowledge Graph Schema for PostgreSQL + pgvector
--
-- Run this to initialize the database:
--   psql -h localhost -U knowledge -d knowledge_graph -f schema.sql

-- Enable pgvector extension (requires superuser or extension already installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables if recreating
-- DROP TABLE IF EXISTS edges CASCADE;
-- DROP TABLE IF EXISTS nodes CASCADE;

-- Nodes table
CREATE TABLE IF NOT EXISTS nodes (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension, adjust as needed
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT nodes_type_not_empty CHECK (type != ''),
    CONSTRAINT nodes_content_not_empty CHECK (content != '')
);

-- Node indexes
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_updated ON nodes(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_metadata ON nodes USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_nodes_metadata_project ON nodes((metadata->>'project_id'));
CREATE INDEX IF NOT EXISTS idx_nodes_metadata_status ON nodes((metadata->>'status'));

-- Vector similarity index (IVFFlat - good balance of speed and accuracy)
-- Requires at least 100 rows before creation, so we create it conditionally
-- For production, run this after initial data load:
-- CREATE INDEX idx_nodes_embedding ON nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- For small datasets, use exact search (no index needed) or hnsw:
CREATE INDEX IF NOT EXISTS idx_nodes_embedding_hnsw ON nodes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Edges table
CREATE TABLE IF NOT EXISTS edges (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES nodes(uuid) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT edges_type_not_empty CHECK (type != ''),
    CONSTRAINT edges_no_self_loops CHECK (source_id != target_id)
);

-- Edge indexes
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_source_type ON edges(source_id, type);
CREATE INDEX IF NOT EXISTS idx_edges_target_type ON edges(target_id, type);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to nodes
DROP TRIGGER IF EXISTS nodes_updated_at_trigger ON nodes;
CREATE TRIGGER nodes_updated_at_trigger
    BEFORE UPDATE ON nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to edges
DROP TRIGGER IF EXISTS edges_updated_at_trigger ON edges;
CREATE TRIGGER edges_updated_at_trigger
    BEFORE UPDATE ON edges
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Useful views

-- Recent activity view
CREATE OR REPLACE VIEW recent_activity AS
SELECT
    uuid,
    type,
    LEFT(content, 200) as content_preview,
    metadata->>'title' as title,
    metadata->>'subject' as subject,
    metadata->>'status' as status,
    created_at,
    updated_at
FROM nodes
ORDER BY created_at DESC
LIMIT 100;

-- Tasks view
CREATE OR REPLACE VIEW tasks AS
SELECT
    uuid,
    content,
    metadata->>'subject' as subject,
    metadata->>'status' as status,
    metadata->>'project_id' as project_id,
    metadata->>'blocked_by' as blocked_by,
    created_at,
    updated_at
FROM nodes
WHERE type = 'task'
ORDER BY created_at DESC;

-- Decisions view
CREATE OR REPLACE VIEW decisions AS
SELECT
    uuid,
    content,
    metadata->>'title' as title,
    metadata->>'rationale' as rationale,
    metadata->>'alternatives' as alternatives,
    metadata->>'context' as context,
    metadata->>'project_id' as project_id,
    created_at,
    updated_at
FROM nodes
WHERE type = 'decision'
ORDER BY created_at DESC;

-- Sessions view
CREATE OR REPLACE VIEW sessions AS
SELECT
    uuid,
    LEFT(content, 500) as summary,
    metadata->>'session_id' as session_id,
    metadata->>'end_reason' as end_reason,
    metadata->>'prompt_count' as prompt_count,
    metadata->>'tool_count' as tool_count,
    created_at
FROM nodes
WHERE type = 'session'
ORDER BY created_at DESC;

-- Grant permissions (adjust user as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO knowledge;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO knowledge;

-- Show summary
DO $$
BEGIN
    RAISE NOTICE 'Knowledge graph schema initialized successfully';
    RAISE NOTICE 'Tables: nodes, edges';
    RAISE NOTICE 'Views: recent_activity, tasks, decisions, sessions';
END $$;
