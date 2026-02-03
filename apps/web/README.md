# Knowledge Graph Frontend

React/Next.js web frontend for the AIOS knowledge graph.

## Features

- **Dashboard**: Overview of knowledge graph stats, recent nodes, and projects
- **Graph Visualization**: Interactive vis-network graph with zoom, pan, and node selection
- **Projects**: Create, view, and manage projects with hierarchical task trees
- **Nodes**: Browse, filter, create, edit, and delete nodes
- **Search**: Semantic search across the knowledge graph
- **CRUD Operations**: Full create/read/update/delete for nodes and edges

## Tech Stack

- Next.js 14+ (App Router, TypeScript)
- vis-network (graph visualization)
- shadcn/ui + Tailwind CSS
- TanStack Query (data fetching)
- Zustand (UI state)

## Prerequisites

- Node.js 20+ (or 18 with limitations)
- Knowledge Graph API running on http://localhost:8000

## Getting Started

1. Install dependencies:
   ```bash
   cd apps/web
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:3000

## Environment Variables

Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Pages

- `/` - Dashboard with stats and recent activity
- `/graph` - Interactive graph visualization
- `/projects` - Project list
- `/projects/[id]` - Project detail with task tree
- `/nodes` - Node browser with filters
- `/nodes/[id]` - Node detail and edit
- `/search` - Semantic search

## API Backend

The frontend requires the FastAPI backend running. From the project root:

```bash
cd /home/may33/projects/aios
python -m apps.api.run
```

Or with uvicorn:
```bash
uvicorn apps.api.main:app --reload --port 8000
```
