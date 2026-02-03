'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { NODE_COLORS, type TreeNode, type NodeType } from '@/types';
import { cn } from '@/lib/utils';

interface TaskTreeProps {
  nodes: TreeNode[];
  className?: string;
}

export function TaskTree({ nodes, className }: TaskTreeProps) {
  if (nodes.length === 0) {
    return (
      <div className="text-muted-foreground text-center py-8">
        No items to display
      </div>
    );
  }

  return (
    <div className={cn('space-y-1', className)}>
      {nodes.map((node) => (
        <TreeNodeItem key={node.uuid} node={node} depth={0} />
      ))}
    </div>
  );
}

interface TreeNodeItemProps {
  node: TreeNode;
  depth: number;
}

function TreeNodeItem({ node, depth }: TreeNodeItemProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <div
        className="flex items-center gap-2 rounded-lg py-1.5 px-2 transition-colors hover:bg-accent group"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {/* Expand/Collapse button */}
        {hasChildren ? (
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-0.5 hover:bg-accent-foreground/10 rounded shrink-0"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <div className="w-5" />
        )}

        {/* Node color indicator */}
        <div
          className="h-2.5 w-2.5 rounded-full shrink-0"
          style={{
            backgroundColor: NODE_COLORS[node.type as NodeType] ?? '#6b7280',
          }}
        />

        {/* Type badge */}
        <Badge variant="outline" className="text-xs capitalize shrink-0">
          {node.type}
        </Badge>

        {/* Content link */}
        <Link
          href={`/nodes/${node.uuid}`}
          className="flex-1 truncate text-sm hover:underline"
        >
          {node.content}
        </Link>

        {/* Status badge */}
        {node.status && (
          <Badge
            variant={getStatusVariant(node.status)}
            className="text-xs shrink-0"
          >
            {node.status}
          </Badge>
        )}
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <TreeNodeItem key={child.uuid} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function getStatusVariant(
  status: string
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'done':
      return 'default';
    case 'in_progress':
    case 'active':
      return 'secondary';
    case 'blocked':
    case 'failed':
      return 'destructive';
    default:
      return 'outline';
  }
}
