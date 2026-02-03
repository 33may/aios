/**
 * API client for the Knowledge Graph backend
 */

import type {
  Node,
  Edge,
  Project,
  TreeNode,
  SearchResult,
  NodeListResponse,
  EdgeListResponse,
  SearchResponse,
  StatsResponse,
  NodeType,
  EdgeType,
} from '@/types';

function getApiBase(): string {
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

const API_BASE = getApiBase();

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// Health check
export async function getHealth(): Promise<{ status: string; database: string }> {
  return fetchAPI('/health');
}

// Stats
export async function getStats(): Promise<StatsResponse> {
  return fetchAPI('/stats');
}

// --- Nodes ---

export async function getNodes(params?: {
  type?: NodeType;
  limit?: number;
}): Promise<NodeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set('type', params.type);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchAPI(`/nodes${query ? `?${query}` : ''}`);
}

export async function getNode(id: string): Promise<Node> {
  return fetchAPI(`/nodes/${id}`);
}

export async function createNode(data: {
  type: NodeType;
  content: string;
  metadata?: Record<string, unknown>;
}): Promise<Node> {
  return fetchAPI('/nodes', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateNode(
  id: string,
  data: {
    content?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<Node> {
  return fetchAPI(`/nodes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteNode(id: string): Promise<{ message: string; uuid: string }> {
  return fetchAPI(`/nodes/${id}`, { method: 'DELETE' });
}

export async function getNodeTypes(): Promise<{ types: NodeType[] }> {
  return fetchAPI('/nodes/types');
}

// --- Edges ---

export async function getEdges(params?: {
  type?: EdgeType;
  source_id?: string;
  target_id?: string;
  limit?: number;
}): Promise<EdgeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set('type', params.type);
  if (params?.source_id) searchParams.set('source_id', params.source_id);
  if (params?.target_id) searchParams.set('target_id', params.target_id);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchAPI(`/edges${query ? `?${query}` : ''}`);
}

export async function getEdge(id: string): Promise<Edge> {
  return fetchAPI(`/edges/${id}`);
}

export async function createEdge(data: {
  type: EdgeType;
  source_id: string;
  target_id: string;
  metadata?: Record<string, unknown>;
}): Promise<Edge> {
  return fetchAPI('/edges', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteEdge(id: string): Promise<{ message: string; uuid: string }> {
  return fetchAPI(`/edges/${id}`, { method: 'DELETE' });
}

export async function getNodeEdges(
  nodeId: string,
  direction: 'incoming' | 'outgoing' | 'both' = 'both'
): Promise<EdgeListResponse> {
  return fetchAPI(`/edges/node/${nodeId}?direction=${direction}`);
}

export async function getEdgeTypes(): Promise<{ types: EdgeType[] }> {
  return fetchAPI('/edges/types');
}

// --- Search ---

export async function search(params: {
  query: string;
  limit?: number;
  min_score?: number;
}): Promise<SearchResponse> {
  return fetchAPI('/search', {
    method: 'POST',
    body: JSON.stringify({
      query: params.query,
      limit: params.limit ?? 10,
      min_score: params.min_score ?? 0,
    }),
  });
}

export async function traverse(params: {
  node_id: string;
  depth?: number;
  edge_types?: EdgeType[];
}): Promise<{
  start_node: {
    uuid: string;
    type: NodeType;
    content: string;
    created_at: string;
  };
  levels: Record<string, Array<{
    uuid: string;
    type: NodeType;
    content: string;
    created_at: string;
  }>>;
  total_nodes: number;
}> {
  return fetchAPI('/search/traverse', {
    method: 'POST',
    body: JSON.stringify({
      node_id: params.node_id,
      depth: params.depth ?? 2,
      edge_types: params.edge_types,
    }),
  });
}

export async function getRelated(
  nodeId: string,
  params?: {
    edge_type?: EdgeType;
    direction?: 'incoming' | 'outgoing' | 'both';
  }
): Promise<{
  node_id: string;
  related: Array<{
    node: {
      uuid: string;
      type: NodeType;
      content: string;
      created_at: string;
    };
    edge: {
      uuid: string;
      type: EdgeType;
      direction: 'incoming' | 'outgoing';
    };
  }>;
  total: number;
}> {
  const searchParams = new URLSearchParams();
  if (params?.edge_type) searchParams.set('edge_type', params.edge_type);
  if (params?.direction) searchParams.set('direction', params.direction);

  const query = searchParams.toString();
  return fetchAPI(`/search/related/${nodeId}${query ? `?${query}` : ''}`);
}

// --- Projects ---

export async function getProjects(): Promise<Project[]> {
  return fetchAPI('/projects');
}

export async function getProject(id: string): Promise<Project> {
  return fetchAPI(`/projects/${id}`);
}

export async function createProject(data: {
  name: string;
  description?: string;
}): Promise<Project> {
  return fetchAPI('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getProjectTree(
  id: string,
  maxDepth: number = 5
): Promise<{
  project: Project;
  tree: TreeNode[];
}> {
  return fetchAPI(`/projects/${id}/tree?max_depth=${maxDepth}`);
}

export async function deleteProject(
  id: string,
  cascade: boolean = false
): Promise<{ message: string; uuid: string; cascade: boolean }> {
  return fetchAPI(`/projects/${id}?cascade=${cascade}`, { method: 'DELETE' });
}
