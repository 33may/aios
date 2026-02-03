'use client';

import { useNodes } from '@/hooks/useKnowledgeGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import Link from 'next/link';
import { Box } from 'lucide-react';
import { useState } from 'react';
import { NODE_COLORS, NODE_TYPES, type NodeType } from '@/types';

export default function NodesPage() {
  const [typeFilter, setTypeFilter] = useState<NodeType | 'all'>('all');
  const [limit, setLimit] = useState(50);

  const { data, isLoading } = useNodes({
    type: typeFilter === 'all' ? undefined : typeFilter,
    limit,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Nodes</h1>
        <div className="flex items-center gap-4">
          <Select
            value={typeFilter}
            onValueChange={(v) => setTypeFilter(v as NodeType | 'all')}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {NODE_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: NODE_COLORS[type] }}
                    />
                    <span className="capitalize">{type}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={limit.toString()}
            onValueChange={(v) => setLimit(parseInt(v))}
          >
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="25">25</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
              <SelectItem value="200">200</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading nodes...</div>
      ) : (
        <>
          <div className="text-sm text-muted-foreground">
            Showing {data?.nodes.length ?? 0} of {data?.total ?? 0} nodes
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data?.nodes.map((node) => (
              <Link key={node.uuid} href={`/nodes/${node.uuid}`}>
                <Card className="h-full transition-colors hover:bg-accent cursor-pointer">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <div
                        className="h-3 w-3 rounded-full shrink-0"
                        style={{
                          backgroundColor:
                            NODE_COLORS[node.type as NodeType] ?? '#6b7280',
                        }}
                      />
                      <Badge variant="outline" className="capitalize">
                        {node.type}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm line-clamp-3">{node.content}</p>
                    <p className="mt-4 text-xs text-muted-foreground">
                      {new Date(node.created_at).toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
            {(!data?.nodes || data.nodes.length === 0) && (
              <div className="col-span-full text-center py-12">
                <Box className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No nodes found</h3>
                <p className="mt-2 text-muted-foreground">
                  {typeFilter !== 'all'
                    ? `No ${typeFilter} nodes yet`
                    : 'Create your first node to get started'}
                </p>
              </div>
            )}
          </div>

          {data && data.nodes.length < data.total && (
            <div className="flex justify-center">
              <Button
                variant="outline"
                onClick={() => setLimit(limit + 50)}
              >
                Load More
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
