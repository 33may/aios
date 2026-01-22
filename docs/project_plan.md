# AIOS - Personal AI Knowledge System

## Core Idea

AI-powered knowledge graph that makes Claude Code persistent. Every session, decision, and task is stored in a graph database (Graphiti). The AI traverses this graph to retrieve context, understand your history, and work with full memory of past sessions.

**"Работа — это и есть отчетность"** - Work IS the report. You don't maintain documentation. The AI does it automatically by analyzing your sessions.

---

## Problems We Solve

### 1. Context Loss (Cold Start)
Every time you return to a project: "What was I doing? Where did I stop? What decisions did I make?"

The AI forgets everything between sessions. You waste energy rebuilding mental context.

### 2. Documentation Decay
Knowledge bases (Notion, Obsidian) are useful only if current. Manual updates are boring, get skipped, and everything rots.

### 3. Idea Fragmentation
Ideas connect to ideas. Projects spawn sub-projects. But tools treat everything as flat lists. No hierarchy, no relations, no graph structure.

### 4. Lost Reasoning
You made a decision last month. Why? The WHAT is in git history, but the WHY is gone. Next session, you (or AI) might undo good decisions from ignorance.

---

## Solution: Graphiti Knowledge Graph

### The Graph Structure
```
[Project: Robotics]
    │
    ├──[Task: Motor Control]──────[Status: in_progress]
    │       │
    │       └──[Session: 2026-01-22]
    │               │
    │               ├──[Decision: Use PCA9685]
    │               │       │
    │               │       └──[Reasoning: "Direct GPIO has jitter issues"]
    │               │
    │               └──[Discovery: "Servo library conflicts with PWM"]
    │
    ├──[Task: Sensor Integration]──[Status: todo]
    │
    └──[Idea: Add camera tracking]──[Related: [[computer-vision-research]]]
```

- **Nodes**: Projects, Tasks, Ideas, Decisions, Sessions, Discoveries
- **Edges**: Relationships (parent, related, spawned, blocked_by) + temporal (created, modified)
- **Semantic search**: Find related content via embeddings, not just keywords

### Why Graphiti (not markdown files)
- Built for AI graph traversal
- Temporal edges (timeline awareness built-in)
- Semantic search via embeddings
- Scales to thousands of nodes
- Auto-Claude already uses it (proven)

Trade-off: Not human-readable directly → we build a simple viewer

---

## How It Works

### Session Start
```
You: "Let's work on robotics"

AI actions:
1. Parse intent → identify "robotics" project
2. Query Graphiti → traverse related nodes
3. Retrieve:
   - Project status
   - Open tasks
   - Recent sessions
   - Past decisions + reasoning
4. Build context

AI: "Robotics project. Last session: motor control debugging.
     You decided on PCA9685 because direct GPIO had jitter.
     Open: sensor integration (blocked by motor control).
     Continue with motor PWM?"
```

### During Work
Normal Claude Code session, but with full context loaded. AI knows your history, decisions, and reasoning.

### Session End (Auto via Hooks)
```
Session ends → Claude Code hooks trigger

AI extracts:
- Decisions made (+ WHY)
- New tasks created/completed
- Problems discovered
- Ideas mentioned
- Links to existing nodes

AI writes to Graphiti:
- New nodes created
- Edges to existing nodes
- Timestamps for timeline
```

### Morning Planning
```
You: "What should I work on today?"

AI actions:
1. Scan all projects
2. Find incomplete tasks
3. Check priorities, blockers, dependencies
4. Consider timeline (what's stale, what's urgent)

AI: "You have 3 active projects.
     Robotics: motor control 80% done, been 2 days
     Web app: blocked by API decision
     Research: no recent activity (2 weeks)

     Suggest: finish motor control (close to done),
     then make API decision to unblock web app."
```

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                   YOU                        │
│              (Claude Code)                   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           Claude Code + Hooks                │
│                                              │
│  • Pre-session: load context from graph      │
│  • Post-session: extract & store to graph    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         Graphiti + LadybugDB                 │
│          (Knowledge Graph)                   │
│                                              │
│  • Nodes: projects, tasks, decisions, etc    │
│  • Edges: relationships + temporal           │
│  • Embeddings: Ollama (local) for search     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│            Simple Viewer                     │
│     (Web/Terminal UI for browsing)           │
└─────────────────────────────────────────────┘
```

### Technical Stack (from Auto-Claude)
- **Graphiti + LadybugDB** - knowledge graph storage
- **claude-agent-sdk** - AI interface
- **Ollama** - local embeddings for semantic search
- **Claude Code hooks** - auto-capture sessions
- **Simple viewer** - browse graph manually (to build)

---

## MVP Scope

### Core (Build First)
1. **Graphiti integration** - setup graph database
2. **Session capture via hooks** - auto-extract knowledge from Claude Code sessions
3. **Context retrieval** - load relevant context on session start
4. **Basic viewer** - see what's in your graph

### Input Sources (MVP)
- Claude Code sessions only

### Later (Post-MVP)
- Voice input (thoughts, ideas on the go)
- Web research capture (browser extension or manual)
- Google/Gemini integration (deep research, then import results)
- Advanced viewer (graph visualization, timeline view)

---

## What This Is

- Personal second brain with AI agency
- Memory augmentation for Claude (persistent via graph)
- Auto-documentation system
- Context retrieval system (RAG via knowledge graph)

## What This Is NOT

- Corporate tool (no agile, no stakeholders, no sprints)
- Team collaboration
- Jira/Linear replacement
- Task app with AI features

---

## Technical Foundation

Built by adapting **Auto-Claude** architecture:
- Fork Auto-Claude repo
- Keep: Graphiti, LadybugDB, claude-agent-sdk, orchestrator
- Replace: coding agents → knowledge management agents
- Add: hooks for session capture, viewer for browsing

Key insight from research: ~85% of Auto-Claude infrastructure is reusable. We're not building from scratch - we're repurposing a coding agent into a knowledge agent.
