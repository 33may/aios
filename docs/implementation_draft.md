# AIOS Technical Stack - Auto-Claude Foundation

## Overview

AIOS is built by adapting the Auto-Claude codebase. Auto-Claude is an open-source multi-agent framework with:
- Semantic memory (Graphiti + LadybugDB)
- Task orchestration (SpecOrchestrator)
- Claude SDK integration
- Isolated workspaces (Git Worktrees)

~85% of the infrastructure is reusable. We adapt the domain from "code management" to "knowledge management".

---

## Core Components

### 1. Graphiti + LadybugDB (Knowledge Graph)

**What it is:** Persistent semantic memory system backed by embedded graph database.

**How it works:**
- Stores facts as nodes in a graph
- Relationships as edges (with timestamps)
- Embedding vectors for semantic search
- Queries return related context automatically

**Key insight:** The technology is content-agnostic. Currently stores code entities (functions, classes). We store knowledge entities (projects, tasks, ideas, decisions, sessions).

#### Two Search Modes (Hybrid Approach)

**1. Semantic/Flat Search** (brain-like associations)
- Query by meaning, not structure
- "motor control" → returns ALL semantically related nodes
- Works across hierarchy - finds related ideas, decisions, notes
- Primary mode for discovery and recall

**2. Hierarchical Scoping** (structured filtering)
- Use hierarchy to SCOPE the search first
- "Find nodes under robotics project" → then search within
- Prevents cross-contamination between unrelated projects
- Good for focused work sessions

**Combined Query Pattern:**
```
scope(project: "robotics") + search("motor issues")
→ Step 1: Get all nodes contained in robotics project
→ Step 2: Semantic search "motor issues" within that set
→ Result: Only robotics-related motor content
```

**Embedding providers:**
- Ollama (local, recommended for privacy)
- OpenAI (optional)

**Configuration:**
```
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**Location:** `apps/backend/integrations/graphiti/`

---

### 2. claude-agent-sdk (AI Interface)

**What it is:** SDK for interfacing with Anthropic's Claude models. Handles API complexity, retries, streaming, tool definitions.

**Key file:** `apps/backend/core/client.py`

**The `create_client()` function:**
- Factory for instantiating ClaudeSDKClient
- Security hooks (sandboxing)
- Dynamic MCP server injection
- Token budget management ("thinking" tokens for extended reasoning)

**What we keep:** Session management, auth handling, error wrapping - all domain-agnostic.

**What we change:** The `allowed_tools` list and MCP server configuration.

---

### 3. SpecOrchestrator (Task Lifecycle)

**What it is:** State machine that manages task lifecycle from start to completion.

**Current states:** `PLANNING -> CODING -> REVIEW -> DONE`

**Key file:** `apps/backend/runners/spec_runner.py`

**How it works:**
- Reads requirement/task
- Breaks down into subtasks (DAG structure)
- Assigns to agents
- Tracks completion
- Persists state to JSON files

**For AIOS:** Adapt states for knowledge sessions:
`CONTEXT_LOAD -> WORKING -> EXTRACTION -> STORED`

---

### 4. Agents Structure

**Location:** `apps/backend/agents/`

**Current agents:**
- `planner.py` - Creates plans from requirements
- `coder.py` - Executes tasks, handles retries
- `qa_reviewer.py` - Validates output
- `qa_fixer.py` - Fixes issues

**Each agent has:**
- Specific loop logic
- System prompt (in `apps/backend/prompts/`)
- Tool permissions

**For AIOS:** Adapt agents for knowledge management:
- Context loader (load relevant graph nodes)
- Session tracker (observe work, extract insights)
- Knowledge updater (write to graph)

---

### 5. Git Worktrees (Isolation)

**What it is:** Git feature for multiple working directories from same repo.

**Current use:** Isolates agent environments so multiple agents can work simultaneously.

**For AIOS:** Can use for:
- Isolated project contexts
- "What-if" scenario branches
- Safe experimentation before committing to main knowledge graph

---

### 6. Frontend (Electron + React)

**Location:** `apps/frontend/`

**Components:**
- KanbanBoard - task visualization
- TaskCard - individual task display
- ChatInterface - conversation view
- Terminal view - agent activity stream

**For AIOS:** Adapt as knowledge graph viewer:
- Graph visualization instead of Kanban
- Node/edge browser
- Session history view

---

## File Structure Reference

```
Auto-Claude/
├── apps/
│   ├── backend/
│   │   ├── core/
│   │   │   ├── client.py         # Claude SDK setup
│   │   │   └── security.py       # Sandboxing logic
│   │   ├── runners/
│   │   │   └── spec_runner.py    # SpecOrchestrator
│   │   ├── agents/
│   │   │   ├── planner.py
│   │   │   ├── coder.py
│   │   │   ├── qa_reviewer.py
│   │   │   └── qa_fixer.py
│   │   ├── integrations/
│   │   │   └── graphiti/         # Knowledge graph
│   │   └── prompts/              # System prompts (.md files)
│   └── frontend/                 # Electron + React
├── requirements.txt
└── package.json
```

---

## Key Technical Patterns

### State Persistence
- Kanban state saved to JSON files
- Graph state in LadybugDB
- Session state serialized to disk

### Agent Loop Pattern
```
1. Wake up
2. Scan context (Graphiti + files)
3. Take action
4. Verify result
5. Update state
6. Sleep or continue
```

### MCP Integration
- MCP servers injected dynamically based on environment
- Each server provides tools (read, write, query)
- Configuration in `mcp_servers` dictionary

### Embedding Search (Hybrid)

**Flat semantic search:**
- Text → embedding vector (via Ollama/OpenAI)
- Query graph by semantic similarity
- Returns related nodes ranked by relevance
- Works across all nodes regardless of hierarchy

**Scoped semantic search:**
```
1. Hierarchy filter: get all nodes under scope (via `contains` edges)
2. Semantic search: find matches within filtered set
3. Result: contextually relevant + semantically matched
```

**When to use which:**
- Starting fresh / exploring → flat search
- Working on specific project → scoped search
- Morning planning → flat search across all projects
- Deep work session → scoped to current project

---

## Adaptation Strategy

### Keep As-Is
- Graphiti/LadybugDB connection logic
- Graph traversal algorithms (`find_related_nodes`)
- claude-agent-sdk wrapper
- Session management
- Error handling
- Frontend component hierarchy

### Modify
- Graph schema (code entities → knowledge entities)
- Agent prompts (coding instructions → knowledge extraction)
- Allowed tools list
- State machine states
- Frontend labels and views

### Add
- Claude Code hooks integration
- Session capture logic
- Knowledge extraction prompts
- Simple graph viewer

---

## Node Schema for AIOS

**Design principle:** Hierarchy for SCOPING, semantic search for FINDING. Structure is optional, not forced.

### Node Structure

```
Node:
  id: unique identifier
  type: project | task | idea | decision | session | note | discovery
  content: text (embedded for semantic search)
  created: timestamp
  modified: timestamp
  parent: optional node_id (for hierarchy/scoping)
  tags: optional list (for filtering)
```

Every node has rich `content` that gets embedded - this enables flat semantic search regardless of type or hierarchy.

### Edge Types

```
Structural (for scoping):
  contains: parent → child (project contains tasks, tasks contain subtasks)

Associative (brain-like):
  related_to: any → any (weighted by strength, AI-determined)
  references: any → any (explicit user/AI links)

Semantic (action-based):
  spawned: idea → task (idea became actionable)
  decided_in: decision → session (when decision was made)
  blocked_by: task → task (dependencies)

Temporal:
  preceded_by: node → node (timeline ordering)
```

### Query Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| `search(query)` | Global brain dump | "What do I know about motors?" |
| `scope(parent) + search(query)` | Focused work | "Motor issues in robotics project" |
| `traverse(node, depth)` | Explore connections | "Everything connected to this decision" |
| `related(node)` | Association hop | "What's related to this idea?" |
| `timeline(project, range)` | History view | "What happened last week on robotics?" |

### Why This Design

1. **Not forced hierarchy** - nodes CAN have parents, but don't MUST
2. **Brain-like associations** - `related_to` edges connect anything to anything
3. **Scoping when needed** - hierarchy exists for focused search, not for organization
4. **Rich content** - semantic search works on content, structure is secondary
5. **Flexible types** - `note` and generic types for things that don't fit categories

---

## References

| Component | Source |
|-----------|--------|
| Codebase | AndyMik90/Auto-Claude |
| Agent SDK | claude-agent-sdk in core/client.py |
| Memory | Graphiti + LadybugDB |
| Orchestration | SpecOrchestrator in runners/spec_runner.py |
| Frontend | Electron + React in apps/frontend |
