'use client';

import { useSearch } from '@/hooks/useKnowledgeGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Search, X } from 'lucide-react';
import { useState } from 'react';
import { NODE_COLORS, type NodeType } from '@/types';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [limit, setLimit] = useState(20);

  const { data, isLoading, error } = useSearch(searchTerm, limit);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchTerm(query);
  };

  const clearSearch = () => {
    setQuery('');
    setSearchTerm('');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Search</h1>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the knowledge graph..."
            className="pl-9 pr-9"
          />
          {query && (
            <button
              type="button"
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Button type="submit" disabled={!query.trim()}>
          Search
        </Button>
      </form>

      {/* Results */}
      {searchTerm && (
        <>
          {isLoading ? (
            <div className="text-muted-foreground">Searching...</div>
          ) : error ? (
            <div className="text-destructive">
              Error: {(error as Error).message}
            </div>
          ) : (
            <>
              <div className="text-sm text-muted-foreground">
                Found {data?.total ?? 0} results for &quot;{searchTerm}&quot;
              </div>

              <div className="space-y-4">
                {data?.results.map((result, index) => (
                  <Card key={index}>
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center justify-between text-base">
                        <div className="flex items-center gap-2">
                          <div
                            className="h-3 w-3 rounded-full"
                            style={{
                              backgroundColor:
                                NODE_COLORS[result.type as NodeType] ??
                                '#6b7280',
                            }}
                          />
                          <Badge variant="outline" className="capitalize">
                            {result.type}
                          </Badge>
                        </div>
                        <Badge variant="secondary">
                          Score: {(result.score * 100).toFixed(1)}%
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">{result.content}</p>
                      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                        {result.source_file && (
                          <span>Source: {result.source_file}</span>
                        )}
                        {result.captured_at && (
                          <span>
                            Captured:{' '}
                            {new Date(result.captured_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {data?.results.length === 0 && (
                  <div className="text-center py-12">
                    <Search className="mx-auto h-12 w-12 text-muted-foreground" />
                    <h3 className="mt-4 text-lg font-medium">No results found</h3>
                    <p className="mt-2 text-muted-foreground">
                      Try a different search term
                    </p>
                  </div>
                )}

                {data && data.results.length > 0 && data.results.length >= limit && (
                  <div className="flex justify-center">
                    <Button
                      variant="outline"
                      onClick={() => setLimit(limit + 20)}
                    >
                      Load More
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}

      {!searchTerm && (
        <div className="text-center py-12">
          <Search className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-medium">Search the Knowledge Graph</h3>
          <p className="mt-2 text-muted-foreground">
            Enter a search term to find nodes, decisions, tasks, and more
          </p>
        </div>
      )}
    </div>
  );
}
