'use client';

import { useProject, useProjectTree, useDeleteProject } from '@/hooks/useKnowledgeGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from '@/components/ui/dialog';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  FolderKanban,
  ArrowLeft,
  Trash2,
  ChevronRight,
  ChevronDown,
  Network,
} from 'lucide-react';
import { useState } from 'react';
import { NODE_COLORS, type TreeNode, type NodeType } from '@/types';

function TreeNodeItem({
  node,
  depth = 0,
}: {
  node: TreeNode;
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <Link
        href={`/nodes/${node.uuid}`}
        className="flex items-center gap-2 rounded-lg p-2 transition-colors hover:bg-accent"
        style={{ paddingLeft: `${depth * 24 + 8}px` }}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.preventDefault();
              setExpanded(!expanded);
            }}
            className="p-1 hover:bg-accent-foreground/10 rounded"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <div className="w-6" />
        )}
        <div
          className="h-3 w-3 rounded-full shrink-0"
          style={{
            backgroundColor: NODE_COLORS[node.type as NodeType] ?? '#6b7280',
          }}
        />
        <Badge variant="outline" className="text-xs capitalize shrink-0">
          {node.type}
        </Badge>
        <span className="truncate text-sm">{node.content}</span>
        {node.status && (
          <Badge variant="secondary" className="ml-auto text-xs">
            {node.status}
          </Badge>
        )}
      </Link>
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

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: treeData, isLoading: treeLoading } = useProjectTree(projectId);
  const deleteProject = useDeleteProject();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleDelete = async (cascade: boolean) => {
    await deleteProject.mutateAsync({ id: projectId, cascade });
    router.push('/projects');
  };

  if (projectLoading) {
    return <div className="text-muted-foreground">Loading project...</div>;
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Project not found</h2>
        <Link href="/projects" className="text-primary hover:underline">
          Back to projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FolderKanban className="h-6 w-6 text-primary" />
            {project.name}
          </h1>
          {project.description && (
            <p className="text-muted-foreground mt-1">{project.description}</p>
          )}
        </div>
        <Link href={`/explore?node=${projectId}`}>
          <Button variant="outline" className="gap-2">
            <Network className="h-4 w-4" />
            Explore
          </Button>
        </Link>
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive" size="icon">
              <Trash2 className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Project</DialogTitle>
              <DialogDescription>
                This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <p>How would you like to delete this project?</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleDelete(false)}
                  disabled={deleteProject.isPending}
                  className="flex-1"
                >
                  Project Only
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => handleDelete(true)}
                  disabled={deleteProject.isPending}
                  className="flex-1"
                >
                  Project + All Children
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.task_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.decision_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Discoveries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{project.discovery_count}</div>
          </CardContent>
        </Card>
      </div>

      {/* Task Tree */}
      <Card>
        <CardHeader>
          <CardTitle>Task Tree</CardTitle>
        </CardHeader>
        <CardContent>
          {treeLoading ? (
            <div className="text-muted-foreground">Loading tree...</div>
          ) : treeData?.tree && treeData.tree.length > 0 ? (
            <div className="space-y-1">
              {treeData.tree.map((node) => (
                <TreeNodeItem key={node.uuid} node={node} />
              ))}
            </div>
          ) : (
            <div className="text-muted-foreground text-center py-8">
              No items in this project yet
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
