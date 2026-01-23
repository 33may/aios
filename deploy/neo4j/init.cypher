// Knowledge Graph Schema for Neo4j
// Run this after Neo4j starts to set up constraints and indexes

// ============================================
// Node Uniqueness Constraints
// ============================================

// Primary node types
CREATE CONSTRAINT decision_uuid IF NOT EXISTS FOR (d:Decision) REQUIRE d.uuid IS UNIQUE;
CREATE CONSTRAINT task_uuid IF NOT EXISTS FOR (t:Task) REQUIRE t.uuid IS UNIQUE;
CREATE CONSTRAINT session_uuid IF NOT EXISTS FOR (s:Session) REQUIRE s.uuid IS UNIQUE;
CREATE CONSTRAINT concept_uuid IF NOT EXISTS FOR (c:Concept) REQUIRE c.uuid IS UNIQUE;
CREATE CONSTRAINT discovery_uuid IF NOT EXISTS FOR (d:Discovery) REQUIRE d.uuid IS UNIQUE;
CREATE CONSTRAINT project_uuid IF NOT EXISTS FOR (p:Project) REQUIRE p.uuid IS UNIQUE;

// ============================================
// Indexes for Common Queries
// ============================================

// Type-based indexes for fast filtering
CREATE INDEX decision_created IF NOT EXISTS FOR (d:Decision) ON (d.created_at);
CREATE INDEX task_created IF NOT EXISTS FOR (t:Task) ON (t.created_at);
CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status);
CREATE INDEX session_created IF NOT EXISTS FOR (s:Session) ON (s.created_at);
CREATE INDEX discovery_created IF NOT EXISTS FOR (d:Discovery) ON (d.created_at);

// Project-scoped queries
CREATE INDEX decision_project IF NOT EXISTS FOR (d:Decision) ON (d.project_id);
CREATE INDEX task_project IF NOT EXISTS FOR (t:Task) ON (t.project_id);
CREATE INDEX session_project IF NOT EXISTS FOR (s:Session) ON (s.project_id);

// Full-text search indexes
CREATE FULLTEXT INDEX node_content IF NOT EXISTS FOR (n:Decision|Task|Session|Discovery|Concept) ON EACH [n.content, n.title];

// ============================================
// Edge Types (Documentation)
// ============================================
// The following relationship types are used in the graph:
//
// RELATES_TO    - General semantic relationship between nodes
// BLOCKS        - Task A blocks Task B (dependency)
// SPAWNED       - Session spawned a Decision/Task/Discovery
// REFERENCES    - Node references another node
// LED_TO        - Decision led to another Decision or Task
// CONTAINS      - Project contains Session/Decision/Task
// SIMILAR_TO    - Nodes with high embedding similarity (created by linker agent)
//
// Example relationships:
// (session:Session)-[:SPAWNED]->(decision:Decision)
// (decision:Decision)-[:LED_TO]->(task:Task)
// (task:Task)-[:BLOCKS]->(other_task:Task)
// (project:Project)-[:CONTAINS]->(session:Session)
// (concept:Concept)-[:RELATES_TO]->(decision:Decision)
