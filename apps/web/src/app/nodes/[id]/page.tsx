'use client';

import {
  useNode,
  useNodeEdges,
  useUpdateNode,
  useDeleteNode,
  useTraverse,
  useEdges,
} from '@/hooks/useKnowledgeGraph';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Trash2,
  Edit,
  Network,
  ArrowRight,
  ArrowLeftRight,
  Save,
  X,
} from 'lucide-react';
import { useState, useMemo, useEffect } from 'react';
import { NODE_COLORS, type NodeType, type EdgeType, type Node, type Edge } from '@/types';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import * as api from '@/lib/api';

export default function NodeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const nodeId = params.id as string;

  const { data: node, isLoading } = useNode(nodeId);
  const { data: edgesData } = useNodeEdges(nodeId);
  const updateNode = useUpdateNode();
  const deleteNode = useDeleteNode();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [outgoingDepth, setOutgoingDepth] = useState(2);

  // Fetch traversal data for the mini graph
  const { data: traverseData } = useTraverse(nodeId, outgoingDepth);

  // Fetch all edges to filter for graph
  const { data: allEdgesData } = useEdges({ limit: 500 });

  // Fetch connected node details for displaying names
  const [connectedNodes, setConnectedNodes] = useState<Record<string, Node>>({});

  useEffect(() => {
    if (!edgesData?.edges) return;

    const nodeIds = new Set<string>();
    edgesData.edges.forEach((e) => {
      if (e.source_id !== nodeId) nodeIds.add(e.source_id);
      if (e.target_id !== nodeId) nodeIds.add(e.target_id);
    });

    // Fetch each node
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
  }, [edgesData, nodeId]);

  // Build graph data for mini visualization
  // Always shows 1 level incoming + N levels outgoing
  const graphData = useMemo(() => {
    if (!node) {
      return { nodes: [], edges: [] };
    }

    const graphNodes: Node[] = [];
    const nodeIds = new Set<string>();

    // Add current node
    graphNodes.push(node);
    nodeIds.add(node.uuid);

    // Add 1 level of INCOMING nodes (edges where target_id === nodeId)
    const incomingEdges = edgesData?.edges.filter((e) => e.target_id === nodeId) ?? [];
    for (const edge of incomingEdges) {
      const incomingNode = connectedNodes[edge.source_id];
      if (incomingNode && !nodeIds.has(incomingNode.uuid)) {
        graphNodes.push(incomingNode);
        nodeIds.add(incomingNode.uuid);
      }
    }

    // Add N levels of OUTGOING nodes from traversal
    if (traverseData) {
      Object.values(traverseData.levels).forEach((levelNodes) => {
        levelNodes.forEach((n) => {
          if (!nodeIds.has(n.uuid)) {
            graphNodes.push({
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
    }

    // Filter edges to only those between displayed nodes
    const graphEdges =
      allEdgesData?.edges.filter(
        (e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id)
      ) ?? [];

    return { nodes: graphNodes, edges: graphEdges };
  }, [node, traverseData, allEdgesData, edgesData, connectedNodes, nodeId]);

  const handleEdit = () => {
    if (node) {
      setEditContent(node.content);
      setEditing(true);
    }
  };

  const handleSave = async () => {
    if (!editContent.trim()) return;

    await updateNode.mutateAsync({
      id: nodeId,
      data: { content: editContent },
    });
    setEditing(false);
  };

  const handleDelete = async () => {
    await deleteNode.mutateAsync(nodeId);
    router.push('/nodes');
  };

  if (isLoading) {
    return <div className="text-muted-foreground">Loading node...</div>;
  }

  if (!node) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Node not found</h2>
        <Link href="/nodes" className="text-primary hover:underline">
          Back to nodes
        </Link>
      </div>
    );
  }

  const incomingEdges =
    edgesData?.edges.filter((e) => e.target_id === nodeId) ?? [];
  const outgoingEdges =
    edgesData?.edges.filter((e) => e.source_id === nodeId) ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div
              className="h-4 w-4 rounded-full"
              style={{
                backgroundColor:
                  NODE_COLORS[node.type as NodeType] ?? '#6b7280',
              }}
            />
            <Badge variant="outline" className="capitalize text-sm">
              {node.type}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {node.metadata?.subject || node.content.substring(0, 60)}
          </p>
        </div>
        <Button variant="outline" size="icon" onClick={handleEdit}>
          <Edit className="h-4 w-4" />
        </Button>
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive" size="icon">
              <Trash2 className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Node</DialogTitle>
              <DialogDescription>
                This will permanently delete this node and all its connected
                edges. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleteNode.isPending}
              >
                {deleteNode.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Mini Graph */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Context Graph
            </CardTitle>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs text-muted-foreground">Incoming: 1</span>
              <span className="text-muted-foreground">|</span>
              <Label className="text-sm text-muted-foreground">
                Outgoing: {outgoingDepth}
              </Label>
              <input
                type="range"
                min={1}
                max={5}
                value={outgoingDepth}
                onChange={(e) => setOutgoingDepth(parseInt(e.target.value))}
                className="w-32"
              />
              <Link href={`/explore?node=${nodeId}`}>
                <Button variant="outline" size="sm" className="gap-1">
                  <Network className="h-3 w-3" />
                  Full Graph
                </Button>
              </Link>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-[500px] rounded-lg border bg-background">
            {graphData.nodes.length > 0 ? (
              <GraphCanvas
                nodes={graphData.nodes}
                edges={graphData.edges}
                selectedNodeId={nodeId}
                showLabels={true}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                Loading graph...
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      <Card>
        <CardHeader>
          <CardTitle>Content</CardTitle>
        </CardHeader>
        <CardContent>
          {editing ? (
            <div className="space-y-4">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full min-h-[200px] p-3 rounded-md border bg-background resize-y"
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setEditing(false)}
                  className="gap-2"
                >
                  <X className="h-4 w-4" />
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={updateNode.isPending}
                  className="gap-2"
                >
                  <Save className="h-4 w-4" />
                  {updateNode.isPending ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="whitespace-pre-wrap">{node.content}</div>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      {node.metadata && Object.keys(node.metadata).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(node.metadata).map(([key, value]) => (
                <div key={key} className="flex gap-4">
                  <span className="font-medium min-w-[120px]">{key}:</span>
                  <span className="text-muted-foreground">
                    {typeof value === 'object'
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connections */}
      <Card>
        <CardHeader>
          <CardTitle>Connections</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="all">
            <TabsList>
              <TabsTrigger value="all" className="gap-2">
                <ArrowLeftRight className="h-4 w-4" />
                All ({edgesData?.total ?? 0})
              </TabsTrigger>
              <TabsTrigger value="incoming" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Incoming ({incomingEdges.length})
              </TabsTrigger>
              <TabsTrigger value="outgoing" className="gap-2">
                <ArrowRight className="h-4 w-4" />
                Outgoing ({outgoingEdges.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              <EdgeList
                edges={edgesData?.edges ?? []}
                currentNodeId={nodeId}
                connectedNodes={connectedNodes}
              />
            </TabsContent>
            <TabsContent value="incoming" className="mt-4">
              <EdgeList
                edges={incomingEdges}
                currentNodeId={nodeId}
                connectedNodes={connectedNodes}
              />
            </TabsContent>
            <TabsContent value="outgoing" className="mt-4">
              <EdgeList
                edges={outgoingEdges}
                currentNodeId={nodeId}
                connectedNodes={connectedNodes}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Timestamps */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>Created: {new Date(node.created_at).toLocaleString()}</span>
        <span>Updated: {new Date(node.updated_at).toLocaleString()}</span>
      </div>
    </div>
  );
}

function EdgeList({
  edges,
  currentNodeId,
  connectedNodes,
}: {
  edges: Array<{
    uuid: string;
    type: EdgeType;
    source_id: string;
    target_id: string;
  }>;
  currentNodeId: string;
  connectedNodes: Record<string, Node>;
}) {
  if (edges.length === 0) {
    return (
      <div className="text-muted-foreground text-center py-4">
        No connections
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {edges.map((edge) => {
        const isOutgoing = edge.source_id === currentNodeId;
        const otherNodeId = isOutgoing ? edge.target_id : edge.source_id;
        const otherNode = connectedNodes[otherNodeId];

        // Get display name from node
        const displayName = otherNode
          ? otherNode.metadata?.subject ||
            otherNode.metadata?.name ||
            otherNode.content.substring(0, 60) +
              (otherNode.content.length > 60 ? '...' : '')
          : 'Loading...';

        const nodeType = otherNode?.type as NodeType;

        return (
          <Link
            key={edge.uuid}
            href={`/nodes/${otherNodeId}`}
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent border"
          >
            {isOutgoing ? (
              <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <ArrowLeft className="h-4 w-4 text-muted-foreground shrink-0" />
            )}
            <Badge variant="secondary" className="capitalize shrink-0">
              {edge.type.replace(/_/g, ' ')}
            </Badge>
            {otherNode && (
              <div
                className="h-3 w-3 rounded-full shrink-0"
                style={{
                  backgroundColor: NODE_COLORS[nodeType] ?? '#6b7280',
                }}
              />
            )}
            {otherNode && (
              <Badge variant="outline" className="capitalize text-xs shrink-0">
                {otherNode.type}
              </Badge>
            )}
            <span className="text-sm truncate flex-1">{displayName}</span>
          </Link>
        );
      })}
    </div>
  );
}
