'use client';

import { useState } from 'react';
import { useCreateEdge, useNodes } from '@/hooks/useKnowledgeGraph';
import { useUIStore } from '@/lib/store';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { EDGE_TYPES, NODE_COLORS, type EdgeType, type NodeType } from '@/types';

export function CreateEdgeDialog() {
  const { createEdgeDialogOpen, setCreateEdgeDialogOpen, selectedNodeId } = useUIStore();
  const createEdge = useCreateEdge();
  const { data: nodesData } = useNodes({ limit: 200 });

  const [type, setType] = useState<EdgeType>('related_to');
  const [sourceId, setSourceId] = useState(selectedNodeId ?? '');
  const [targetId, setTargetId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [searchSource, setSearchSource] = useState('');
  const [searchTarget, setSearchTarget] = useState('');

  // Filter nodes for search
  const filteredSourceNodes = nodesData?.nodes.filter(
    (n) =>
      n.uuid !== targetId &&
      (searchSource === '' ||
        n.content.toLowerCase().includes(searchSource.toLowerCase()) ||
        n.type.toLowerCase().includes(searchSource.toLowerCase()))
  );

  const filteredTargetNodes = nodesData?.nodes.filter(
    (n) =>
      n.uuid !== sourceId &&
      (searchTarget === '' ||
        n.content.toLowerCase().includes(searchTarget.toLowerCase()) ||
        n.type.toLowerCase().includes(searchTarget.toLowerCase()))
  );

  const handleCreate = async () => {
    if (!sourceId) {
      setError('Source node is required');
      return;
    }
    if (!targetId) {
      setError('Target node is required');
      return;
    }

    try {
      await createEdge.mutateAsync({
        type,
        source_id: sourceId,
        target_id: targetId,
      });

      // Reset form
      setType('related_to');
      setSourceId('');
      setTargetId('');
      setSearchSource('');
      setSearchTarget('');
      setError(null);
      setCreateEdgeDialogOpen(false);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleClose = () => {
    setType('related_to');
    setSourceId('');
    setTargetId('');
    setSearchSource('');
    setSearchTarget('');
    setError(null);
    setCreateEdgeDialogOpen(false);
  };

  // Update source when selected node changes
  if (selectedNodeId && sourceId !== selectedNodeId && createEdgeDialogOpen) {
    setSourceId(selectedNodeId);
  }

  return (
    <Dialog open={createEdgeDialogOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Edge</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-4">
          {/* Edge Type */}
          <div className="space-y-2">
            <Label>Edge Type</Label>
            <Select value={type} onValueChange={(v) => setType(v as EdgeType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EDGE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    <span className="capitalize">{t.replace(/_/g, ' ')}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Source Node */}
          <div className="space-y-2">
            <Label>Source Node</Label>
            <Input
              value={searchSource}
              onChange={(e) => setSearchSource(e.target.value)}
              placeholder="Search nodes..."
              className="mb-2"
            />
            <Select value={sourceId} onValueChange={setSourceId}>
              <SelectTrigger>
                <SelectValue placeholder="Select source node" />
              </SelectTrigger>
              <SelectContent className="max-h-60">
                {filteredSourceNodes?.slice(0, 50).map((node) => (
                  <SelectItem key={node.uuid} value={node.uuid}>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{
                          backgroundColor:
                            NODE_COLORS[node.type as NodeType] ?? '#6b7280',
                        }}
                      />
                      <span className="truncate max-w-[300px]">
                        [{node.type}] {node.content.substring(0, 40)}...
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Target Node */}
          <div className="space-y-2">
            <Label>Target Node</Label>
            <Input
              value={searchTarget}
              onChange={(e) => setSearchTarget(e.target.value)}
              placeholder="Search nodes..."
              className="mb-2"
            />
            <Select value={targetId} onValueChange={setTargetId}>
              <SelectTrigger>
                <SelectValue placeholder="Select target node" />
              </SelectTrigger>
              <SelectContent className="max-h-60">
                {filteredTargetNodes?.slice(0, 50).map((node) => (
                  <SelectItem key={node.uuid} value={node.uuid}>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{
                          backgroundColor:
                            NODE_COLORS[node.type as NodeType] ?? '#6b7280',
                        }}
                      />
                      <span className="truncate max-w-[300px]">
                        [{node.type}] {node.content.substring(0, 40)}...
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-destructive">{error}</div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!sourceId || !targetId || createEdge.isPending}
            >
              {createEdge.isPending ? 'Creating...' : 'Create Edge'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
