# Project: Management Agent

This project has a knowledge graph that stores decisions, tasks, discoveries, and project context.

## ALWAYS Use Knowledge Tools

**You MUST proactively use the knowledge graph MCP tools during conversations:**

### When Starting ANY Implementation Work
1. **Create a task first** - Before writing code, call `add_task` with:
   - Clear subject describing what you're building
   - Description with acceptance criteria
   - Status: "in_progress"

2. **Search for context** - Call `search_knowledge` to find:
   - Related past decisions
   - Similar work done before
   - Potential gotchas or learnings

### When Making Choices
**Immediately call `record_decision`** when you:
- Choose a library/framework/approach
- Decide on architecture or structure
- Pick one option over alternatives
- Decide NOT to do something

Example: "I'll use Neo4j for this" → record_decision with rationale

### When Learning Something
**Call `add_discovery`** when you:
- Find a bug or gotcha
- Learn how something works
- Discover an undocumented behavior
- Find a useful pattern

### When Completing Work
**Call `update_task`** to mark tasks completed with a summary of what was done.

## Proactive Behavior Examples

```
User: "Add a caching layer to the API"

You: [FIRST call add_task with subject="Implement API caching layer", status="in_progress"]
     [THEN call search_knowledge("caching API") to find context]

     "I've created a task to track this work. Let me check for any previous context...

     Found: We discussed Redis vs Memcached last month. Decision was Redis for...

     I'll proceed with Redis. Should I record this as a decision?"
```

```
User: "Let's use PostgreSQL instead of SQLite"

You: [call record_decision with title="Switch from SQLite to PostgreSQL",
      rationale="...", alternatives=["SQLite", "MySQL"]]

     "Recorded the decision to switch to PostgreSQL. Now implementing..."
```

```
User: "Hmm, turns out the API has a rate limit of 100/min"

You: [call add_discovery with content="API rate limit is 100 requests/minute",
      context="Discovered while implementing...", tags=["api", "rate-limit"]]

     "Good to know - I've recorded that for future reference."
```

## Two Modes

### Normal Mode (default)
Still use knowledge tools proactively as described above.

### Manager Mode
When the user says "manager mode", "start session", or "init session":

1. **Call `initialize_session`** immediately
2. Show summary of context found
3. Suggest what to work on based on pending tasks
4. Be extra proactive about searching context before any work

## Knowledge Graph Tools

| Tool | When to Use |
|------|-------------|
| `add_task` | **Starting any implementation work** - auto-links to context |
| `update_task` | Completing work, changing status |
| `record_decision` | **Any technology/architecture choice** |
| `add_discovery` | Learning something worth remembering |
| `search_knowledge` | **Before starting work** - find context |
| `get_tasks` | See what's pending/in-progress (supports `parent_id` filter) |
| `get_decisions` | Review past architectural choices |
| `initialize_session` | Starting manager mode |
| `traverse_related` | Understanding node relationships |
| `get_context` | Check current active project/task |
| `set_context` | **Set active project/task** for context-aware task creation |
| `create_project` | Create a new project (ask user first!) |
| `list_projects` | See all available projects |
| `get_task_tree` | View hierarchical task structure |

## Key Rules

1. **Task before code** - Always create a task before starting implementation
2. **Record decisions immediately** - Don't wait, record as you make them
3. **Search first** - Check for existing context before diving in
4. **Discoveries are valuable** - Even small learnings are worth recording

## Context Management

**Claude should intelligently infer and manage project context:**

### 1. Detect Project from Conversation
- "Good morning, robotics project" → `set_context(project="robotics")`
- "Let's work on linux setup" → `set_context(project="linux-setup")`
- Call `get_context()` to check current, `set_context()` to update

### 2. Before Creating New Projects, ASK
- "Project 'robotics' doesn't exist. Should I create it?"
- Only create with `create_project()` after user confirms

### 3. When Working on a Task
- Call `set_context(task_id=...)` to mark it active
- New problems/subtasks automatically link to active task via `use_context=true`

### 4. Use Signals to Infer Context
- Working directory (cwd)
- User mentions ("robotics", "linux", project names)
- Recent tasks/decisions in the graph
- Explicit statements ("switch to X project")

### 5. When Context is Unclear, ASK
- "Should this task go under 'robotics' or somewhere else?"

### Context Flow Example

```
User: "Good morning, let's work on robotics"
Claude: [calls get_context() → no context]
        [calls list_projects() → sees if "robotics" exists]
        If not: "Project 'robotics' doesn't exist. Create it?"
        After confirm: [calls create_project(name="robotics")]
                      [calls set_context(project="robotics")]

User: "Add a task to build the arm controller"
Claude: [calls add_task(subject="Build arm controller")]
        → auto-links to robotics via use_context=true

User: "Let's work on that task"
Claude: [calls set_context(task_id=<arm controller>)]

User: "The servo is jittering, need to fix that"
Claude: [calls add_task(subject="Fix servo jitter")]
        → becomes subtask of arm controller automatically

User: "Quick detour - need to fix my wifi on linux"
Claude: "This seems like a different project. Add to 'linux-setup' or create new?"
        After confirm: [calls set_context(project="linux-setup")]
                      [calls add_task(...)]
```

## Context Tools

| Tool | When to Use |
|------|-------------|
| `get_context` | Check current active project/task |
| `set_context` | Set active project and/or task |
| `create_project` | Create a new project (ask first!) |
| `list_projects` | See all available projects |
| `get_task_tree` | View hierarchical task structure |

## Project Structure

- `apps/mcp/` - MCP server for knowledge graph
- `apps/backend/integrations/graphiti/` - Knowledge graph backends (Neo4j, Postgres, Memory)
- `apps/agents/` - Background agents (linker, researcher, session_reviewer)
- `deploy/neo4j/` - Neo4j Docker setup
