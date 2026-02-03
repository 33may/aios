'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/lib/api';
import type { NodeType, EdgeType } from '@/types';

// Query keys
export const queryKeys = {
  health: ['health'] as const,
  stats: ['stats'] as const,
  nodes: (params?: { type?: NodeType; limit?: number }) =>
    ['nodes', params] as const,
  node: (id: string) => ['node', id] as const,
  nodeTypes: ['nodeTypes'] as const,
  edges: (params?: {
    type?: EdgeType;
    source_id?: string;
    target_id?: string;
    limit?: number;
  }) => ['edges', params] as const,
  edge: (id: string) => ['edge', id] as const,
  nodeEdges: (nodeId: string, direction: string) =>
    ['nodeEdges', nodeId, direction] as const,
  edgeTypes: ['edgeTypes'] as const,
  search: (query: string, limit?: number) => ['search', query, limit] as const,
  traverse: (nodeId: string, depth?: number) =>
    ['traverse', nodeId, depth] as const,
  related: (nodeId: string, edgeType?: EdgeType, direction?: string) =>
    ['related', nodeId, edgeType, direction] as const,
  projects: ['projects'] as const,
  project: (id: string) => ['project', id] as const,
  projectTree: (id: string, depth?: number) =>
    ['projectTree', id, depth] as const,
};

// Health
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.getHealth,
    refetchInterval: 30000,
  });
}

// Stats
export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: api.getStats,
    refetchInterval: 60000,
  });
}

// Nodes
export function useNodes(params?: { type?: NodeType; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.nodes(params),
    queryFn: () => api.getNodes(params),
  });
}

export function useNode(id: string) {
  return useQuery({
    queryKey: queryKeys.node(id),
    queryFn: () => api.getNode(id),
    enabled: !!id,
  });
}

export function useNodeTypes() {
  return useQuery({
    queryKey: queryKeys.nodeTypes,
    queryFn: api.getNodeTypes,
    staleTime: Infinity,
  });
}

export function useCreateNode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createNode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

export function useUpdateNode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { content?: string; metadata?: Record<string, unknown> };
    }) => api.updateNode(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.node(id) });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });
}

export function useDeleteNode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteNode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

// Edges
export function useEdges(params?: {
  type?: EdgeType;
  source_id?: string;
  target_id?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: queryKeys.edges(params),
    queryFn: () => api.getEdges(params),
  });
}

export function useEdge(id: string) {
  return useQuery({
    queryKey: queryKeys.edge(id),
    queryFn: () => api.getEdge(id),
    enabled: !!id,
  });
}

export function useNodeEdges(
  nodeId: string,
  direction: 'incoming' | 'outgoing' | 'both' = 'both'
) {
  return useQuery({
    queryKey: queryKeys.nodeEdges(nodeId, direction),
    queryFn: () => api.getNodeEdges(nodeId, direction),
    enabled: !!nodeId,
  });
}

export function useEdgeTypes() {
  return useQuery({
    queryKey: queryKeys.edgeTypes,
    queryFn: api.getEdgeTypes,
    staleTime: Infinity,
  });
}

export function useCreateEdge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createEdge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['nodeEdges'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

export function useDeleteEdge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteEdge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['nodeEdges'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

// Search
export function useSearch(query: string, limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.search(query, limit),
    queryFn: () => api.search({ query, limit }),
    enabled: query.length > 0,
  });
}

export function useTraverse(nodeId: string, depth: number = 2) {
  return useQuery({
    queryKey: queryKeys.traverse(nodeId, depth),
    queryFn: () => api.traverse({ node_id: nodeId, depth }),
    enabled: !!nodeId,
  });
}

export function useRelated(
  nodeId: string,
  edgeType?: EdgeType,
  direction?: 'incoming' | 'outgoing' | 'both'
) {
  return useQuery({
    queryKey: queryKeys.related(nodeId, edgeType, direction),
    queryFn: () =>
      api.getRelated(nodeId, { edge_type: edgeType, direction }),
    enabled: !!nodeId,
  });
}

// Projects
export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: api.getProjects,
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: queryKeys.project(id),
    queryFn: () => api.getProject(id),
    enabled: !!id,
  });
}

export function useProjectTree(id: string, depth: number = 5) {
  return useQuery({
    queryKey: queryKeys.projectTree(id, depth),
    queryFn: () => api.getProjectTree(id, depth),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, cascade }: { id: string; cascade?: boolean }) =>
      api.deleteProject(id, cascade),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}
