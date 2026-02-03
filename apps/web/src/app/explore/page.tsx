'use client';

import { useNodes, useEdges, useNode, useNodeEdges, useProjects, useUpdateNode, useDeleteNode } from '@/hooks/useKnowledgeGraph';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, useMemo, Suspense } from 'react';
import Link from 'next/link';
import { Network, X, ExternalLink, ArrowLeft, ArrowRight, FolderKanban, Edit, Save, Trash2 } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TASK_STATUS_COLORS } from '@/types';
import { NODE_COLORS, type NodeType, type Node, type Edge } from '@/types';
import * as api from '@/lib/api';

function ExplorePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialNodeId = searchParams.get('node');

  // anchorNodeId = center of the graph (changes on double-click)
  // selectedNodeId = node shown in details panel (changes on single-click)
  const [anchorNodeId, setAnchorNodeId] = useState<string | null>(initialNodeId);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [focusDepth, setFocusDepth] = useState(2);
  const [showLabels, setShowLabels] = useState(true);
  const [nodeLimit, setNodeLimit] = useState(200);

  // Fetch all nodes and edges
  const { data: allNodesData, isLoading: nodesLoading } = useNodes({ limit: nodeLimit });
  const { data: allEdgesData, isLoading: edgesLoading } = useEdges({ limit: nodeLimit * 2 });

  // Fetch edges for anchor node to get INCOMING (1 level)
  const { data: anchorEdgesData } = useNodeEdges(anchorNodeId ?? '');

  // Fetch anchor node details
  const { data: anchorNode } = useNode(anchorNodeId ?? '');

  // Fetch selected node details
  const { data: selectedNode } = useNode(selectedNodeId ?? '');

  // Fetch selected node edges for details panel
  const { data: selectedNodeEdges } = useNodeEdges(selectedNodeId ?? '');

  // Fetch projects for quick switching
  const { data: projectsData } = useProjects();

  // Mutations
  const updateNode = useUpdateNode();
  const deleteNode = useDeleteNode();

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editStatus, setEditStatus] = useState<string>('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Connected nodes for the connections list
  const [connectedNodes, setConnectedNodes] = useState<Record<string, Node>>({});

  // Incoming nodes (1 level) for the graph
  const [incomingNodes, setIncomingNodes] = useState<Node[]>([]);

  // Outgoing nodes (N levels) for the graph - manually traversed
  const [outgoingNodes, setOutgoingNodes] = useState<Node[]>([]);
  const [outgoingEdgeIds, setOutgoingEdgeIds] = useState<Set<string>>(new Set());

  // Fetch incoming nodes (nodes that point TO the anchor) - 1 level only
  useEffect(() => {
    if (!anchorEdgesData?.edges || !anchorNodeId) {
      setIncomingNodes([]);
      return;
    }

    // Get edges where target is the anchor (incoming)
    const incomingEdges = anchorEdgesData.edges.filter(e => e.target_id === anchorNodeId);
    const sourceIds = incomingEdges.map(e => e.source_id);

    const fetchIncoming = async () => {
      const nodes: Node[] = [];
      for (const id of sourceIds) {
        try {
          const n = await api.getNode(id);
          nodes.push(n);
        } catch {
          // Node might not exist
        }
      }
      setIncomingNodes(nodes);
    };

    if (sourceIds.length > 0) {
      fetchIncoming();
    } else {
      setIncomingNodes([]);
    }
  }, [anchorEdgesData, anchorNodeId]);

  // Fetch outgoing nodes (N levels) - manually traverse OUTGOING edges only
  useEffect(() => {
    if (!anchorNodeId || !allEdgesData?.edges) {
      setOutgoingNodes([]);
      setOutgoingEdgeIds(new Set());
      return;
    }

    let cancelled = false;

    const fetchOutgoing = async () => {
      const allNodes: Node[] = [];
      const visitedIds = new Set<string>([anchorNodeId]);
      const validEdgeIds = new Set<string>();
      let currentLevelIds = [anchorNodeId];

      // Traverse N levels of OUTGOING edges
      for (let level = 0; level < focusDepth; level++) {
        if (cancelled) return;

        const nextLevelIds: string[] = [];

        for (const nodeId of currentLevelIds) {
          // Find OUTGOING edges (where source_id = current node)
          const outgoingEdges = allEdgesData.edges.filter(
            e => e.source_id === nodeId && !visitedIds.has(e.target_id)
          );

          for (const edge of outgoingEdges) {
            validEdgeIds.add(edge.uuid);
            if (!visitedIds.has(edge.target_id)) {
              visitedIds.add(edge.target_id);
              nextLevelIds.push(edge.target_id);
            }
          }
        }

        // Fetch nodes for this level
        for (const id of nextLevelIds) {
          if (cancelled) return;
          try {
            const n = await api.getNode(id);
            if (!cancelled) {
              allNodes.push(n);
            }
          } catch {
            // Node might not exist
          }
        }

        currentLevelIds = nextLevelIds;
        if (currentLevelIds.length === 0) break;
      }

      if (!cancelled) {
        setOutgoingNodes(allNodes);
        setOutgoingEdgeIds(validEdgeIds);
      }
    };

    fetchOutgoing();

    return () => {
      cancelled = true;
    };
  }, [anchorNodeId, allEdgesData, focusDepth]);

  // Fetch connected node details
  useEffect(() => {
    if (!selectedNodeEdges?.edges) return;

    const nodeIds = new Set<string>();
    selectedNodeEdges.edges.forEach((e) => {
      if (e.source_id !== selectedNodeId) nodeIds.add(e.source_id);
      if (e.target_id !== selectedNodeId) nodeIds.add(e.target_id);
    });

    const fetchNodes = async () => {
      const nodes: Record<string, Node> = {};
      for (const id of nodeIds) {
        try {
          const n = await api.getNode(id);
          nodes[id] = n;
        } catch {
          // Node might not exist
        }
      }
      setConnectedNodes(nodes);
    };

    fetchNodes();
  }, [selectedNodeEdges, selectedNodeId]);

  // Auto-select first project on startup
  useEffect(() => {
    if (!initialNodeId && !anchorNodeId && allNodesData?.nodes && allNodesData.nodes.length > 0) {
      const projectNode = allNodesData.nodes.find((n) => n.type === 'project');
      const defaultNode = projectNode || allNodesData.nodes[0];
      setAnchorNodeId(defaultNode.uuid);
      setSelectedNodeId(defaultNode.uuid);
    }
  }, [initialNodeId, anchorNodeId, allNodesData]);

  // Handle double-click to anchor/focus on a node (changes graph center)
  const handleNodeAnchor = (nodeId: string) => {
    setAnchorNodeId(nodeId);
    setSelectedNodeId(nodeId);
  };

  // Edit handlers
  const handleEdit = () => {
    if (selectedNode) {
      setEditContent(selectedNode.content);
      setEditStatus((selectedNode.metadata?.status as string) || 'pending');
      setEditing(true);
    }
  };

  const handleSave = async () => {
    if (!editContent.trim() || !selectedNodeId || !selectedNode) return;

    const updateData: { content: string; metadata?: Record<string, unknown> } = {
      content: editContent,
    };

    // Include status in metadata for task nodes
    if (selectedNode.type === 'task' && editStatus) {
      updateData.metadata = {
        ...selectedNode.metadata,
        status: editStatus,
      };
    }

    await updateNode.mutateAsync({
      id: selectedNodeId,
      data: updateData,
    });
    setEditing(false);
  };

  const handleDelete = async () => {
    if (!selectedNodeId) return;
    await deleteNode.mutateAsync(selectedNodeId);
    setDeleteDialogOpen(false);
    setSelectedNodeId(null);
  };

  // Compute connections
  const incomingEdges = selectedNodeEdges?.edges.filter((e) => e.target_id === selectedNodeId) ?? [];
  const outgoingEdges = selectedNodeEdges?.edges.filter((e) => e.source_id === selectedNodeId) ?? [];

  // Determine which data to display
  // 1 level incoming (always) + N levels outgoing (from slider)
  const displayData = useMemo(() => {
    if (anchorNodeId && anchorNode) {
      const nodes: Node[] = [];
      const nodeIds = new Set<string>();
      const incomingNodeIds = new Set<string>(); // Track which nodes are incoming (parents)

      // Add anchor node
      nodes.push(anchorNode);
      nodeIds.add(anchorNode.uuid);

      // Add 1 level of INCOMING nodes (nodes that point TO anchor)
      incomingNodes.forEach((n) => {
        if (!nodeIds.has(n.uuid)) {
          nodes.push(n);
          nodeIds.add(n.uuid);
          incomingNodeIds.add(n.uuid); // Mark as incoming/parent node
        }
      });

      // Add N levels of OUTGOING nodes (manually traversed)
      outgoingNodes.forEach((n) => {
        if (!nodeIds.has(n.uuid)) {
          nodes.push(n);
          nodeIds.add(n.uuid);
        }
      });

      // Build edges (dedupe to avoid DataSet errors):
      // - Edges from incoming nodes TO anchor only
      // - Outgoing edges that we traversed
      const edgeMap = new Map<string, Edge>();

      // Add incoming edges (parent -> anchor)
      allEdgesData?.edges.forEach((e) => {
        if (incomingNodeIds.has(e.source_id) && e.target_id === anchorNodeId) {
          edgeMap.set(e.uuid, e);
        }
      });

      // Add outgoing edges (the ones we traversed)
      allEdgesData?.edges.forEach((e) => {
        if (outgoingEdgeIds.has(e.uuid)) {
          edgeMap.set(e.uuid, e);
        }
      });

      return { nodes, edges: Array.from(edgeMap.values()) };
    }

    return { nodes: [], edges: [] };
  }, [anchorNodeId, anchorNode, allEdgesData, incomingNodes, outgoingNodes, outgoingEdgeIds]);

  const isLoading = nodesLoading || edgesLoading || !anchorNode;

  // Update URL when anchor changes
  useEffect(() => {
    if (anchorNodeId) {
      router.replace(`/explore?node=${anchorNodeId}`, { scroll: false });
    }
  }, [anchorNodeId, router]);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-0">
      {/* Left: Node Details Panel */}
      <div className="w-1/2 border-r flex flex-col overflow-hidden">
        {/* Project Selector Bar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/50">
          <FolderKanban className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Project:</span>
          <div className="flex gap-1 flex-wrap">
            {projectsData?.map((project) => (
              <Button
                key={project.uuid}
                variant={anchorNodeId === project.uuid ? "default" : "outline"}
                size="sm"
                className="h-6 text-xs px-2"
                onClick={() => handleNodeAnchor(project.uuid)}
              >
                {project.name}
              </Button>
            ))}
          </div>
        </div>

        {/* Header with node info and actions */}
        <div className="flex items-center gap-2 p-4 border-b bg-card">
          <div className="flex-1 min-w-0">
            {selectedNode ? (
              <div className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full shrink-0"
                  style={{
                    backgroundColor: NODE_COLORS[selectedNode.type as NodeType] ?? '#6b7280',
                  }}
                />
                <Badge variant="outline" className="capitalize shrink-0">
                  {selectedNode.type}
                </Badge>
                <span className="text-sm text-muted-foreground truncate">
                  {selectedNode.metadata?.subject || selectedNode.content.substring(0, 40)}
                </span>
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">Select a node</span>
            )}
          </div>
          {selectedNode && (
            <div className="flex gap-1 shrink-0">
              <Button variant="ghost" size="icon" onClick={handleEdit} title="Edit">
                <Edit className="h-4 w-4" />
              </Button>
              <Link href={`/nodes/${selectedNodeId}`}>
                <Button variant="ghost" size="icon" title="Full page">
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </Link>
              <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon" title="Delete">
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Delete Node</DialogTitle>
                    <DialogDescription>
                      This will permanently delete this node and all its connected edges.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="flex justify-end gap-2 pt-4">
                    <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button variant="destructive" onClick={handleDelete} disabled={deleteNode.isPending}>
                      {deleteNode.isPending ? 'Deleting...' : 'Delete'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {!selectedNodeId ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <div className="text-center">
                <Network className="mx-auto h-12 w-12 mb-4" />
                <p>Click a node in the graph to view details</p>
              </div>
            </div>
          ) : !selectedNode ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Loading...
            </div>
          ) : (
            <>
              {/* Subject */}
              {selectedNode.metadata?.subject && (
                <div>
                  <Label className="text-xs text-muted-foreground">Subject</Label>
                  <h2 className="text-lg font-semibold">{selectedNode.metadata.subject}</h2>
                </div>
              )}

              {/* Content */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Content</CardTitle>
                </CardHeader>
                <CardContent>
                  {editing ? (
                    <div className="space-y-3">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full min-h-[150px] p-3 rounded-md border bg-background resize-y text-sm"
                      />
                      {/* Status selector for task nodes */}
                      {selectedNode?.type === 'task' && (
                        <div className="flex items-center gap-2">
                          <Label className="text-sm">Status:</Label>
                          <Select value={editStatus} onValueChange={setEditStatus}>
                            <SelectTrigger className="w-[180px]">
                              <SelectValue placeholder="Select status" />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(TASK_STATUS_COLORS).map(([status, color]) => (
                                <SelectItem key={status} value={status}>
                                  <div className="flex items-center gap-2">
                                    <div
                                      className="h-3 w-3 rounded-full"
                                      style={{ backgroundColor: color }}
                                    />
                                    <span className="capitalize">{status.replace(/_/g, ' ')}</span>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
                          <X className="h-3 w-3 mr-1" /> Cancel
                        </Button>
                        <Button size="sm" onClick={handleSave} disabled={updateNode.isPending}>
                          <Save className="h-3 w-3 mr-1" />
                          {updateNode.isPending ? 'Saving...' : 'Save'}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{selectedNode.content}</p>
                  )}
                </CardContent>
              </Card>

              {/* Metadata */}
              {selectedNode.metadata && Object.keys(selectedNode.metadata).filter(k => k !== 'subject').length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Metadata</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-1 text-sm">
                      {Object.entries(selectedNode.metadata)
                        .filter(([key]) => key !== 'subject')
                        .map(([key, value]) => (
                          <div key={key} className="flex gap-2">
                            <span className="text-muted-foreground min-w-[100px]">{key}:</span>
                            <span className="break-all">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Connections */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span>Connections</span>
                    <span className="text-xs font-normal text-muted-foreground">
                      {incomingEdges.length} in / {outgoingEdges.length} out
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedNodeEdges?.edges.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No connections</p>
                  ) : (
                    <div className="space-y-1 max-h-[300px] overflow-auto">
                      {selectedNodeEdges?.edges.map((edge) => {
                        const isOutgoing = edge.source_id === selectedNodeId;
                        const otherNodeId = isOutgoing ? edge.target_id : edge.source_id;
                        const otherNode = connectedNodes[otherNodeId];
                        const displayName = otherNode
                          ? otherNode.metadata?.subject ||
                            otherNode.content.substring(0, 40) +
                              (otherNode.content.length > 40 ? '...' : '')
                          : 'Loading...';

                        return (
                          <button
                            key={edge.uuid}
                            onClick={() => setSelectedNodeId(otherNodeId)}
                            onDoubleClick={() => handleNodeAnchor(otherNodeId)}
                            className="flex items-center gap-2 p-2 rounded hover:bg-accent w-full text-left text-sm"
                          >
                            {isOutgoing ? (
                              <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                            ) : (
                              <ArrowLeft className="h-3 w-3 text-muted-foreground shrink-0" />
                            )}
                            <Badge variant="secondary" className="text-xs shrink-0">
                              {edge.type.replace(/_/g, ' ')}
                            </Badge>
                            {otherNode && (
                              <div
                                className="h-2 w-2 rounded-full shrink-0"
                                style={{
                                  backgroundColor: NODE_COLORS[otherNode.type as NodeType] ?? '#6b7280',
                                }}
                              />
                            )}
                            <span className="truncate">{displayName}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Timestamps */}
              <div className="text-xs text-muted-foreground space-y-1">
                <div>Created: {new Date(selectedNode.created_at).toLocaleString()}</div>
                <div>Updated: {new Date(selectedNode.updated_at).toLocaleString()}</div>
              </div>
            </>
          )}
        </div>

        {/* Footer with graph controls */}
        <div className="flex items-center gap-4 px-4 py-2 border-t bg-muted/50 text-xs">
          <span className="text-muted-foreground">In: 1</span>
          <span className="text-muted-foreground">|</span>
          <Label className="text-muted-foreground">Out: {focusDepth}</Label>
          <input
            type="range"
            min={1}
            max={5}
            value={focusDepth}
            onChange={(e) => setFocusDepth(parseInt(e.target.value))}
            className="w-20"
          />
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="showLabels"
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              className="rounded border"
            />
            <Label htmlFor="showLabels" className="text-muted-foreground">Labels</Label>
          </div>
          <span className="text-muted-foreground ml-auto">
            {displayData.nodes.length} nodes
          </span>
        </div>
      </div>

      {/* Right: Graph Area */}
      <div className="w-1/2 bg-card">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex items-center gap-2 text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Loading graph...
            </div>
          </div>
        ) : displayData.nodes.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <Network className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No nodes to display</h3>
              <p className="mt-2 text-muted-foreground">
                Select a node to explore
              </p>
            </div>
          </div>
        ) : (
          <GraphCanvas
            nodes={displayData.nodes}
            edges={displayData.edges}
            selectedNodeId={selectedNodeId}
            onNodeSelect={setSelectedNodeId}
            onNodeDoubleClick={handleNodeAnchor}
            showLabels={showLabels}
          />
        )}
      </div>
    </div>
  );
}

export default function ExplorePage() {
  return (
    <Suspense fallback={
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading...
        </div>
      </div>
    }>
      <ExplorePageContent />
    </Suspense>
  );
}
