# AIOS User Stories

Development phase user stories for the personal AI knowledge system.

---

## Story 1: Session Capture & Task Management

**Priority:** HIGH (MVP)

### User Stories

```
AS a user ending a Claude Code session
I WANT the AI to capture decisions, problems, ideas, and task updates
SO THAT my knowledge base stays current without manual work
```

```
AS a user planning my day
I WANT to discuss tasks with AI and have them created in the graph
SO THAT "let's work on robotics, we need to do X, Y, Z" creates actual task nodes
```

### What Gets Captured

| Type | Example | Stored As |
|------|---------|-----------|
| Decision | "Let's use ROS2 for this" | Decision node + reasoning |
| Problem | "Servo jitter when PWM > 80%" | Problem node + context |
| Idea | "Maybe we could add camera tracking" | Idea node + links |
| Task created | "We need to calibrate motors" | Task node (status: todo) |
| Task completed | "Finished the motor driver" | Task node (status: done) |
| Discovery | "Found that library X doesn't support Y" | Discovery node |

### Acceptance Criteria

- [ ] Conversation ends → AI extracts knowledge automatically
- [ ] Decisions saved with reasoning (WHY not just WHAT)
- [ ] Problems/blockers captured with context
- [ ] Ideas linked to relevant projects
- [ ] New tasks created when discussed in conversation
- [ ] Task status updated when work completed
- [ ] Session node created linking all extracted knowledge

### Notes

- Extraction happens via hooks or explicit trigger (decide during dev)
- AI should ask for clarification if project context unclear
- Multiple projects in one session → link session to all relevant projects

---

## Story 2: Context Retrieval on Session Start

**Priority:** HIGH (MVP)

### User Story

```
AS a user starting a new session
I WANT the AI to load relevant context from the knowledge graph
SO THAT I can continue work without rebuilding mental context
```

### Trigger Phrases → Actions

| User Says | AI Does |
|-----------|---------|
| "Let's work on robotics" | Load robotics project, recent sessions, open tasks |
| "What did we do yesterday?" | Query recent sessions, summarize |
| "Where did we stop on motor control?" | Find task, load last session, show status |
| "What's blocking this?" | Find related problems, decisions |
| "Continue where we left off" | Load last session context |

### Acceptance Criteria

- [ ] AI knows project state without manual briefing
- [ ] Can answer "what was the last progress on X?"
- [ ] Can answer "what problems did we encounter?"
- [ ] Can answer "what decisions did we make and why?"
- [ ] Can answer "what's still open/todo?"
- [ ] Context loads automatically based on conversation intent

### Notes

- Use scoped search: identify project first, then retrieve within scope
- Fall back to global search if project unclear
- Show confidence: "Based on your last session on Jan 20..."

---

## Story 3: Persistent System Prompt

**Priority:** HIGH (MVP)

### User Story

```
AS a user
I WANT the AI to always know about the knowledge system
SO THAT it consistently uses the graph for memory and context
```

### System Prompt Must Include

- Knowledge graph exists and how to use it
- Instructions to extract knowledge from sessions
- Instructions to query for context on session start
- Node/edge schema awareness
- When to create vs update nodes
- How to link related concepts

### Requirements

- [ ] System prompt loaded on every session
- [ ] User has control over prompt content
- [ ] Prompt managed by AIOS system (not external file dependency)
- [ ] Can be updated without code changes
- [ ] Versioned (track prompt changes over time)

### Notes

- Implementation flexible: could be config file, database, or injected programmatically
- NOT hardcoded in source
- User wants control over agent behavior via prompt

---

## Story 4: Research/Query Mode

**Priority:** MEDIUM

### User Story

```
AS a user with a question
I WANT the AI to search and reason over my knowledge base
SO THAT it answers using MY stored knowledge, not just general knowledge
```

### Example Queries

| Question | AI Behavior |
|----------|-------------|
| "Why did we choose ROS2?" | Find decision node → return with reasoning |
| "What have I tried for motor control?" | Traverse sessions related to motor tasks |
| "Any patterns in my blocked tasks?" | Analyze problem nodes across projects |
| "What do I know about PID tuning?" | Semantic search → aggregate related nodes |
| "Compare my robotics vs web projects" | Cross-project analysis |

### Acceptance Criteria

- [ ] AI queries graph semantically (not just keyword)
- [ ] AI traverses relationships to find connected info
- [ ] Answers grounded in stored knowledge
- [ ] AI cites sources: "In your session on Jan 20, you decided..."
- [ ] Can distinguish "I don't have info on this" vs general knowledge answer

### Notes

- This is RAG over personal knowledge graph
- Should prefer stored knowledge over hallucination
- Combine: scoped search (if project known) + semantic search

---

## Story 5: Knowledge Base Viewer

**Priority:** MEDIUM (MVP: CLI, Later: GUI)

### User Story

```
AS a user
I WANT to browse and review my knowledge graph
SO THAT I can see what's stored and verify/edit if needed
```

### MVP: CLI Commands

```bash
aios projects              # List all projects
aios show robotics         # Show project details + children
aios tasks robotics        # List tasks for project
aios search "motor"        # Semantic search across all
aios recent                # Recent sessions/changes
aios node <id>             # Show specific node + edges
```

### Later: GUI

- Visual graph with nodes and edges
- Click node to expand/explore
- Filter by: type, project, date range, status
- Edit nodes directly
- Timeline view of sessions

### Acceptance Criteria

**MVP:**
- [ ] Can list projects
- [ ] Can view project contents (tasks, ideas, decisions)
- [ ] Can search across knowledge base
- [ ] Can view recent activity
- [ ] Can inspect individual nodes

**Later:**
- [ ] Visual graph rendering
- [ ] Interactive exploration
- [ ] Inline editing

---

## Story Priority & Dependencies

```
┌─────────────────────────────────────────────────┐
│  Story 3: System Prompt                         │
│  (Foundation - needed for all others)           │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
┌─────────────┐       ┌───────────────┐
│  Story 1:   │       │   Story 2:    │
│  Capture    │       │   Retrieval   │
└─────────────┘       └───────────────┘
      │                       │
      └───────────┬───────────┘
                  ▼
          ┌─────────────┐
          │  Story 4:   │
          │  Research   │
          └─────────────┘
                  │
                  ▼
          ┌─────────────┐
          │  Story 5:   │
          │  Viewer     │
          └─────────────┘
```

**Suggested order:**
1. Story 3 (System Prompt) - foundation
2. Story 1 (Capture) + Story 2 (Retrieval) - can parallel
3. Story 4 (Research) - builds on 1+2
4. Story 5 (Viewer) - can start MVP early, enhance later

---

## Out of Scope (Future)

- Voice input capture
- Web research integration
- Google/Gemini integration
- Multi-device sync
- Collaboration/sharing
