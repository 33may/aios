# AIOS CLI - Claude Code-Like Interface

## Vision
A **chat interface identical to Claude Code** but for your knowledge base. Same look, same `/` commands, same experience - just talking to your memory instead of (or alongside) Claude.

```
┌─────────────────────────────────────────────────────────────────────┐
│  aios v0.1.0                                          my-robot      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Welcome back! Last session: 2 hours ago                            │
│  Project: my-robot (5 open tasks, 3 recent decisions)               │
│                                                                     │
│  > why did we choose ROS2?                                          │
│                                                                     │
│  Found 2 relevant decisions:                                        │
│                                                                     │
│  📋 Decision: ROS2 over ROS1                                        │
│  ├─ Date: 2026-01-15                                                │
│  ├─ Rationale: Better real-time support, modern DDS middleware      │
│  └─ Session: robot-arm-planning                                     │
│                                                                     │
│  📋 Discussion: Middleware evaluation                               │
│  ├─ Date: 2026-01-10                                                │
│  └─ Related: Task #42 - Sensor integration                          │
│                                                                     │
│  > /tasks                                                           │
│                                                                     │
│  Open tasks in my-robot:                                            │
│  ○ #42 Integrate LIDAR sensor                                       │
│  ○ #43 Implement path planning                                      │
│  ◉ #44 Setup simulation environment (in progress)                   │
│                                                                     │
│  > _                                                                │
├─────────────────────────────────────────────────────────────────────┤
│  /help  /tasks  /decisions  /recent  /work  /config        ctrl+c  │
└─────────────────────────────────────────────────────────────────────┘
```

## Two Modes

### Mode 1: AIOS Chat (Knowledge Interface)
- Query your knowledge base conversationally
- Use `/` commands for quick actions
- Navigate projects, view history, search memories

### Mode 2: Claude Work Session
- Start with `/work` - launches Claude Code with context injected
- All your knowledge automatically available to Claude
- Session learnings saved back to knowledge graph

## Phase 1: AIOS Chat Interface (Knowledge Mode)

### Core Experience
```bash
# Navigate like normal terminal
$ cd ~/projects/my-robot

# Query knowledge naturally from anywhere
$ aios "why did we choose ROS2?"
> Found 3 relevant decisions:
>
> [2026-01-15] Decision: ROS2 over ROS1
>   Rationale: Better real-time support, modern DDS middleware
>   Session: robot-arm-planning
>
> [2026-01-10] Discussion: Middleware options
>   Context: Evaluated ROS2, MQTT, custom solution
>   Related: Task #42 - Sensor integration
>
> Source: project:my-robot, 3 nodes matched

# Quick queries
$ aios recent              # What was I working on?
$ aios blocked             # What tasks are blocked?
$ aios decisions           # Recent architectural decisions
$ aios "tasks about auth"  # Semantic search
```

### Navigation & Scoping
```bash
# Auto-detect project from current directory
$ cd ~/projects/my-robot
$ aios status
> Project: my-robot (detected from .git)
> Last session: 2 hours ago
> Open tasks: 5
> Recent decisions: 3

# Explicit project scope
$ aios --project my-robot "what's the sensor architecture?"

# Cross-project queries
$ aios --all "how do we handle authentication?"
```

### Interactive Mode (Settings/Config)
```bash
$ aios config
┌─────────────────────────────────────────────┐
│  AIOS Configuration                         │
├─────────────────────────────────────────────┤
│  ○ Memory Backend: Graphiti (LadybugDB)     │
│  ○ Embeddings: Ollama (nomic-embed-text)    │
│  ○ LLM: Anthropic (claude-sonnet-4)         │
│                                             │
│  Projects:                                  │
│  ├─ my-robot (active)                       │
│  ├─ web-dashboard                           │
│  └─ aios-core                               │
│                                             │
│  [s] Settings  [p] Projects  [m] Memory     │
│  [h] Hooks     [q] Quit                     │
└─────────────────────────────────────────────┘
```

## Phase 2: Work Mode (Claude Session with Context)

### Session Initialization
```bash
# Start work session - context auto-injected
$ aios work
> Initializing Claude session for: my-robot
>
> Injecting context:
>   ├─ Project summary (2.1k tokens)
>   ├─ Recent decisions (1.4k tokens)
>   ├─ Open tasks (800 tokens)
>   ├─ Last session summary (600 tokens)
>   └─ Relevant code patterns (1.2k tokens)
>
> Starting Claude Code...

# Claude session starts with CLAUDE.md containing:
# - Project context
# - Recent decisions
# - Current tasks
# - Relevant memories
```

### Context Injection Strategy
```yaml
# Auto-generated .claude/session-context.md
## Project: my-robot
Last active: 2 hours ago

## Recent Decisions
- [2026-01-15] Chose ROS2 for middleware (real-time support)
- [2026-01-14] Using async/await for sensor callbacks

## Current Tasks
- [ ] #42: Integrate LIDAR sensor
- [ ] #43: Implement path planning
- [x] #41: Setup ROS2 workspace

## Relevant Memories
- Sensor data format: Protocol Buffers
- Testing approach: Simulation-first with Gazebo
- Code style: Google C++ style guide

## Last Session Summary
Worked on LIDAR driver integration. Got basic readings working.
Next: Parse point cloud data and publish to /scan topic.
```

### Seamless Transition
```bash
# Quick start - uses defaults
$ aios work

# With specific focus
$ aios work --focus "LIDAR integration"
> Injecting context focused on: LIDAR integration
> Found 5 relevant memories, 2 decisions, 1 active task

# Resume previous session
$ aios resume
> Resuming session from 2 hours ago
> Context: LIDAR driver integration
```

## Slash Commands (Claude Code Style)

```
/help                    Show all commands
/clear                   Clear chat history
/compact                 Summarize conversation

─── Navigation ───
/project [name]          Switch or show current project
/cd <path>               Change working directory
/ls                      List files in current directory

─── Knowledge Queries ───
/tasks                   List open tasks
/decisions               Show recent decisions
/recent                  What was I working on?
/blocked                 Show blocked items
/search <query>          Semantic search across all memories

─── Memory Management ───
/remember <note>         Add a memory manually
/forget <id>             Remove a memory
/history                 Show session history

─── Work Session ───
/work                    Start Claude Code with context injection
/resume                  Resume last Claude session
/context                 Show what context will be injected

─── Configuration ───
/config                  Open settings TUI
/status                  Show project & system status
/login                   Authenticate (like Claude /login)
```

## Architecture

### CLI Structure
```
aios (main entry point - launches chat interface)
│
├── Chat Mode (default)
│   ├── Natural language queries → Knowledge graph search
│   ├── Slash commands → Direct actions
│   └── Tab completion for commands
│
├── /work → Launches Claude Code
│   ├── Injects context from knowledge graph
│   ├── Sets up hooks for session capture
│   └── Returns to AIOS chat when done
│
└── /config → Settings TUI
    ├── Memory backend settings
    ├── Project management
    └── Hook configuration
```

### Context Injection Hook
```python
# hooks/session_start.py
def inject_context(project_path: str) -> str:
    """Generate context for Claude session."""

    # Query knowledge graph
    project = detect_project(project_path)
    memories = graphiti.search(
        project=project,
        limit=10,
        recency_weight=0.3
    )

    # Build context document
    context = ContextBuilder()
    context.add_section("Project", project.summary)
    context.add_section("Recent Decisions", memories.decisions)
    context.add_section("Current Tasks", memories.tasks)
    context.add_section("Last Session", memories.last_session)

    # Write to .claude/session-context.md
    write_context(project_path, context)

    return context.as_markdown()
```

### Integration with Claude Code Hooks
```json
// .claude/settings.json
{
  "hooks": {
    "session_start": {
      "command": "aios inject-context",
      "timeout": 5000
    },
    "session_end": {
      "command": "aios save-session",
      "timeout": 10000
    }
  }
}
```

## User Stories (Extended)

### Exploration
- As a developer, I want to query my knowledge base from any terminal without leaving my workflow
- As a developer, I want to see project status instantly when I cd into a project
- As a developer, I want to search across all my projects for patterns and decisions

### Work Sessions
- As a developer starting work, I want relevant context automatically loaded so I can start immediately
- As a developer, I want Claude to know what I was working on yesterday without me explaining
- As a developer, I want my decisions and learnings to persist across sessions automatically

### Configuration
- As a developer, I want to configure AIOS with a familiar CLI interface like Claude Code settings
- As a developer, I want to see what's stored in my knowledge graph and manage it

## Acceptance Criteria (Extended)

### Exploration Mode
- [ ] CLI accepts natural language questions from any directory
- [ ] Auto-detects project from .git or .aios config
- [ ] Returns relevant knowledge with source attribution
- [ ] Supports project-scoped and cross-project queries
- [ ] Quick commands: recent, blocked, decisions, tasks
- [ ] Interactive config mode with TUI

### Work Mode
- [ ] `aios work` starts Claude session with auto-injected context
- [ ] Context includes: project summary, recent decisions, tasks, last session
- [ ] Context is token-efficient (stays under 6k tokens)
- [ ] `aios resume` continues previous session with full context
- [ ] Session end automatically saves learnings to knowledge graph

### Integration
- [ ] Works with Claude Code hooks for seamless injection
- [ ] Shell integration for cd-triggered status (optional)
- [ ] Respects .gitignore and .aiosignore for privacy

## Technical Implementation

### UI Framework Options
1. **Textual** (Python) - Rich TUI framework, similar to what Claude Code uses
2. **Ink** (Node.js) - React for CLI, very flexible
3. **Bubble Tea** (Go) - Fast, elm-architecture based

**Recommendation: Textual** (Python)
- Already using Python for backend
- Rich styling, panels, tables
- Easy integration with Graphiti

### Example Textual Implementation
```python
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static, Footer
from textual.binding import Binding

class AIOSChat(App):
    """Claude Code-like chat interface for AIOS."""

    CSS = """
    #chat-log {
        height: 1fr;
        border: solid green;
    }
    #input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("aios v0.1.0", id="header")
        yield RichLog(id="chat-log", highlight=True, markup=True)
        yield Input(placeholder="> Ask a question or type /help", id="input")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        log = self.query_one("#chat-log", RichLog)

        if query.startswith("/"):
            await self.handle_command(query)
        else:
            await self.handle_query(query)

        self.query_one("#input", Input).value = ""

    async def handle_command(self, cmd: str) -> None:
        log = self.query_one("#chat-log", RichLog)

        if cmd == "/help":
            log.write(HELP_TEXT)
        elif cmd == "/tasks":
            tasks = await graphiti.search(type="task", status="open")
            log.write(format_tasks(tasks))
        elif cmd == "/work":
            await self.start_claude_session()
        # ... more commands

    async def handle_query(self, query: str) -> None:
        """Natural language query to knowledge graph."""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[dim]> {query}[/dim]")

        results = await graphiti.semantic_search(query)
        log.write(format_results(results))
```

### Startup Flow
```
$ aios
     ┌────────────────────────────────────────────┐
     │  Detecting project...                      │
     │  ✓ Found: my-robot (from .git)             │
     │  ✓ Connected to knowledge graph            │
     │  ✓ Last session: 2 hours ago               │
     └────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  aios v0.1.0                                          my-robot      │
│                                                                     │
│  Welcome back! You were working on LIDAR integration.               │
│  Type a question or /help for commands.                             │
│                                                                     │
│  > _                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Notes

### Token Budget
- Total context injection: ~6k tokens max
- Project summary: 2k tokens
- Recent decisions: 1.5k tokens
- Tasks: 1k tokens
- Last session: 1k tokens
- Buffer: 500 tokens

### Performance
- Query response: <500ms for local queries
- Context injection: <2s for session start
- Embedding generation: handled async, cached

### Privacy
- All data stored locally (LadybugDB)
- No cloud sync by default
- Respects .gitignore patterns
- Explicit opt-in for cross-project queries
