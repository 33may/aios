/**
 * TypeScript types for the Knowledge Graph
 */

// Node types
export type NodeType =
  | 'project'
  | 'session'
  | 'task'
  | 'decision'
  | 'discovery'
  | 'idea'
  | 'note'
  | 'thought'
  | 'constraint'
  | 'problem'
  | 'fix'
  | 'resource';

// Edge types
export type EdgeType =
  | 'contains'
  | 'related_to'
  | 'references'
  | 'spawned'
  | 'led_to'
  | 'supports'
  | 'contradicts'
  | 'constrained_by'
  | 'fixed_by'
  | 'blocked_by'
  | 'decided_in'
  | 'preceded_by'
  | 'refined_by';

// Node interface
export interface Node {
  uuid: string;
  type: NodeType;
  content: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

// Edge interface
export interface Edge {
  uuid: string;
  type: EdgeType;
  source_id: string;
  target_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

// Project interface (extended Node with stats)
export interface Project {
  uuid: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  task_count: number;
  decision_count: number;
  discovery_count: number;
}

// Tree node for hierarchical views
export interface TreeNode {
  uuid: string;
  type: NodeType;
  content: string;
  created_at: string;
  children: TreeNode[];
  status?: string;
}

// Search result
export interface SearchResult {
  content: string;
  score: number;
  type: NodeType;
  source_file?: string;
  captured_at?: string;
  episode_type?: string;
}

// API response types
export interface NodeListResponse {
  nodes: Node[];
  total: number;
}

export interface EdgeListResponse {
  edges: Edge[];
  total: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export interface StatsResponse {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

// Node styling for graph visualization
export const NODE_COLORS: Record<NodeType, string> = {
  project: '#3b82f6',    // blue
  session: '#6366f1',    // indigo
  task: '#22c55e',       // green (default)
  decision: '#f59e0b',   // amber
  discovery: '#06b6d4',  // cyan
  idea: '#a855f7',       // purple
  note: '#64748b',       // slate
  thought: '#8b5cf6',    // violet
  constraint: '#f97316', // orange
  problem: '#ef4444',    // red
  fix: '#10b981',        // emerald
  resource: '#0ea5e9',   // sky
};

// Task status colors (distinct colors for each status)
export const TASK_STATUS_COLORS: Record<string, string> = {
  pending: '#6b7280',     // gray-500 - waiting/not started
  in_progress: '#2563eb', // blue-600 - active work
  completed: '#16a34a',   // green-600 - done
  blocked: '#dc2626',     // red-600 - blocked/stuck
};

export const NODE_SHAPES: Record<NodeType, string> = {
  project: 'diamond',
  session: 'box',
  task: 'box',
  decision: 'star',
  discovery: 'ellipse',
  idea: 'ellipse',
  note: 'text',
  thought: 'ellipse',
  constraint: 'hexagon',
  problem: 'triangle',
  fix: 'triangleDown',
  resource: 'database',
};

// All node types for forms
export const NODE_TYPES: NodeType[] = [
  'project',
  'session',
  'task',
  'decision',
  'discovery',
  'idea',
  'note',
  'thought',
  'constraint',
  'problem',
  'fix',
  'resource',
];

// All edge types for forms
export const EDGE_TYPES: EdgeType[] = [
  'contains',
  'related_to',
  'references',
  'spawned',
  'led_to',
  'supports',
  'contradicts',
  'constrained_by',
  'fixed_by',
  'blocked_by',
  'decided_in',
  'preceded_by',
  'refined_by',
];
