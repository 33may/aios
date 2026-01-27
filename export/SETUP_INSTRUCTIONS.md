# Setup Instructions for Knowledge Management Agent

## Quick Start

### 1. Clone the Repository

```bash
git clone git@github.com:33may/aios.git
cd aios
git checkout feature/knowledge-restructure
```

### 2. Set Up Neo4j

```bash
cd deploy/neo4j
docker compose up -d
```

Wait for Neo4j to be healthy:
```bash
docker compose logs -f  # Watch until you see "Started"
# Or check health:
docker ps --filter "name=knowledge-neo4j"
```

Neo4j will be available at:
- Browser UI: http://localhost:7474
- Bolt: bolt://localhost:7687
- Credentials: `neo4j` / `devpassword`

### 3. Import Knowledge Graph Data

Copy the exported data into the container and import:

```bash
# Copy import file to container
docker cp ../export/knowledge_graph_import.cypher knowledge-neo4j:/var/lib/neo4j/import/

# Run import
docker exec -it knowledge-neo4j cypher-shell -u neo4j -p devpassword < ../export/knowledge_graph_import.cypher
```

Or via Neo4j Browser (http://localhost:7474):
1. Open the browser
2. Paste the contents of `knowledge_graph_import.cypher`
3. Run

### 4. Create Environment File

Create `.env` in the project root:

```bash
cat > .env << 'EOF'
# Knowledge Graph Configuration
KNOWLEDGE_BACKEND=neo4j
KNOWLEDGE_DB_HOST=localhost
KNOWLEDGE_DB_PORT=5432
KNOWLEDGE_DB_NAME=knowledge_graph
KNOWLEDGE_DB_USER=knowledge
KNOWLEDGE_DB_PASSWORD=devpassword
EOF
```

### 5. Set Up Python Environment

```bash
# Using conda (recommended)
conda create -n aios python=3.11
conda activate aios

# Install dependencies
pip install -e apps/mcp
# Or if there's a requirements.txt:
pip install -r requirements.txt
```

### 6. Configure Claude Code MCP Server

Add to your Claude Code settings (`~/.claude.json` or project `.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "knowledge": {
      "command": "python",
      "args": ["-m", "apps.mcp.knowledge_server"],
      "cwd": "/path/to/aios",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "devpassword"
      }
    }
  }
}
```

### 7. Verify Setup

Start Claude Code and test the knowledge tools:
```
# In Claude Code conversation:
"Search the knowledge graph for recent decisions"
```

## Project Structure

```
aios/
├── apps/
│   ├── mcp/                    # MCP Server for Claude Code
│   │   ├── knowledge_server.py # Main server
│   │   ├── tools/              # Tool implementations
│   │   └── hooks/              # Claude Code hooks
│   └── backend/
│       └── integrations/
│           └── graphiti/       # Knowledge graph backends
├── deploy/
│   └── neo4j/                  # Docker setup for Neo4j
├── export/                     # This folder - exported data
│   ├── knowledge_graph_import.cypher
│   └── SETUP_INSTRUCTIONS.md
├── .claude/
│   ├── agents/                 # Custom agent definitions
│   ├── commands/               # Slash commands (e.g., /research)
│   └── settings.local.json     # Project-specific Claude settings
├── CLAUDE.md                   # Claude Code instructions
└── .env                        # Environment variables (create this)
```

## Knowledge Graph Stats (as of export)

| Node Type   | Count |
|-------------|-------|
| Thought     | 63    |
| Discovery   | 32    |
| Task        | 25    |
| Decision    | 22    |
| Session     | 15    |
| Constraint  | 13    |
| Fix         | 6     |
| Problem     | 5     |
| Project     | 2     |
| Context     | 1     |
| **Total**   | **184** |

## Troubleshooting

### Port Already in Use

If port 7474 or 7687 is already in use:
```bash
# Find what's using the port
sudo lsof -i :7474

# Kill the process or change ports in docker-compose.yml
```

### Neo4j Won't Start

Check logs:
```bash
docker compose logs neo4j
```

### MCP Server Not Connecting

1. Check Neo4j is running: `docker ps`
2. Test connection: `docker exec knowledge-neo4j cypher-shell -u neo4j -p devpassword "RETURN 1"`
3. Verify environment variables are set

### Import Errors

If you see constraint errors during import, the data may already exist. You can clear the database first:
```bash
docker exec knowledge-neo4j cypher-shell -u neo4j -p devpassword "MATCH (n) DETACH DELETE n"
```

Then re-run the import.

## Using the Knowledge System

Once set up, Claude Code will automatically have access to knowledge tools. Key patterns:

1. **Start sessions** with `initialize_session` to get context
2. **Record thoughts** as you analyze problems
3. **Capture constraints** when you state preferences
4. **Record decisions** with rationale
5. **Document problems and fixes** when debugging

See `CLAUDE.md` for full documentation on the knowledge-centric workflow.
