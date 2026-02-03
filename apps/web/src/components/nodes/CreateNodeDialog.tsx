'use client';

import { useState } from 'react';
import { useCreateNode } from '@/hooks/useKnowledgeGraph';
import { useUIStore } from '@/lib/store';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { NODE_TYPES, NODE_COLORS, type NodeType } from '@/types';

export function CreateNodeDialog() {
  const { createNodeDialogOpen, setCreateNodeDialogOpen } = useUIStore();
  const createNode = useCreateNode();

  const [type, setType] = useState<NodeType>('task');
  const [content, setContent] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!content.trim()) {
      setError('Content is required');
      return;
    }

    try {
      await createNode.mutateAsync({
        type,
        content: content.trim(),
      });

      // Reset form
      setType('task');
      setContent('');
      setError(null);
      setCreateNodeDialogOpen(false);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleClose = () => {
    setType('task');
    setContent('');
    setError(null);
    setCreateNodeDialogOpen(false);
  };

  return (
    <Dialog open={createNodeDialogOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create New Node</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-4">
          {/* Type Selection */}
          <div className="space-y-2">
            <Label>Type</Label>
            <Select value={type} onValueChange={(v) => setType(v as NodeType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {NODE_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[t] }}
                      />
                      <span className="capitalize">{t}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Content */}
          <div className="space-y-2">
            <Label>Content</Label>
            <textarea
              value={content}
              onChange={(e) => {
                setContent(e.target.value);
                setError(null);
              }}
              placeholder={getPlaceholder(type)}
              className="w-full min-h-[120px] p-3 rounded-md border bg-background resize-y"
            />
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
              disabled={!content.trim() || createNode.isPending}
            >
              {createNode.isPending ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function getPlaceholder(type: NodeType): string {
  switch (type) {
    case 'project':
      return 'Project name and description...';
    case 'task':
      return 'What needs to be done...';
    case 'decision':
      return 'Decision and rationale...';
    case 'discovery':
      return 'What was learned or discovered...';
    case 'thought':
      return 'Observation or reasoning step...';
    case 'problem':
      return 'Description of the issue...';
    case 'fix':
      return 'Solution or fix applied...';
    case 'constraint':
      return 'Requirement or preference...';
    case 'idea':
      return 'Idea or suggestion...';
    case 'note':
      return 'General note...';
    case 'session':
      return 'Session description...';
    case 'resource':
      return 'Resource URL or reference...';
    default:
      return 'Content...';
  }
}
