'use client';

import { create } from 'zustand';
import type { Node, NodeType } from '@/types';

interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // Selected node (for graph interactions)
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;

  // Node filter
  nodeTypeFilter: NodeType | null;
  setNodeTypeFilter: (type: NodeType | null) => void;

  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // Dialog states
  createNodeDialogOpen: boolean;
  setCreateNodeDialogOpen: (open: boolean) => void;
  createEdgeDialogOpen: boolean;
  setCreateEdgeDialogOpen: (open: boolean) => void;

  // Node being edited
  editingNode: Node | null;
  setEditingNode: (node: Node | null) => void;

  // Graph view options
  graphDepth: number;
  setGraphDepth: (depth: number) => void;
  showLabels: boolean;
  setShowLabels: (show: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Sidebar
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  // Selected node
  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  // Node filter
  nodeTypeFilter: null,
  setNodeTypeFilter: (type) => set({ nodeTypeFilter: type }),

  // Search
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  // Dialog states
  createNodeDialogOpen: false,
  setCreateNodeDialogOpen: (open) => set({ createNodeDialogOpen: open }),
  createEdgeDialogOpen: false,
  setCreateEdgeDialogOpen: (open) => set({ createEdgeDialogOpen: open }),

  // Node being edited
  editingNode: null,
  setEditingNode: (node) => set({ editingNode: node }),

  // Graph view options
  graphDepth: 2,
  setGraphDepth: (depth) => set({ graphDepth: depth }),
  showLabels: true,
  setShowLabels: (show) => set({ showLabels: show }),
}));
