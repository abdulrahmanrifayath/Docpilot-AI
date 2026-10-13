import React, { useMemo, useState, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Search,
  Filter,
  Layers,
  Cpu,
  Boxes,
  Code2,
  FileCode,
  Package,
  Braces,
  ArrowRight,
  ExternalLink,
  Target,
  Sparkles,
  Info,
  Maximize2,
  RefreshCw,
  X,
  Check,
} from 'lucide-react';
import {
  DependencyGraphResponse,
  DependencyNode,
  DependencyRelationship,
  DependencyNodeType,
  DependencyRelationshipType,
} from '../types';

interface DependencyGraphViewerProps {
  graphData: DependencyGraphResponse | null;
  onRefresh?: () => void;
  isLoading?: boolean;
}

// 1. Custom Node Component
const CustomDependencyNode: React.FC<NodeProps> = ({ data, selected }) => {
  const node = data.node as DependencyNode;
  const isSearchMatch = Boolean(data.isSearchMatch);
  const isFocused = Boolean(data.isFocused);

  const getNodeColors = (type: DependencyNodeType) => {
    switch (type) {
      case 'service':
        return {
          border: 'border-purple-500/50',
          bg: 'bg-purple-950/60',
          text: 'text-purple-300',
          badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
          icon: Cpu,
        };
      case 'class':
        return {
          border: 'border-emerald-500/50',
          bg: 'bg-emerald-950/60',
          text: 'text-emerald-300',
          badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
          icon: Boxes,
        };
      case 'function':
        return {
          border: 'border-sky-500/50',
          bg: 'bg-sky-950/60',
          text: 'text-sky-300',
          badge: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
          icon: Code2,
        };
      case 'component':
        return {
          border: 'border-amber-500/50',
          bg: 'bg-amber-950/60',
          text: 'text-amber-300',
          badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          icon: Layers,
        };
      case 'interface':
        return {
          border: 'border-cyan-500/50',
          bg: 'bg-cyan-950/60',
          text: 'text-cyan-300',
          badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
          icon: Braces,
        };
      case 'external':
        return {
          border: 'border-orange-500/50',
          bg: 'bg-orange-950/60',
          text: 'text-orange-300',
          badge: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
          icon: Package,
        };
      default:
        return {
          border: 'border-slate-700',
          bg: 'bg-slate-900',
          text: 'text-slate-300',
          badge: 'bg-slate-800 text-slate-300 border-slate-700',
          icon: FileCode,
        };
    }
  };

  const colors = getNodeColors(node.node_type);
  const Icon = colors.icon;

  return (
    <div
      className={`relative min-w-[190px] max-w-[260px] p-3 rounded-xl border backdrop-blur-md transition-all shadow-lg ${
        colors.bg
      } ${colors.border} ${
        selected || isFocused
          ? 'ring-2 ring-brand-400 ring-offset-2 ring-offset-slate-950 shadow-brand-500/20 scale-[1.02]'
          : isSearchMatch
          ? 'ring-2 ring-amber-400 ring-offset-2 ring-offset-slate-950 animate-pulse'
          : 'hover:border-slate-500 hover:shadow-xl'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-brand-400" />

      {/* Top Header */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${colors.text}`} />
          <span
            className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${colors.badge}`}
          >
            {node.node_type}
          </span>
        </div>
        {node.is_external && (
          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">
            external
          </span>
        )}
      </div>

      {/* Name */}
      <div className="font-mono text-xs font-bold text-white truncate" title={node.name}>
        {node.name}
      </div>

      {/* File Path */}
      {node.file_path && (
        <div className="text-[10px] text-slate-400 truncate mt-1 font-mono" title={node.file_path}>
          {node.file_path}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-brand-400" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomDependencyNode,
};

export const DependencyGraphViewer: React.FC<DependencyGraphViewerProps> = ({
  graphData,
  onRefresh,
  isLoading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedRelFilter, setSelectedRelFilter] = useState<string>('ALL');
  const [showExternal, setShowExternal] = useState<boolean>(true);
  const [selectedNode, setSelectedNode] = useState<DependencyNode | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  // 2. Filter Graph based on controls
  const filteredData = useMemo(() => {
    let nodes = graphData?.nodes || [];
    let edges = graphData?.edges || [];

    // Filter external nodes
    if (!showExternal) {
      nodes = nodes.filter((n) => !n.is_external);
      edges = edges.filter((e) => !e.is_external);
    }

    // Filter by relationship type
    if (selectedRelFilter !== 'ALL') {
      edges = edges.filter((e) => e.relationship_type === selectedRelFilter);
    }

    // Filter by focus entity if set
    if (focusedNodeId) {
      const focusNode = nodes.find((n) => n.id === focusedNodeId || n.name === focusedNodeId);
      if (focusNode) {
        const neighborNames = new Set<string>([focusNode.name, focusNode.id]);
        const connectedEdges = edges.filter((e) => {
          if (e.source === focusNode.name || e.source === focusNode.id) {
            neighborNames.add(e.target);
            return true;
          }
          if (e.target === focusNode.name || e.target === focusNode.id) {
            neighborNames.add(e.source);
            return true;
          }
          return false;
        });

        nodes = nodes.filter((n) => neighborNames.has(n.name) || neighborNames.has(n.id));
        edges = connectedEdges;
      }
    }

    return { nodes, edges };
  }, [graphData, showExternal, selectedRelFilter, focusedNodeId]);

  // 3. Compute Automatic DAG / Layered Layout
  const { initialNodes, initialEdges } = useMemo(() => {
    const { nodes, edges } = filteredData;

    // Group nodes by tier/type for clean hierarchical positioning
    const tierGroups: Record<number, DependencyNode[]> = {
      0: [], // Services / Controllers / Endpoints
      1: [], // Classes / Components
      2: [], // Repositories / Helper Functions
      3: [], // Interfaces / Models / External
    };

    nodes.forEach((n) => {
      if (n.node_type === 'service') {
        tierGroups[0].push(n);
      } else if (n.node_type === 'class' || n.node_type === 'component') {
        tierGroups[1].push(n);
      } else if (n.node_type === 'function' || n.node_type === 'file') {
        tierGroups[2].push(n);
      } else {
        tierGroups[3].push(n);
      }
    });

    const flowNodes: any[] = [];
    const nodeXSpacing = 300;
    const nodeYSpacing = 140;

    Object.entries(tierGroups).forEach(([tierStr, tierNodes]) => {
      const tierIndex = parseInt(tierStr, 10);
      tierNodes.forEach((node, nodeIndex) => {
        const isSearchMatch =
          searchQuery.trim() !== '' &&
          node.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
        const isFocused = focusedNodeId === node.id || focusedNodeId === node.name;

        flowNodes.push({
          id: node.id || node.name,
          type: 'custom',
          position: {
            x: tierIndex * nodeXSpacing + 60,
            y: nodeIndex * nodeYSpacing + 60,
          },
          data: {
            node,
            isSearchMatch,
            isFocused,
          },
        });
      });
    });

    const flowEdges: any[] = edges.map((edge) => {
      const getEdgeColor = (type: DependencyRelationshipType) => {
        switch (type) {
          case 'EXTENDS':
            return '#10b981'; // emerald
          case 'IMPLEMENTS':
            return '#a855f7'; // purple
          case 'DEPENDS_ON':
            return '#f59e0b'; // amber
          case 'CALLS':
            return '#38bdf8'; // sky
          case 'USES':
            return '#ec4899'; // pink
          case 'IMPORTS':
          default:
            return '#64748b'; // slate
        }
      };

      const edgeColor = getEdgeColor(edge.relationship_type);
      const isAnimated = edge.relationship_type === 'CALLS' || edge.relationship_type === 'DEPENDS_ON';

      // Find node ID mapping for source and target
      const sourceNode = nodes.find((n) => n.name === edge.source || n.id === edge.source);
      const targetNode = nodes.find((n) => n.name === edge.target || n.id === edge.target);

      const sourceId = sourceNode ? sourceNode.id : edge.source;
      const targetId = targetNode ? targetNode.id : edge.target;

      return {
        id: edge.id,
        source: sourceId,
        target: targetId,
        animated: isAnimated,
        style: {
          stroke: edgeColor,
          strokeWidth: 2,
          strokeDasharray: edge.relationship_type === 'IMPLEMENTS' ? '5,5' : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edgeColor,
          width: 16,
          height: 16,
        },
        label: `${edge.relationship_type} (${Math.round(edge.confidence * 100)}%)`,
        labelStyle: {
          fill: '#cbd5e1',
          fontWeight: 600,
          fontSize: 10,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#090d16',
          fillOpacity: 0.85,
          stroke: '#334155',
          strokeWidth: 1,
        },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 6,
        data: { edge },
      };
    });

    return { initialNodes: flowNodes, initialEdges: flowEdges };
  }, [filteredData, searchQuery, focusedNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Handle clicking on a node
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: any) => {
      const depNode = node.data?.node as DependencyNode;
      if (depNode) {
        setSelectedNode(depNode);
      }
    },
    []
  );

  // Selected node details (inbound and outbound edges)
  const nodeConnections = useMemo(() => {
    if (!selectedNode) return { incoming: [], outgoing: [] };
    const allEdges = graphData?.edges || [];
    const incoming = allEdges.filter(
      (e) => e.target === selectedNode.name || e.target === selectedNode.id
    );
    const outgoing = allEdges.filter(
      (e) => e.source === selectedNode.name || e.source === selectedNode.id
    );
    return { incoming, outgoing };
  }, [selectedNode, graphData]);

  const relationshipTypes: DependencyRelationshipType[] = [
    'IMPORTS',
    'CALLS',
    'EXTENDS',
    'IMPLEMENTS',
    'DEPENDS_ON',
    'USES',
  ];

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md overflow-hidden flex flex-col space-y-0">
      {/* 1. TOP TOOLBAR & CONTROLS */}
      <div className="p-4 border-b border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-slate-950/60">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-white tracking-tight">Interactive Dependency Graph</h3>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {filteredData.nodes.length} nodes • {filteredData.edges.length} edges
            </span>
          </div>

          {/* Focused badge if active */}
          {focusedNodeId && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-300 text-xs">
              <Target className="w-3.5 h-3.5 text-brand-400" />
              <span>Focused: <strong className="text-white">{focusedNodeId}</strong></span>
              <button
                onClick={() => setFocusedNodeId(null)}
                className="ml-1 p-0.5 hover:text-white"
                title="Reset Focus"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Search Input */}
          <div className="relative w-full sm:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search entity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* External Packages Toggle */}
          <button
            onClick={() => setShowExternal(!showExternal)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
              showExternal
                ? 'bg-orange-500/10 border-orange-500/30 text-orange-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
            title="Toggle third-party libraries & external packages"
          >
            <Package className="w-3.5 h-3.5" />
            <span>External: {showExternal ? 'ON' : 'OFF'}</span>
          </button>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all disabled:opacity-50"
              title="Re-analyze and reload dependency graph"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* 2. FILTER PILLS BAR */}
      <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-950/40 flex items-center gap-1.5 overflow-x-auto text-xs">
        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mr-1">
          Relationship:
        </span>
        <button
          onClick={() => setSelectedRelFilter('ALL')}
          className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold transition-all ${
            selectedRelFilter === 'ALL'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'bg-slate-800/70 text-slate-400 hover:text-white'
          }`}
        >
          All
        </button>
        {relationshipTypes.map((type) => (
          <button
            key={type}
            onClick={() => setSelectedRelFilter(type)}
            className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold transition-all ${
              selectedRelFilter === type
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-slate-800/70 text-slate-400 hover:text-white'
            }`}
          >
            {type}
          </button>
        ))}
      </div>

      {/* 3. MAIN CANVAS & SIDE DRAWER */}
      <div className="relative w-full h-[580px] bg-slate-950">
        {isLoading && (
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm z-30 flex flex-col items-center justify-center text-slate-300">
            <RefreshCw className="w-8 h-8 animate-spin text-brand-500 mb-3" />
            <span className="text-xs font-semibold">Analyzing dependencies and building topology...</span>
          </div>
        )}

        {!isLoading && (!graphData || filteredData.nodes.length === 0) ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-center p-6">
            <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-3">
              <Layers className="w-7 h-7" />
            </div>
            <h4 className="text-sm font-bold text-white mb-1">No Dependencies Available</h4>
            <p className="text-xs text-slate-400 max-w-sm mb-4">
              {searchQuery || selectedRelFilter !== 'ALL'
                ? 'No matching nodes or edges found for the active filter.'
                : 'Click "Analyze Dependencies" to detect imports, class inheritance, function calls, and service connections.'}
            </p>
            {onRefresh && !searchQuery && selectedRelFilter === 'ALL' && (
              <button
                onClick={onRefresh}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Analyze Dependencies</span>
              </button>
            )}
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={2.0}
          >
            <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#334155" />
            <Controls className="!bg-slate-900 !border-slate-800 !rounded-xl !shadow-lg [&>button]:!bg-slate-900 [&>button]:!border-slate-800 [&>button]:!text-slate-300" />
            <MiniMap
              className="!bg-slate-900/90 !border-slate-800 !rounded-xl !shadow-lg"
              nodeColor={(n: any) => {
                const nodeType = n.data?.node?.node_type;
                if (nodeType === 'service') return '#a855f7';
                if (nodeType === 'class') return '#10b981';
                if (nodeType === 'function') return '#38bdf8';
                if (nodeType === 'component') return '#f59e0b';
                if (nodeType === 'external') return '#f97316';
                return '#64748b';
              }}
            />
          </ReactFlow>
        )}

        {/* 4. NODE SELECTION INSPECTOR DRAWER */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-80 max-h-[530px] rounded-2xl bg-slate-900/95 border border-slate-800 shadow-2xl backdrop-blur-md p-4 overflow-y-auto space-y-4 z-10">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-brand-400" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Entity Inspector
                </h4>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Entity Header */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  {selectedNode.node_type}
                </span>
                {selectedNode.is_external && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30">
                    external
                  </span>
                )}
              </div>
              <h3 className="text-sm font-bold text-white font-mono break-all">{selectedNode.name}</h3>
              {selectedNode.file_path && (
                <p className="text-[11px] text-slate-400 font-mono break-all mt-0.5">
                  {selectedNode.file_path}
                </p>
              )}
            </div>

            {/* Focus Action Button */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setFocusedNodeId(selectedNode.id || selectedNode.name);
                }}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
              >
                <Target className="w-3.5 h-3.5" />
                <span>Focus Subgraph</span>
              </button>
            </div>

            {/* Incoming Connections */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                Incoming Dependencies ({nodeConnections.incoming.length})
              </span>
              {nodeConnections.incoming.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">No incoming callers or importers.</p>
              ) : (
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {nodeConnections.incoming.map((e) => (
                    <div
                      key={e.id}
                      className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between"
                    >
                      <span className="font-mono text-white truncate max-w-[140px]">{e.source}</span>
                      <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                        {e.relationship_type} ({Math.round(e.confidence * 100)}%)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Outgoing Connections */}
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                Outgoing Dependencies ({nodeConnections.outgoing.length})
              </span>
              {nodeConnections.outgoing.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">No outgoing dependencies detected.</p>
              ) : (
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {nodeConnections.outgoing.map((e) => (
                    <div
                      key={e.id}
                      className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between"
                    >
                      <span className="font-mono text-white truncate max-w-[140px]">{e.target}</span>
                      <span className="text-[10px] font-semibold text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/20">
                        {e.relationship_type} ({Math.round(e.confidence * 100)}%)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Static Analysis Detection Metadata */}
            <div className="pt-2 border-t border-slate-800 text-[10px] text-slate-500 space-y-1">
              <p>
                <strong>Inference:</strong> Static AST and syntax parser analysis detected relationships.
              </p>
              {selectedNode.metadata?.description && (
                <p className="italic text-slate-400">&ldquo;{selectedNode.metadata.description}&rdquo;</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
