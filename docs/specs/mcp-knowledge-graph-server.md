# Task: Build MCP Server for Knowledge Graph Integration with Claude Code

## Goal

Build an MCP (Model Context Protocol) server that exposes the existing Graphiti knowledge graph to Claude Code. This enables Claude Code to act as a **project manager** with persistent memory about decisions, tasks, context, and project history.

## Background

We have an existing knowledge graph infrastructure:
- **Location**: `apps/backend/integrations/graphiti/`
- **Components**:
  - `client.py` - GraphitiClient for CRUD operations on nodes/edges
  - `queries.py` - High-level query functions (semantic search, temporal queries, traversal)
  - `models.py` - Node and Edge dataclasses
  - `config.py` - Configuration management

The knowledge graph stores:
- **Decisions** - Why we chose X over Y, with rationale and alternatives
- **Tasks** - Work items with status, blockers, dependencies
- **Sessions** - Conversation/work session history
- **Discoveries** - Insights and learnings during development
- **Projects** - Project metadata and hierarchical scope

## Deliverable

An MCP server (`apps/mcp/knowledge_server.py`) that Claude Code can connect to via `~/.claude/claude_desktop_config.json` or project-level `.mcp.json`.

## MCP Tools to Implement

### 1. `search_knowledge`
Semantic search across all knowledge.
```
Input:
  - query: string (natural language question)
  - limit: int (default 10)
  - min_score: float (default 0.0)

Output:
  - results: array of {content, type, score, source_file, captured_at}
```

### 2. `get_decisions`
Retrieve architectural/design decisions.
```
Input:
  - project_id: string (optional, for scoping)
  - days: int (default 90, how far back to look)
  - limit: int (default 20)

Output:
  - decisions: array of {title, rationale, alternatives, date, related_tasks}
```

### 3. `get_tasks`
Retrieve tasks from the knowledge graph.
```
Input:
  - status: string (optional: "pending", "in_progress", "completed", "blocked")
  - project_id: string (optional)
  - days: int (default 30)

Output:
  - tasks: array of {subject, description, status, blockers, created_at}
```

### 4. `get_recent_activity`
Get recent activity across all types.
```
Input:
  - hours: int (default 24)
  - types: array of string (optional filter: ["decision", "task", "discovery"])

Output:
  - activity: array of {type, content, timestamp}
```

### 5. `record_decision`
Record a new decision to the knowledge graph.
```
Input:
  - title: string
  - rationale: string (why this choice)
  - alternatives: array of string (what was considered)
  - context: string (optional, what prompted this decision)

Output:
  - decision_id: string
```

### 6. `add_task`
Add a new task to the knowledge graph.
```
Input:
  - subject: string
  - description: string
  - status: string (default "pending")
  - blocked_by: array of string (optional task IDs)

Output:
  - task_id: string
```

### 7. `update_task`
Update an existing task.
```
Input:
  - task_id: string
  - status: string (optional)
  - description: string (optional)

Output:
  - success: boolean
```

### 8. `add_discovery`
Record a learning or insight.
```
Input:
  - content: string (what was learned)
  - context: string (optional, where/how it was discovered)
  - tags: array of string (optional)

Output:
  - discovery_id: string
```

### 9. `get_project_context`
Get comprehensive context for current project.
```
Input:
  - project_id: string (optional, auto-detect from cwd if not provided)

Output:
  - project: {name, description, recent_decisions, active_tasks, key_discoveries}
```

### 10. `traverse_related`
Explore relationships from a node.
```
Input:
  - node_id: string
  - depth: int (default 1)
  - edge_types: array of string (optional filter)

Output:
  - nodes: array of {id, type, content, relationship}
```

## Technical Requirements

### MCP Server Setup
Use the official MCP Python SDK: `pip install mcp`

Basic server structure:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("knowledge-graph")

@app.list_tools()
async def list_tools():
    return [
        Tool(name="search_knowledge", description="...", inputSchema={...}),
        # ... other tools
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_knowledge":
        return await search_knowledge(**arguments)
    # ... handle other tools

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)
```

### Integration with Existing Code
- Import and use `GraphitiClient` from `apps.backend.integrations.graphiti.client`
- Use query functions from `apps.backend.integrations.graphiti.queries`
- Maintain a persistent client connection for the server lifetime

### Configuration
The MCP server should be configurable via:
- Environment variables (GRAPHITI_HOST, GRAPHITI_PORT, etc.)
- Fall back to defaults from existing `GraphitiConfig`

### Claude Code Integration
After implementation, users configure in `~/.claude.json` or project `.mcp.json`:
```json
{
  "mcpServers": {
    "knowledge": {
      "command": "python",
      "args": ["-m", "apps.mcp.knowledge_server"],
      "cwd": "/path/to/management_agent"
    }
  }
}
```

## File Structure
```
apps/mcp/
├── __init__.py
├── knowledge_server.py    # Main MCP server
├── tools/
│   ├── __init__.py
│   ├── search.py          # search_knowledge, get_project_context
│   ├── decisions.py       # get_decisions, record_decision
│   ├── tasks.py           # get_tasks, add_task, update_task
│   ├── activity.py        # get_recent_activity, add_discovery
│   └── traversal.py       # traverse_related
└── utils.py               # Shared utilities, serialization helpers
```

## Testing
- Unit tests for each tool function
- Integration test that starts the MCP server and makes tool calls
- Test with actual Claude Code connection

## Success Criteria
1. MCP server starts without errors
2. All 10 tools are listed when Claude Code connects
3. `search_knowledge` returns relevant results from the graph
4. `record_decision` and `add_task` persist to the graph
5. Claude Code can use these tools naturally in conversation

## References
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP Specification: https://spec.modelcontextprotocol.io/
- Existing Graphiti code: `apps/backend/integrations/graphiti/`
