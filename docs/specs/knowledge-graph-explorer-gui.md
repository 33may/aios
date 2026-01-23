# Plan: Knowledge Graph GUI - Critical Analysis & Recommendation

> Saved: 2026-01-23
> Status: Planning complete, implementation pending

## Current State

The existing Streamlit dashboard (`apps/dashboard/app.py`) provides:
- Project/Task/Decision/Activity tabs
- Basic CRUD display with expanders
- Text-based task tree (indentation only)
- **No graph visualization whatsoever**

## Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Graph visualization | Critical | See connections between nodes |
| Explore/traverse | Critical | Navigate through relationships |
| Readable/maintainable | High | User wants to maintain it themselves |
| Note reading | Medium | View discoveries, decisions in context |
| Future research features | Medium | Extensibility for sources, citations |
| Not necessarily web-based | Open | User is open to alternatives |

---

## Critical Analysis of Options

### WEB-BASED

#### 1. Streamlit + Graph Add-ons (streamlit-agraph, pyvis)
**Verdict: REJECT - Band-aid solution**

| Pros | Cons |
|------|------|
| Minimal change | Streamlit fundamentally limited for interactivity |
| Python-only | Graph viz add-ons are janky, poor UX |
| Already working | Every interaction causes full page re-render |

#### 2. Dash + Cytoscape.js
**Verdict: STRONG CANDIDATE**

| Pros | Cons |
|------|------|
| Python callbacks | Learning curve for Dash patterns |
| Cytoscape is industry-standard graph viz | Still web-based (if that's a concern) |
| Professional look | Can be verbose |
| Great interactivity without full re-renders | |
| Plotly ecosystem for other viz | |

Example: Click node → show details panel, drag to rearrange, zoom/pan, search highlight

#### 3. Panel/HoloViews + Bokeh
**Verdict: MARGINAL IMPROVEMENT**

| Pros | Cons |
|------|------|
| More flexible than Streamlit | Graph viz not as mature as Cytoscape |
| Python | Similar paradigm, similar limitations |

#### 4. React/Vue + D3.js/Cytoscape.js (Full Custom)
**Verdict: BEST UX, HIGHEST COST**

| Pros | Cons |
|------|------|
| Complete control | Separate frontend codebase |
| Best possible UX | Requires API layer |
| Industry standard | TypeScript/JS knowledge needed |
| | More infrastructure to maintain |

---

### DESKTOP-BASED

#### 5. Dear PyGui
**Verdict: INTERESTING DARK HORSE**

| Pros | Cons |
|------|------|
| Pure Python | Less mature ecosystem |
| GPU-accelerated, fast | Documentation has gaps |
| Built-in node editor component | Graph viz needs custom work |
| Lightweight (<10MB) | Smaller community |
| Immediate mode GUI - very responsive | |

Could build a custom graph view using the drawing API or node editor primitives.

#### 6. PyQt/PySide
**Verdict: OVERKILL**

| Pros | Cons |
|------|------|
| Native desktop, professional | Complex, dated paradigm |
| Full control | QGraphicsView for graphs is significant work |
| | Large learning curve |

#### 7. Tauri + Web Frontend
**Verdict: GOOD FOR DESKTOP + WEB TECH**

| Pros | Cons |
|------|------|
| Lightweight desktop (~10MB vs Electron's 200MB) | Rust knowledge for backend parts |
| Can use any web graph lib (Cytoscape, D3) | Adds build complexity |
| Modern, fast | |

---

### TERMINAL-BASED (TUI)

#### 8. Textual
**Verdict: COMPLEMENT, NOT REPLACEMENT**

| Pros | Cons |
|------|------|
| Runs in terminal alongside Claude Code | Can't visualize graphs (ASCII at best) |
| Lightweight, no browser | Limited to text representation |
| Modern Python TUI | |

Good for quick task management, but can't fulfill graph viz requirement.

---

### LEVERAGE EXISTING TOOLS

#### 9. Neo4j Browser (Already Installed)
**Verdict: USE AS COMPLEMENT**

| Pros | Cons |
|------|------|
| Native graph viz, already working | Not customizable |
| Powerful Cypher queries | Separate from workflow |
| Free | Generic, not tailored to your domain |

**Recommendation**: Keep using for ad-hoc graph exploration, build custom UI for domain-specific features.

#### 10. Obsidian
**Verdict: DIFFERENT PARADIGM**

| Pros | Cons |
|------|------|
| Beautiful graph view | Markdown-based, needs export/sync |
| Plugin ecosystem | Different data model |
| Great for notes | |

Could export knowledge graph to Obsidian vault, but it's a separate system.

---

## Recommendation Matrix

| Option | Graph Viz | Interactivity | Maintainability | Learning Curve | Desktop |
|--------|-----------|---------------|-----------------|----------------|---------|
| Dash + Cytoscape | ★★★★★ | ★★★★☆ | ★★★★☆ | Medium | No |
| Dear PyGui | ★★★☆☆ | ★★★★★ | ★★★☆☆ | Medium | Yes |
| React + Cytoscape | ★★★★★ | ★★★★★ | ★★☆☆☆ | High | No |
| Tauri + Web | ★★★★★ | ★★★★★ | ★★★☆☆ | High | Yes |
| Neo4j Browser | ★★★★★ | ★★★☆☆ | N/A | Low | No |
| Textual (TUI) | ★☆☆☆☆ | ★★★☆☆ | ★★★★★ | Low | Terminal |

---

## Final Recommendation: **Tauri + React + Cytoscape.js**

Given user requirements:
- ✅ Desktop preferred
- ✅ Best product, complexity irrelevant
- ✅ Integrated graph visualization

### Why Tauri + React + Cytoscape.js

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Shell** | Tauri | 10MB app vs Electron's 200MB. Uses system webview. Rust backend for performance. |
| **Frontend** | React + TypeScript | Industry standard, huge ecosystem, excellent dev experience |
| **Graph Viz** | Cytoscape.js | Gold standard for interactive graphs. Layouts, zoom, pan, selection, styling |
| **Styling** | Tailwind CSS | Rapid UI development, consistent design |
| **State** | Zustand or Jotai | Lightweight state management |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │   Sidebar       │    │      Main View              │ │
│  │                 │    │  ┌───────────────────────┐  │ │
│  │  • Projects     │    │  │   Cytoscape Graph     │  │ │
│  │  • Filters      │    │  │                       │  │ │
│  │  • Search       │    │  │   [nodes + edges]     │  │ │
│  │  • Context      │    │  │                       │  │ │
│  │                 │    │  └───────────────────────┘  │ │
│  │                 │    │  ┌───────────────────────┐  │ │
│  │                 │    │  │   Detail Panel        │  │ │
│  │                 │    │  │   (selected node)     │  │ │
│  │                 │    │  └───────────────────────┘  │ │
│  └─────────────────┘    └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    Tauri Backend (Rust)                  │
│  • Neo4j driver (native, fast)                          │
│  • File system access                                    │
│  • IPC commands                                          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │        Neo4j            │
              │   (bolt://localhost)    │
              └─────────────────────────┘
```

### Key Features to Build

#### Phase 1: Core Graph Explorer
- [ ] Interactive graph view (zoom, pan, drag nodes)
- [ ] Node types visually distinct (color/shape: projects, tasks, decisions, discoveries)
- [ ] Click node → detail panel with full content
- [ ] Edge labels showing relationship types
- [ ] Layout algorithms (hierarchical for tasks, force-directed for exploration)

#### Phase 2: Navigation & Search
- [ ] Sidebar with project list
- [ ] Full-text search across all nodes
- [ ] Filter by node type, status, date range
- [ ] "Focus mode" - show only N hops from selected node
- [ ] Breadcrumb trail for navigation history

#### Phase 3: Task Management
- [ ] Quick status toggle (pending → in_progress → completed)
- [ ] Create new task/decision/discovery from UI
- [ ] Drag-and-drop to reparent tasks
- [ ] Keyboard shortcuts for power users

#### Phase 4: Research Features (Future)
- [ ] Source/citation links on discoveries
- [ ] Web fetch integration (preview URLs)
- [ ] Session timeline view
- [ ] Export to Obsidian/Markdown

---

## Tech Stack Details

| Layer | Technology | Purpose |
|-------|------------|---------|
| Desktop Shell | Tauri 2.0 | Native window, system tray, IPC |
| Frontend Framework | React 18 | Component-based UI |
| Graph Visualization | Cytoscape.js + react-cytoscapejs | Interactive graph |
| Styling | Tailwind CSS + shadcn/ui | Beautiful, consistent UI |
| State Management | Zustand | Simple, performant state |
| Build Tool | Vite | Fast HMR, TypeScript support |
| Backend | Rust + neo4rs | Native Neo4j driver |
| Testing | Vitest + Playwright | Unit + E2E tests |

---

## Project Structure

```
apps/explorer/
├── src-tauri/                 # Rust backend
│   ├── src/
│   │   ├── main.rs           # Entry point
│   │   ├── commands/         # IPC commands
│   │   │   ├── graph.rs      # Query nodes/edges
│   │   │   ├── tasks.rs      # CRUD tasks
│   │   │   └── context.rs    # Context management
│   │   └── neo4j.rs          # Neo4j connection
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                       # React frontend
│   ├── App.tsx
│   ├── components/
│   │   ├── Graph/
│   │   │   ├── GraphView.tsx      # Cytoscape wrapper
│   │   │   ├── NodeStyles.ts      # Visual styling
│   │   │   └── Layouts.ts         # Layout configs
│   │   ├── Sidebar/
│   │   │   ├── ProjectList.tsx
│   │   │   ├── Filters.tsx
│   │   │   └── Search.tsx
│   │   ├── Detail/
│   │   │   ├── NodeDetail.tsx
│   │   │   ├── TaskCard.tsx
│   │   │   └── DecisionCard.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       └── Input.tsx
│   ├── hooks/
│   │   ├── useGraph.ts           # Graph data fetching
│   │   ├── useNeo4j.ts           # Tauri IPC wrapper
│   │   └── useSelection.ts       # Selected node state
│   ├── stores/
│   │   ├── graphStore.ts         # Graph state
│   │   └── filterStore.ts        # Filter state
│   └── types/
│       └── graph.ts              # TypeScript types
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

---

## Implementation Plan

### Step 1: Scaffold Tauri + React project
```bash
npm create tauri-app@latest apps/explorer -- --template react-ts
cd apps/explorer
npm install cytoscape react-cytoscapejs @types/cytoscape
npm install -D tailwindcss postcss autoprefixer
```

### Step 2: Add Neo4j Rust driver
```toml
# src-tauri/Cargo.toml
[dependencies]
neo4rs = "0.7"
tokio = { version = "1", features = ["full"] }
```

### Step 3: Implement IPC commands for graph queries

### Step 4: Build Cytoscape graph component

### Step 5: Add sidebar, filters, detail panel

### Step 6: Polish UI, add keyboard shortcuts

### Step 7: Package for distribution

---

## Verification

1. **Build check**: `cd apps/explorer && npm run tauri build`
2. **Graph renders**: Launch app, see AIOS project with 6 tasks
3. **Interactivity**: Click node, see detail panel update
4. **Neo4j connection**: Query works, data persists
5. **Performance**: Smooth with 100+ nodes
