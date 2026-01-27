# Project: Management Agent

This project has a knowledge graph that captures reasoning, decisions, constraints, and problem-solving - not just tasks and outputs.

## Core Philosophy: Capture the Thinking

**Focus on WHY and HOW, not just WHAT:**
- Record reasoning chains that lead to decisions
- Capture constraints that shape choices
- Document problems and how they were fixed
- Link everything together

## When to Use Knowledge Tools

### When Analyzing Options
**Create `thought` nodes** for each option considered:

```
User: "Let's build a better GUI"

You: [add_thought: "Evaluated Streamlit - limited interactivity, re-render issues"]
     [add_thought: "Evaluated Dash + Cytoscape - good for graphs but web-based"]
     [add_thought: "Evaluated Tauri - lightweight desktop, best UX, Rust backend"]
```

### When User States a Preference
**Create a `constraint` node** immediately:

```
User: "I prefer desktop apps"

You: [add_constraint: "User prefers desktop applications over web-based solutions"
      source="user", priority="high"]
```

### When Making a Decision
**Create a `decision` node AND link the reasoning:**

```
You: [record_decision: "Use Tauri + React for GUI"
      rationale="Best desktop UX, lightweight, Rust backend for performance"]
     [link_nodes: thought1 --led_to--> decision]
     [link_nodes: thought2 --led_to--> decision]
     [link_nodes: constraint --constrained_by--> decision]
```

### When Hitting a Problem
**Create a `problem` node** with context:

```
User: "Dashboard is showing empty"

You: [add_problem: "Dashboard showing empty despite Neo4j having data"
      context="Noticed during GUI testing", severity="high"]
     [add_thought: "Investigating - checking backend config..."]
     [add_discovery: ".env file not loaded by boot script"]
```

### When Fixing Something
**Create a `fix` node** linked to the problem:

```
You: [add_fix: "Source .env in boot script before starting dashboard"
      problem_id=<problem_uuid>]
     // This automatically creates: problem --fixed_by--> fix
```

## Node Types

| Type | When to Use | Example |
|------|-------------|---------|
| `thought` | Reasoning, analysis, observations | "Evaluated 10 GUI options, Streamlit has re-render issues" |
| `constraint` | User preference or requirement | "User prefers desktop app" |
| `decision` | Final choice with rationale | "Use Tauri because..." |
| `problem` | Issue encountered | "Dashboard showed empty" |
| `fix` | Solution to a problem | "Updated boot script to source .env" |
| `discovery` | Learning or insight | "API has undocumented rate limit" |
| `task` | Work to be done | "Implement caching layer" |

## Edge Types (Linking)

| Edge | Purpose | Example |
|------|---------|---------|
| `spawned` | Parent created child (auto-used for thoughts, constraints) | task --spawned--> thought |
| `led_to` | Reasoning chain / something led to this | thought --led_to--> decision |
| `supports` | Evidence for | discovery --supports--> decision |
| `contradicts` | Evidence against | thought --contradicts--> option |
| `refined_by` | Evolved thinking | thought1 --refined_by--> thought2 |
| `constrained_by` | Limited by preference | decision --constrained_by--> constraint |
| `fixed_by` | Problem solved | problem --fixed_by--> fix |

## Knowledge Tools Reference

| Tool | When to Use |
|------|-------------|
| `add_thought` | Recording reasoning steps, observations, analysis (auto-links to focus) |
| `add_constraint` | Capturing user preferences, requirements (auto-collected for decisions) |
| `add_problem` | Documenting issues, bugs, blockers (sets active_problem for fix linking) |
| `add_fix` | Recording solutions (auto-links to active_problem) |
| `add_discovery` | Capturing learnings, insights (auto-links via led_to) |
| `record_decision` | Recording choices (auto-links focus + all collected constraints) |
| `link_nodes` | Creating custom edges (most linking is automatic now) |
| `add_task` | Work items (still useful, just not the focus) |
| `search_knowledge` | Finding context before starting work |
| `set_focus` | Set focus to a specific node for auto-linking |
| `clear_focus` | Stop automatic parent-based linking |
| `get_reasoning_context` | Debug: see focus, active problem, collected constraints |

## Example: Full Knowledge-Centric Flow

```
User: "Let's build a better GUI for the knowledge graph"

You: [search_knowledge("GUI knowledge graph") to find context]
     "Found previous work on dashboards. Let me analyze options..."

     [add_thought: "Considered Streamlit - good for quick prototypes but limited
      interactivity, full page re-renders on every interaction"]

     [add_thought: "Considered Dash + Cytoscape - excellent graph visualization,
      but requires running a web server, no native feel"]

     [add_thought: "Considered Tauri with React + vis-network - lightweight
      desktop app, native feel, good graph libraries available"]

User: "I really want it to feel like a native desktop app, not a browser"

You: [add_constraint: "User requires native desktop feel, not web-based"
      source="user", priority="must-have"]

     "Got it - desktop feel is a must-have. That rules out Dash..."

     [record_decision: "Use Tauri + React + vis-network for knowledge graph GUI"
      rationale="Only option that provides native desktop experience while having
      good graph visualization capabilities"
      alternatives=["Streamlit", "Dash + Cytoscape", "Electron"]]

     [link_nodes: thought3 --led_to--> decision]
     [link_nodes: constraint --constrained_by--> decision]

     "Decision recorded. Now let me implement..."

User: "The graph is not showing any nodes"

You: [add_problem: "Graph visualization showing no nodes despite data in Neo4j"
      context="Testing new Tauri GUI", severity="high"]

     [add_thought: "Checking connection - Neo4j responds to test queries..."]
     [add_thought: "Found issue - environment variables not loaded"]
     [add_discovery: "Tauri doesn't inherit shell environment by default"]

     [add_fix: "Load .env file explicitly in Tauri main.rs setup"
      problem_id=<problem_id>]

     "Fixed! The issue was that Tauri doesn't inherit shell environment variables."
```

## Context-Aware Reasoning (Auto-Linking)

The system automatically tracks a **focus node** and creates parent-child relationships. You don't need to manually call `link_nodes` for most cases.

### How It Works

1. **Focus tracking**: When you create a reasoning node, it becomes the new focus
2. **Auto-linking**: New nodes automatically link to the current focus as their parent
3. **Edge types**: Different node types use appropriate edges (`spawned`, `led_to`, etc.)

This creates traversable reasoning trees:
```
Task: "Implement GUI"
├── Thought: "Evaluating Streamlit..."  (spawned)
│   ├── Thought: "Streamlit has issues" (spawned)
│   └── Discovery: "Lacks native feel"  (led_to)
├── Constraint: "Must be desktop app"   (spawned)
└── Decision: "Use Tauri"               (led_to + constrained_by)
    └── Problem: "Graph not rendering"  (led_to)
        └── Fix: "Load .env in setup"   (fixed_by)
```

### Auto-Linking Behavior by Tool

| Tool | Links to Parent Via | Also Does |
|------|---------------------|-----------|
| `add_thought` | `spawned` | Becomes focus |
| `add_discovery` | `led_to` | Becomes focus |
| `add_problem` | `led_to` | Becomes focus + sets active_problem |
| `add_fix` | `spawned` + `fixed_by` | Links to active_problem, clears it |
| `add_constraint` | `spawned` | Collected for decision, becomes focus |
| `record_decision` | `led_to` | Links all collected constraints |

### Focus Management Tools

| Tool | Purpose |
|------|---------|
| `set_focus(node_id)` | Jump focus to any node (task, problem, etc.) |
| `clear_focus()` | Stop auto-linking |
| `get_reasoning_context()` | See current focus, active problem, collected constraints |

### Opting Out

Pass `use_context=false` to any reasoning tool to skip auto-linking:
```
add_thought(content="...", use_context=false)  // Won't link, won't become focus
```

Or use explicit `parent_id` to override the current focus:
```
add_thought(content="...", parent_id="<task-uuid>")  // Links to specific node
```

### Example: Simplified Flow (No Manual Linking!)

```
[set_focus(task_id)]  // Focus on a task

[add_thought: "Evaluating Option A"]
// Auto: task --spawned--> thought1, focus = thought1

[add_thought: "Option A has issues"]
// Auto: thought1 --spawned--> thought2, focus = thought2

[add_constraint: "Must be fast"]
// Auto: thought2 --spawned--> constraint, constraint collected

[add_discovery: "Found that B is fastest"]
// Auto: constraint --led_to--> discovery, focus = discovery

[record_decision: "Use Option B"]
// Auto: discovery --led_to--> decision
// Auto: decision --constrained_by--> constraint (all collected)
```

### Problem-Fix Flow

```
[add_problem: "Build is failing"]
// Auto: focus --led_to--> problem
// Auto: problem becomes focus AND active_problem

[add_thought: "Checking logs..."]
// Auto: problem --spawned--> thought

[add_fix: "Missing dependency"]
// Auto: problem --fixed_by--> fix (uses active_problem)
// Auto: thought --spawned--> fix
// Auto: clears active_problem
```

## Key Behaviors

1. **Search first** - Always `search_knowledge` before starting work
2. **Capture reasoning** - Create `thought` nodes as you analyze (auto-links!)
3. **Capture constraints immediately** - When user states a preference, record it (auto-collected!)
4. **Let the system link** - Auto-linking handles most cases; use `link_nodes` only for special relationships
5. **Document problems** - Create `problem` and `fix` nodes when debugging (auto-linked!)
6. **Decisions auto-gather constraints** - Just call `record_decision` and constraints link automatically

## Manager Mode

When user says "manager mode", "start session", or "init session":

1. Call `initialize_session` immediately
2. Show summary of recent context
3. Show any open problems
4. Suggest focus areas based on reasoning chains

## Context Management

Same as before - use `set_context`, `get_context`, `create_project`, etc. to manage which project you're working in. Tasks and other nodes will auto-link to the active context.

## Project Structure

- `apps/mcp/` - MCP server for knowledge graph
- `apps/backend/integrations/graphiti/` - Knowledge graph backends (Neo4j, Postgres, Memory)
- `apps/agents/` - Background agents (linker, researcher, session_reviewer)
- `deploy/neo4j/` - Neo4j Docker setup
