'use client';

import { useHealth } from '@/hooks/useKnowledgeGraph';
import { Badge } from '@/components/ui/badge';
import { Circle, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/lib/store';
import { cn } from '@/lib/utils';

export function Header() {
  const { data: health, isLoading } = useHealth();
  const { setCreateNodeDialogOpen } = useUIStore();

  const isConnected = health?.status === 'healthy';

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-4">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold">AIOS Knowledge Graph</h1>
      </div>

      <div className="flex items-center gap-4">
        <Button
          size="sm"
          onClick={() => setCreateNodeDialogOpen(true)}
          className="gap-2"
        >
          <Plus className="h-4 w-4" />
          New Node
        </Button>

        <Badge
          variant={isConnected ? 'default' : 'destructive'}
          className="gap-1.5"
        >
          <Circle
            className={cn(
              'h-2 w-2 fill-current',
              isLoading && 'animate-pulse'
            )}
          />
          {isLoading ? 'Connecting...' : isConnected ? 'Connected' : 'Disconnected'}
        </Badge>
      </div>
    </header>
  );
}
