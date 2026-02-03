'use client';

import { useProjects, useCreateProject } from '@/hooks/useKnowledgeGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import Link from 'next/link';
import { Plus, FolderKanban } from 'lucide-react';
import { useState } from 'react';

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  const handleCreate = async () => {
    if (!newProject.name.trim()) return;

    await createProject.mutateAsync({
      name: newProject.name,
      description: newProject.description || undefined,
    });

    setNewProject({ name: '', description: '' });
    setDialogOpen(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject({ ...newProject, name: e.target.value })
                  }
                  placeholder="My Project"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Input
                  id="description"
                  value={newProject.description}
                  onChange={(e) =>
                    setNewProject({ ...newProject, description: e.target.value })
                  }
                  placeholder="Project description..."
                />
              </div>
              <Button
                onClick={handleCreate}
                disabled={!newProject.name.trim() || createProject.isPending}
                className="w-full"
              >
                {createProject.isPending ? 'Creating...' : 'Create Project'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading projects...</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects?.map((project) => (
            <Link key={project.uuid} href={`/projects/${project.uuid}`}>
              <Card className="h-full transition-colors hover:bg-accent cursor-pointer">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FolderKanban className="h-5 w-5 text-primary" />
                    {project.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {project.description && (
                    <p className="text-sm text-muted-foreground mb-4">
                      {project.description}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {project.task_count} tasks
                    </Badge>
                    <Badge variant="secondary">
                      {project.decision_count} decisions
                    </Badge>
                    <Badge variant="secondary">
                      {project.discovery_count} discoveries
                    </Badge>
                  </div>
                  <p className="mt-4 text-xs text-muted-foreground">
                    Created: {new Date(project.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
          {(!projects || projects.length === 0) && (
            <div className="col-span-full text-center py-12">
              <FolderKanban className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No projects yet</h3>
              <p className="mt-2 text-muted-foreground">
                Create your first project to get started
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
