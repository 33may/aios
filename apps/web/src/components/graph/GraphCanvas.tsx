'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { Network, Options, Node as VisNode, Edge as VisEdge } from 'vis-network';
import { DataSet } from 'vis-data';
import { useRouter } from 'next/navigation';
import { NODE_COLORS, NODE_SHAPES, TASK_STATUS_COLORS, type NodeType, type Node, type Edge } from '@/types';

interface GraphCanvasProps {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
  onNodeDoubleClick?: (nodeId: string) => void;
  showLabels?: boolean;
}

const networkOptions: Options = {
  nodes: {
    font: {
      size: 14,
      color: '#ffffff',
    },
    borderWidth: 2,
    shadow: true,
    margin: 10,
  },
  edges: {
    arrows: {
      to: { enabled: true, scaleFactor: 0.8 },
    },
    color: {
      color: '#6b7280',
      highlight: '#3b82f6',
      hover: '#6366f1',
    },
    width: 1.5,
    smooth: {
      enabled: true,
      type: 'cubicBezier',
      forceDirection: 'horizontal',
      roundness: 0.4,
    },
  },
  physics: {
    enabled: true,
    solver: 'hierarchicalRepulsion',
    hierarchicalRepulsion: {
      centralGravity: 0.0,
      springLength: 250,
      springConstant: 0.01,
      nodeDistance: 250,
      damping: 0.09,
    },
    stabilization: {
      enabled: true,
      iterations: 300,
      fit: true,
    },
  },
  interaction: {
    hover: true,
    tooltipDelay: 200,
    zoomView: true,
    dragView: true,
    multiselect: true,
  },
  layout: {
    hierarchical: {
      enabled: true,
      direction: 'LR', // Left-to-Right (better for wide labels)
      sortMethod: 'directed',
      levelSeparation: 300,
      nodeSpacing: 150,
      treeSpacing: 200,
      blockShifting: true,
      edgeMinimization: true,
      parentCentralization: true,
    },
  },
};

function getNodeColor(type: NodeType, status?: string): string {
  // For tasks, use status-based colors
  if (type === 'task' && status) {
    return TASK_STATUS_COLORS[status] ?? NODE_COLORS[type] ?? '#6b7280';
  }
  return NODE_COLORS[type] ?? '#6b7280';
}

function getNodeGroup(type: NodeType, status?: string): object {
  const color = getNodeColor(type, status);
  return {
    color: {
      background: color,
      border: color,
      highlight: {
        background: color,
        border: '#ffffff',
      },
      hover: {
        background: color,
        border: '#ffffff',
      },
    },
    shape: NODE_SHAPES[type] ?? 'ellipse',
  };
}

export function GraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  onNodeSelect,
  onNodeDoubleClick,
  showLabels = true,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const router = useRouter();
  const [isStabilizing, setIsStabilizing] = useState(true);

  // Convert nodes to vis-network format
  const visNodes = useCallback(() => {
    return new DataSet<VisNode>(
      nodes.map((node) => {
        const displayText = node.metadata?.subject || node.content;
        const status = node.metadata?.status as string | undefined;
        return {
          id: node.uuid,
          label: showLabels
            ? displayText.substring(0, 100) + (displayText.length > 100 ? '...' : '')
            : node.type,
          title: `${node.type}${status ? ` (${status})` : ''}: ${node.content}`,
          ...getNodeGroup(node.type as NodeType, status),
        };
      })
    );
  }, [nodes, showLabels]);

  // Convert edges to vis-network format
  const visEdges = useCallback(() => {
    return new DataSet<VisEdge>(
      edges.map((edge) => ({
        id: edge.uuid,
        from: edge.source_id,
        to: edge.target_id,
        label: edge.type.replace(/_/g, ' '),
        title: edge.type,
        font: { size: 10, color: '#9ca3af' },
      }))
    );
  }, [edges]);

  // Initialize network - use refs for callbacks to keep network stable
  const onNodeSelectRef = useRef(onNodeSelect);
  const onNodeDoubleClickRef = useRef(onNodeDoubleClick);
  onNodeSelectRef.current = onNodeSelect;
  onNodeDoubleClickRef.current = onNodeDoubleClick;

  useEffect(() => {
    if (!containerRef.current) return;

    const network = new Network(
      containerRef.current,
      { nodes: visNodes(), edges: visEdges() },
      networkOptions
    );

    networkRef.current = network;

    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        onNodeSelectRef.current?.(nodeId);
      } else {
        onNodeSelectRef.current?.(null);
      }
    });

    network.on('doubleClick', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        if (onNodeDoubleClickRef.current) {
          onNodeDoubleClickRef.current(nodeId);
        } else {
          router.push(`/nodes/${nodeId}`);
        }
      }
    });

    network.on('stabilizationProgress', () => {
      setIsStabilizing(true);
    });

    network.on('stabilizationIterationsDone', () => {
      setIsStabilizing(false);
      network.fit();
    });

    network.on('dragStart', () => {
      network.setOptions({ physics: { enabled: false } });
    });

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [visNodes, visEdges, router]);

  // Update selection
  useEffect(() => {
    if (!networkRef.current || !selectedNodeId) return;

    try {
      networkRef.current.selectNodes([selectedNodeId]);
      networkRef.current.focus(selectedNodeId, {
        scale: 1.2,
        animation: { duration: 500, easingFunction: 'easeInOutQuad' },
      });
    } catch {
      // Node might not exist
    }
  }, [selectedNodeId]);

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale * 1.3 });
    }
  };

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale / 1.3 });
    }
  };

  const handleFit = () => {
    if (networkRef.current) {
      networkRef.current.fit();
    }
  };

  return (
    <div className="relative h-full w-full">
      {isStabilizing && (
        <div className="absolute top-4 left-4 z-10 flex items-center gap-2 rounded-lg bg-background/80 px-3 py-2 text-sm">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Stabilizing graph...
        </div>
      )}

      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <button
          onClick={handleZoomIn}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-background/80 hover:bg-background text-lg font-bold"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-background/80 hover:bg-background text-lg font-bold"
          title="Zoom out"
        >
          -
        </button>
        <button
          onClick={handleFit}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-background/80 hover:bg-background text-sm"
          title="Fit to view"
        >
          ⊙
        </button>
      </div>

      <div ref={containerRef} className="h-full w-full" />

      <div className="absolute bottom-4 left-4 z-10 flex flex-wrap gap-2 rounded-lg bg-background/80 p-3">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
