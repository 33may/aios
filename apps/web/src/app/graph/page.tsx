'use client';

import { useNodes, useEdges, useTraverse, useNode, useNodeEdges } from '@/hooks/useKnowledgeGraph';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSearchParams, useRouter } from 'next/navigation';
import { useState, useEffect, useMemo, Suspense } from 'react';
import Link from 'next/link';
import { Network, ZoomIn, X, Settings, ExternalLink, Target } from 'lucide-react';
import { NODE_COLORS, type NodeType, type Node, type Edge } from '@/types';

function GraphPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialNodeId = searchParams.get('node');

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [viewMode, setViewMode] = useState<'all' | 'focused'>('all');
  const [focusDepth, setFocusDepth] = useState(2);
  const [showLabels, setShowLabels] = useState(true);
  const [nodeLimit, setNodeLimit] = useState(200);

  // Fetch all nodes and edges for "all" mode
  const { data: allNodesData, isLoading: nodesLoading } = useNodes({ limit: nodeLimit });
  const { data: allEdgesData, isLoading: edgesLoading } = useEdges({ limit: nodeLimit * 2 });

  // Fetch traversal data for "focused" mode
  const { data: traverseData, isLoading: traverseLoading } = useTraverse(
    selectedNodeId ?? '',
    focusDepth
  );

  // Fetch selected node details
  const { data: selectedNode } = useNode(selectedNodeId ?? '');

  // Fetch selected node edges for details panel
  const { data: selectedNodeEdges } = useNodeEdges(selectedNodeId ?? '');

  // Handle double-click to anchor/focus on a node
  const handleNodeAnchor = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setViewMode('focused');
  };

  // Determine which data to display
  const displayData = useMemo(() => {
    if (viewMode === 'focused' && selectedNodeId && traverseData) {
      // Build nodes from traversal
      const nodes: Node[] = [];
      const nodeIds = new Set<string>();

      // Add start node
      if (traverseData.start_node) {
        nodes.push({
          uuid: traverseData.start_node.uuid,
          type: traverseData.start_node.type as NodeType,
          content: traverseData.start_node.content,
          created_at: traverseData.start_node.created_at,
          updated_at: traverseData.start_node.created_at,
          metadata: {},
        });
        nodeIds.add(traverseData.start_node.uuid);
      }

      // Add nodes from each level
      Object.values(traverseData.levels).forEach((levelNodes) => {
        levelNodes.forEach((n) => {
          if (!nodeIds.has(n.uuid)) {
            nodes.push({
              uuid: n.uuid,
              type: n.type as NodeType,
              content: n.content,
              created_at: n.created_at,
              updated_at: n.created_at,
              metadata: {},
            });
            nodeIds.add(n.uuid);
          }
        });
      });

      // Filter edges to only those between displayed nodes
      const edges =
        allEdgesData?.edges.filter(
          (e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)
        ) ?? [];

      return { nodes, edges };
    }

    return {
      nodes: allNodesData?.nodes ?? [],
      edges: allEdgesData?.edges ?? [],
    };
  }, [viewMode, selectedNodeId, traverseData, allNodesData, allEdgesData]);

  const isLoading = viewMode === 'all'
    ? nodesLoading || edgesLoading
    : traverseLoading;

  // Update URL when selection changes
  useEffect(() => {
    if (selectedNodeId) {
      const params = new URLSearchParams(searchParams);
      params.set('node', selectedNodeId);
      router.replace(`/graph?${params.toString()}`);
    }
  }, [selectedNodeId, router, searchParams]);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Main Graph Area */}
      <div className="flex-1 rounded-lg border bg-card">
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
                Create some nodes to see them in the graph
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

      {/* Sidebar */}
      <div className="w-96 flex flex-col gap-4 overflow-hidden">
        {/* View Controls */}
        <Card className="flex-shrink-0">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Settings className="h-4 w-4" />
              View Options
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>View Mode</Label>
              <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'all' | 'focused')}>
                <TabsList className="w-full">
                  <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
                  <TabsTrigger value="focused" className="flex-1" disabled={!selectedNodeId}>
                    Focused
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            {viewMode === 'focused' && (
              <div className="space-y-2">
                <Label>Depth: {focusDepth}</Label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={focusDepth}
                  onChange={(e) => setFocusDepth(parseInt(e.target.value))}
                  className="w-full"
                />
              </div>
            )}

            {viewMode === 'all' && (
              <div className="space-y-2">
                <Label>Node Limit</Label>
                <Select
                  value={nodeLimit.toString()}
                  onValueChange={(v) => setNodeLimit(parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="50">50 nodes</SelectItem>
                    <SelectItem value="100">100 nodes</SelectItem>
                    <SelectItem value="200">200 nodes</SelectItem>
                    <SelectItem value="500">500 nodes</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="showLabels"
                checked={showLabels}
                onChange={(e) => setShowLabels(e.target.checked)}
                className="rounded border"
              />
              <Label htmlFor="showLabels">Show Labels</Label>
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <div>Showing {displayData.nodes.length} nodes, {displayData.edges.length} edges</div>
              <div className="pt-2 border-t">
                <strong>Click</strong> = select node | <strong>Double-click</strong> = focus
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Selected Node Details */}
        {selectedNodeId && (
          <Card className="flex-1 overflow-hidden flex flex-col">
            <CardHeader className="pb-2 flex-shrink-0">
              <CardTitle className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  {selectedNode && (
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{
                        backgroundColor:
                          NODE_COLORS[selectedNode.type as NodeType] ?? '#6b7280',
                      }}
                    />
                  )}
                  Node Details
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setSelectedNodeId(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {selectedNode ? (
                <div className="space-y-4">
                  {/* Type and actions */}
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="capitalize">
                      {selectedNode.type}
                    </Badge>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleNodeAnchor(selectedNodeId)}
                        title="Focus on this node"
                      >
                        <Target className="h-4 w-4" />
                      </Button>
                      <Link href={`/nodes/${selectedNodeId}`}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          title="Open full details"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </Link>
                    </div>
                  </div>

                  {/* Subject if available */}
                  {selectedNode.metadata?.subject && (
                    <div>
                      <Label className="text-xs text-muted-foreground">Subject</Label>
                      <p className="text-sm font-medium">{selectedNode.metadata.subject}</p>
                    </div>
                  )}

                  {/* Content */}
                  <div>
                    <Label className="text-xs text-muted-foreground">Content</Label>
                    <p className="text-sm whitespace-pre-wrap mt-1">{selectedNode.content}</p>
                  </div>

                  {/* Metadata */}
                  {selectedNode.metadata && Object.keys(selectedNode.metadata).filter(k => k !== 'subject').length > 0 && (
                    <div>
                      <Label className="text-xs text-muted-foreground">Metadata</Label>
                      <div className="mt-1 space-y-1">
                        {Object.entries(selectedNode.metadata)
                          .filter(([key]) => key !== 'subject')
                          .map(([key, value]) => (
                            <div key={key} className="flex gap-2 text-xs">
                              <span className="text-muted-foreground">{key}:</span>
                              <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Connections summary */}
                  {selectedNodeEdges && (
                    <div>
                      <Label className="text-xs text-muted-foreground">Connections</Label>
                      <div className="mt-1 flex gap-4 text-sm">
                        <span>
                          <span className="text-muted-foreground">In:</span>{' '}
                          {selectedNodeEdges.edges.filter(e => e.target_id === selectedNodeId).length}
                        </span>
                        <span>
                          <span className="text-muted-foreground">Out:</span>{' '}
                          {selectedNodeEdges.edges.filter(e => e.source_id === selectedNodeId).length}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Created: {new Date(selectedNode.created_at).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">Loading...</div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Quick Stats */}
        <Card className="flex-shrink-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Graph Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Nodes</span>
                <span>{allNodesData?.total ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Edges</span>
                <span>{allEdgesData?.total ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Displayed</span>
                <span>{displayData.nodes.length} / {displayData.edges.length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading...
        </div>
      </div>
    }>
      <GraphPageContent />
    </Suspense>
  );
}
