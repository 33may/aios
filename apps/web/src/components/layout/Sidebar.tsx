'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Network,
  FolderKanban,
  Search,
  LayoutDashboard,
  Box,
  ChevronLeft,
  ChevronRight,
  Compass,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/lib/store';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/explore', label: 'Explore', icon: Compass },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/projects', label: 'Projects', icon: FolderKanban },
  { href: '/nodes', label: 'Nodes', icon: Box },
  { href: '/search', label: 'Search', icon: Search },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        {sidebarOpen && (
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <Network className="h-5 w-5 text-primary" />
            <span>Knowledge Graph</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className={cn(!sidebarOpen && 'mx-auto')}
        >
          {sidebarOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                !sidebarOpen && 'justify-center px-2'
              )}
              title={!sidebarOpen ? item.label : undefined}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
