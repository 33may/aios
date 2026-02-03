'use client';

import { useStats, useNodes, useProjects } from '@/hooks/useKnowledgeGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NODE_COLORS, type NodeType } from '@/types';
import Link from 'next/link';
import {
  Network,
  GitBranch,
  FolderKanban,
  Box,
  Activity,
  Clock,
} from 'lucide-react';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: recentNodes, isLoading: nodesLoading } = useNodes({ limit: 10 });
  const { data: projects, isLoading: projectsLoading } = useProjects();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
            <Box className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '...' : stats?.total_nodes ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Edges</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '...' : stats?.total_edges ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Projects</CardTitle>
            <FolderKanban className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {projectsLoading ? '...' : projects?.length ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Node Types</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading
                ? '...'
                : Object.keys(stats?.nodes_by_type ?? {}).length}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Nodes by Type */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Nodes by Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="text-muted-foreground">Loading...</div>
            ) : (
              <div className="space-y-3">
                {Object.entries(stats?.nodes_by_type ?? {}).map(
                  ([type, count]) => (
                    <div
                      key={type}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{
                            backgroundColor:
                              NODE_COLORS[type as NodeType] ?? '#6b7280',
                          }}
                        />
                        <span className="capitalize">{type}</span>
                      </div>
                      <Badge variant="secondary">{count}</Badge>
                    </div>
                  )
                )}
                {Object.keys(stats?.nodes_by_type ?? {}).length === 0 && (
                  <div className="text-muted-foreground">No nodes yet</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Nodes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {nodesLoading ? (
              <div className="text-muted-foreground">Loading...</div>
            ) : (
              <div className="space-y-3">
                {recentNodes?.nodes.slice(0, 5).map((node) => (
                  <Link
                    key={node.uuid}
                    href={`/nodes/${node.uuid}`}
                    className="flex items-start gap-3 rounded-lg p-2 transition-colors hover:bg-accent"
                  >
                    <div
                      className="mt-1 h-2 w-2 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          NODE_COLORS[node.type as NodeType] ?? '#6b7280',
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs capitalize">
                          {node.type}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground truncate">
                        {node.content}
                      </p>
                    </div>
                  </Link>
                ))}
                {(!recentNodes?.nodes || recentNodes.nodes.length === 0) && (
                  <div className="text-muted-foreground">No nodes yet</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Projects List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FolderKanban className="h-5 w-5" />
            Projects
          </CardTitle>
          <Link
            href="/projects"
            className="text-sm text-primary hover:underline"
          >
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {projectsLoading ? (
            <div className="text-muted-foreground">Loading...</div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects?.slice(0, 6).map((project) => (
                <Link
                  key={project.uuid}
                  href={`/projects/${project.uuid}`}
                  className="rounded-lg border p-4 transition-colors hover:bg-accent"
                >
                  <h3 className="font-medium">{project.name}</h3>
                  {project.description && (
                    <p className="mt-1 text-sm text-muted-foreground truncate">
                      {project.description}
                    </p>
                  )}
                  <div className="mt-3 flex gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {project.task_count} tasks
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {project.decision_count} decisions
                    </Badge>
                  </div>
                </Link>
              ))}
              {(!projects || projects.length === 0) && (
                <div className="col-span-full text-muted-foreground">
                  No projects yet
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
