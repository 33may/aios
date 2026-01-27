# /research Command

Initiates an interactive, multi-agent research workflow with persistent workspace and knowledge linking.

## Usage

```
/research [topic]           # Start new or continue research
/research                   # Interactive mode - choose existing research
/research continue [id]     # Continue specific research
```

## What This Does

1. **Interactive Setup** - Choose existing research or create new
2. **Parallel Research** - 3 specialized agents investigate simultaneously
3. **Verification** - Cross-checks findings for accuracy
4. **Synthesis** - Reconciles findings, produces conclusions
5. **Linking** - Connects discoveries to each other and existing knowledge
6. **Documentation** - Writes comprehensive research report to workspace

## Execution Instructions

### Phase 0: Interactive Setup (ALWAYS DO FIRST)

```python
# 1. Check for existing research projects
list_projects()  # Look for projects with "research:" prefix

# 2. Ask user what they want to do
AskUserQuestion(
    questions=[{
        "question": "How would you like to proceed with research?",
        "header": "Research Mode",
        "options": [
            {"label": "New Research", "description": "Start fresh research on a new topic"},
            {"label": "Continue Existing", "description": "Resume or extend previous research"},
            {"label": "Link to Project", "description": "Research related to an existing project/task"}
        ],
        "multiSelect": false
    }]
)

# 3. If "Continue Existing" - show existing research sessions
search_knowledge("research")
# Present list, let user choose

# 4. If "Link to Project" - show projects/tasks
list_projects()
get_tasks(status="pending")
# Let user select what to link to

# 5. Create or set context
IF new_research:
    create_project(name="research:[topic-slug]", description="Research on: [topic]")
    set_context(project="research:[topic-slug]")
    mkdir research/[topic-slug]
ELSE:
    set_context(project="research:[existing-id]")
```

### Phase 1: Initialize

```python
search_knowledge("[topic]")  # Find existing related knowledge
add_thought("Starting research on: [topic]. Context: [any linked projects/tasks]",
            tags=["source:agent", "research-init"])
```

### Phase 2: Parallel Research (3 agents in ONE message)

**CRITICAL**: Launch ALL THREE in a single response for parallel execution.

```python
Task(
  subagent_type="general-purpose",
  description="Research [topic] theory",
  prompt="""[Include theoretical-researcher.md content]

RESEARCH PROJECT: [project-id]
TOPIC: [topic]
LINKED CONTEXT: [any related projects/tasks]

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Use knowledge tools throughout
- Tag all nodes with source:agent or source:external
""",
  allowed_tools=["WebSearch", "WebFetch", "mcp__knowledge__*"]
)

Task(
  subagent_type="general-purpose",
  description="Research [topic] solutions",
  prompt="""[Include solutions-researcher.md content]

RESEARCH PROJECT: [project-id]
TOPIC: [topic]
LINKED CONTEXT: [any related projects/tasks]

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Use knowledge tools throughout
- Tag all nodes with source:agent or source:external
""",
  allowed_tools=["WebSearch", "WebFetch", "mcp__knowledge__*"]
)

Task(
  subagent_type="general-purpose",
  description="Research [topic] ecosystem",
  prompt="""[Include market-researcher.md content]

RESEARCH PROJECT: [project-id]
TOPIC: [topic]
LINKED CONTEXT: [any related projects/tasks]

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Use knowledge tools throughout
- Tag all nodes with source:agent or source:external
""",
  allowed_tools=["WebSearch", "WebFetch", "mcp__knowledge__*"]
)
```

### Phase 3: Verification

```python
Task(
  subagent_type="general-purpose",
  description="Verify [topic] research",
  prompt="""[Include research-verifier.md content]

RESEARCH PROJECT: [project-id]
FINDINGS TO VERIFY:
[All findings from Phase 2]

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Record problems for any inaccuracies found
- Tag corrections with source:agent
""",
  allowed_tools=["WebSearch", "WebFetch", "mcp__knowledge__*"]
)
```

### Phase 4: Synthesis

```python
Task(
  subagent_type="general-purpose",
  description="Synthesize [topic] research",
  prompt="""[Include research-synthesizer.md content]

RESEARCH PROJECT: [project-id]
VERIFIED FINDINGS:
[Output from verifier]

CONFLICTS TO RESOLVE:
[Any contradictions found]

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Record arguments as thoughts with tags: argument, synthesis
- Record final decisions with full rationale
- Link everything: thought → decision, discovery → supports → decision
""",
  allowed_tools=["mcp__knowledge__*"]
)
```

### Phase 5: Linking (NEW)

```python
Task(
  subagent_type="general-purpose",
  description="Link [topic] research nodes",
  prompt="""[Include research-linker.md content]

RESEARCH PROJECT: [project-id]

Your job:
1. Find all unlinked discoveries and thoughts from this research
2. Connect them to each other (supports, contradicts, led_to)
3. Connect them to existing projects/tasks/knowledge
4. Report what you linked

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Use traverse_related to see existing connections
- Create edges, don't create new content
""",
  allowed_tools=["mcp__knowledge__*"]
)
```

### Phase 6: Documentation (NEW)

```python
Task(
  subagent_type="general-purpose",
  description="Write [topic] research report",
  prompt="""[Include research-writer.md content]

RESEARCH PROJECT: [project-id]
OUTPUT PATH: research/[topic-slug]/report.md

Your job:
1. Gather all research nodes from this session
2. Write comprehensive markdown report
3. Include all findings, reasoning chains, decisions
4. Write sources.md with all references
5. Make it readable without the knowledge graph

IMPORTANT:
- Call set_context(project="research:[topic-slug]") first
- Include node IDs for traceability
- Follow the document structure in research-writer.md
""",
  allowed_tools=["mcp__knowledge__*", "Write", "Read"]
)
```

### Phase 7: Report to User

Present to user:
1. **Executive Summary** - Key findings in 2-3 paragraphs
2. **Recommendations** - What to do based on research
3. **Workspace** - Path to full report: `research/[topic-slug]/report.md`
4. **Knowledge Graph** - How to explore: `search_knowledge("[topic]")`
5. **Continue Later** - Project ID for resuming: `research:[topic-slug]`

## Research Workspace Structure

```
research/
└── [topic-slug]/
    ├── report.md        # Comprehensive research document
    ├── sources.md       # All references and links
    └── notes/           # Any additional working files
```

## Continuing Research

When user says `/research continue` or wants to extend:

1. Load existing research project: `set_context(project="research:[id]")`
2. Show what was researched before: `search_knowledge` within that project
3. Ask what aspect to investigate further
4. Run focused research on that aspect
5. Update the report.md with new findings

## Linking to Existing Work

When research relates to a project or task:

```python
# Link research project to main project
link_nodes(research_project_id, main_project_id, "references")

# Link key findings to relevant tasks
link_nodes(discovery_id, task_id, "supports")
link_nodes(decision_id, task_id, "references")
```

## Example Flow

```
User: /research

Claude: "How would you like to proceed?"
- [ ] New Research
- [x] Continue Existing
- [ ] Link to Project

User: Continue Existing

Claude: "Found 2 previous research sessions:"
1. research:graph-knowledge-systems (Jan 24) - Graph knowledge for AI agents
2. research:python-cli-tools (Jan 20) - CLI framework comparison

User: research:graph-knowledge-systems

Claude: "Loading research context..."
- 30 discoveries, 5 decisions recorded
- Main conclusion: Keep custom system for provenance

"What aspect would you like to research further?"
- [ ] Deeper dive on specific tool (Graphiti, Mem0, etc.)
- [x] Implementation patterns
- [ ] Performance benchmarks

User: Implementation patterns

Claude: [Runs focused research on implementation patterns]
[Updates report.md with new section]
[Links new findings to existing discoveries]

"Research extended. New findings added to research/graph-knowledge-systems/report.md"
```

## Notes

- Research projects persist in knowledge graph as `project` nodes with "research:" prefix
- All nodes created during research are linked to the research project
- Reports are standalone markdown files that don't require the knowledge graph to read
- Use `search_knowledge` to explore reasoning chains after research
- Total research typically creates 30-100+ knowledge nodes with extensive linking
