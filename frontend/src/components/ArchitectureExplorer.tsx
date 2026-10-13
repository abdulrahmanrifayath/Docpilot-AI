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
  Network,
  Layers,
  Database,
  Server,
  Globe,
  FileCode,
  Folder,
  Boxes,
  Code2,
  Cpu,
  Braces,
  Search,
  Filter,
  Target,
  Sparkles,
  RefreshCw,
  Loader2,
  ChevronRight,
  ArrowRight,
  ExternalLink,
  Shield,
  Activity,
  Check,
  X,
  Maximize2,
  Zap,
  Info,
  GitFork,
  ArrowDownRight,
  Compass,
} from 'lucide-react';
import {
  KnowledgeGraphResponse,
  KnowledgeNode,
  KnowledgeEdge,
  KnowledgeNodeType,
  KnowledgeEntityDetailResponse,
} from '../types';
import {
  fetchKnowledgeGraph,
  buildKnowledgeGraph,
  fetchKnowledgeEntityDetail,
} from '../api/client';

interface ArchitectureExplorerProps {
  projectId: string;
  projectName?: string;
}

// 1. Color and Icon mappings for node types
const getNodeVisuals = (nodeType: KnowledgeNodeType) => {
  switch (nodeType.toLowerCase()) {
    case 'api':
      return {
        border: 'border-cyan-500/60',
        bg: 'bg-cyan-950/70',
        glow: 'shadow-cyan-500/20',
        text: 'text-cyan-300',
        badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
        badgeLabel: 'API Route',
        icon: Globe,
        colorHex: '#06b6d4',
      };
    case 'database':
      return {
        border: 'border-rose-500/60',
        bg: 'bg-rose-950/70',
        glow: 'shadow-rose-500/20',
        text: 'text-rose-300',
        badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        badgeLabel: 'DB Model',
        icon: Database,
        colorHex: '#f43f5e',
      };
    case 'service':
      return {
        border: 'border-purple-500/60',
        bg: 'bg-purple-950/70',
        glow: 'shadow-purple-500/20',
        text: 'text-purple-300',
        badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
        badgeLabel: 'Service Layer',
        icon: Cpu,
        colorHex: '#a855f7',
      };
    case 'class':
      return {
        border: 'border-emerald-500/60',
        bg: 'bg-emerald-950/70',
        glow: 'shadow-emerald-500/20',
        text: 'text-emerald-300',
        badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
        badgeLabel: 'Class',
        icon: Boxes,
        colorHex: '#10b981',
      };
    case 'function':
    case 'method':
      return {
        border: 'border-sky-500/60',
        bg: 'bg-sky-950/70',
        glow: 'shadow-sky-500/20',
        text: 'text-sky-300',
        badge: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
        badgeLabel: 'Function',
        icon: Code2,
        colorHex: '#0284c7',
      };
    case 'file':
      return {
        border: 'border-amber-500/60',
        bg: 'bg-amber-950/70',
        glow: 'shadow-amber-500/20',
        text: 'text-amber-300',
        badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
        badgeLabel: 'Source File',
        icon: FileCode,
        colorHex: '#f59e0b',
      };
    case 'folder':
      return {
        border: 'border-blue-500/60',
        bg: 'bg-blue-950/70',
        glow: 'shadow-blue-500/20',
        text: 'text-blue-300',
        badge: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
        badgeLabel: 'Directory',
        icon: Folder,
        colorHex: '#3b82f6',
      };
    case 'dependency':
      return {
        border: 'border-orange-500/60',
        bg: 'bg-orange-950/70',
        glow: 'shadow-orange-500/20',
        text: 'text-orange-300',
        badge: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
        badgeLabel: 'Dependency',
        icon: Braces,
        colorHex: '#f97316',
      };
    default:
      return {
        border: 'border-slate-600/60',
        bg: 'bg-slate-900/80',
        glow: 'shadow-slate-500/20',
        text: 'text-slate-300',
        badge: 'bg-slate-800 text-slate-300 border-slate-700',
        badgeLabel: nodeType.toUpperCase(),
        icon: Layers,
        colorHex: '#64748b',
      };
  }
};

// 2. Custom Node Component
const CustomKnowledgeNode: React.FC<NodeProps> = ({ data, selected }) => {
  const node = data.node as KnowledgeNode;
  const isSearchMatch = Boolean(data.isSearchMatch);
  const isFocused = Boolean(data.isFocused);
  const inDegree = Number(data.inDegree || 0);
  const outDegree = Number(data.outDegree || 0);

  const visuals = getNodeVisuals(node.node_type);
  const Icon = visuals.icon;

  return (
    <div
      className={`px-3.5 py-3 rounded-2xl border transition-all cursor-pointer shadow-xl backdrop-blur-md min-w-[210px] max-w-[260px] relative ${
        visuals.bg
      } ${visuals.border} ${
        isFocused
          ? 'ring-4 ring-brand-400 ring-offset-2 ring-offset-slate-950 shadow-2xl scale-105 z-30'
          : selected
          ? 'ring-2 ring-white/80 shadow-2xl scale-102 z-20'
          : isSearchMatch
          ? 'ring-2 ring-amber-400 shadow-amber-400/30 scale-102'
          : 'hover:border-slate-400/80 hover:scale-[1.01]'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-slate-900 transition-colors hover:!bg-white"
      />

      {/* Top row: badge + degrees */}
      <div className="flex items-center justify-between gap-1 mb-2">
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${visuals.text}`} />
          <span
            className={`text-[9px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-md border ${visuals.badge}`}
          >
            {visuals.badgeLabel}
          </span>
        </div>
        <div className="flex items-center gap-1 text-[9px] font-mono text-slate-400 bg-slate-900/80 px-1.5 py-0.5 rounded border border-slate-800">
          <span title="Incoming connections">{inDegree}↓</span>
          <span>·</span>
          <span title="Outgoing connections">{outDegree}↑</span>
        </div>
      </div>

      {/* Name / Label */}
      <div className="mb-1">
        <p
          className={`text-xs font-bold truncate leading-tight ${
            isFocused ? 'text-white' : 'text-slate-100'
          }`}
          title={node.label || node.name}
        >
          {node.label || node.name}
        </p>
      </div>

      {/* File Path or Subtitle */}
      {node.file_path && (
        <p
          className="text-[10px] font-mono text-slate-400 truncate opacity-80"
          title={node.file_path}
        >
          {node.file_path.split('/').pop()}
        </p>
      )}

      {/* API Method indicator */}
      {node.node_type === 'api' && node.metadata?.method && (
        <div className="mt-1.5 flex items-center gap-1">
          <span className="text-[9px] font-bold font-mono px-1 py-0.2 bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 rounded">
            {node.metadata.method}
          </span>
          <span className="text-[9px] font-mono text-slate-400 truncate">
            {node.metadata.path}
          </span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-brand-400 !border-2 !border-slate-900 transition-colors hover:!bg-white"
      />
    </div>
  );
};

// 3. Category Filter Definitions
type FilterCategory = 'ALL' | 'files' | 'classes' | 'apis' | 'services' | 'database';

export const ArchitectureExplorer: React.FC<ArchitectureExplorerProps> = ({
  projectId,
  projectName,
}) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [building, setBuilding] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters & exploration state
  const [activeCategory, setActiveCategory] = useState<FilterCategory>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [focusId, setFocusId] = useState<string | null>(null);
  const [depthLimit, setDepthLimit] = useState<number>(2);
  const [nodeLimit, setNodeLimit] = useState<number>(100);
  const [pageOffset, setPageOffset] = useState<number>(0);

  // Detail Inspector state
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [entityDetail, setEntityDetail] = useState<KnowledgeEntityDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Load Graph Data
  const loadGraph = useCallback(
    async (overrideFocus?: string | null, overrideOffset?: number) => {
      setLoading(true);
      setErrorMsg(null);
      try {
        const curFocus = overrideFocus !== undefined ? overrideFocus : focusId;
        const curOffset = overrideOffset !== undefined ? overrideOffset : pageOffset;

        let nodeTypesParam: string[] | undefined = undefined;
        if (activeCategory === 'files') nodeTypesParam = ['file', 'folder'];
        else if (activeCategory === 'classes') nodeTypesParam = ['class', 'interface'];
        else if (activeCategory === 'apis') nodeTypesParam = ['api'];
        else if (activeCategory === 'services') nodeTypesParam = ['service'];
        else if (activeCategory === 'database') nodeTypesParam = ['database'];

        const data = await fetchKnowledgeGraph(projectId, {
          node_types: nodeTypesParam,
          search: searchQuery.trim() || undefined,
          focus_id: curFocus || undefined,
          depth: curFocus ? depthLimit : undefined,
          limit: nodeLimit,
          offset: curOffset,
        });

        setGraphData(data);
      } catch (err: any) {
        console.warn('Error fetching knowledge graph:', err);
        setErrorMsg(err.message || 'Failed to load project knowledge graph');
      } finally {
        setLoading(false);
      }
    },
    [projectId, activeCategory, searchQuery, focusId, depthLimit, nodeLimit, pageOffset]
  );

  // Build / Re-build pipeline
  const handleBuildGraph = async () => {
    setBuilding(true);
    setErrorMsg(null);
    try {
      await buildKnowledgeGraph(projectId);
      await loadGraph(null, 0);
    } catch (err: any) {
      alert(`Knowledge graph build failed: ${err.message || err}`);
    } finally {
      setBuilding(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Load Entity Details when selected
  const handleNodeClick = async (_: any, flowNode: any) => {
    const kNode = flowNode.data?.node as KnowledgeNode;
    if (!kNode) return;
    setSelectedNode(kNode);
    setLoadingDetail(true);
    try {
      const detail = await fetchKnowledgeEntityDetail(projectId, kNode.id);
      setEntityDetail(detail);
    } catch (err) {
      console.warn('Failed to load entity detail:', err);
      setEntityDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Focus on node
  const handleFocusOnNode = (nodeId: string) => {
    setFocusId(nodeId);
    setPageOffset(0);
    loadGraph(nodeId, 0);
  };

  // Clear focus mode
  const handleClearFocus = () => {
    setFocusId(null);
    setPageOffset(0);
    loadGraph(null, 0);
  };

  // Map into React Flow nodes and edges
  const nodeTypes = useMemo(() => ({ customKnowledge: CustomKnowledgeNode }), []);

  const { flowNodes, flowEdges } = useMemo(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    // Compute in/out degrees
    const inDegrees: Record<string, number> = {};
    const outDegrees: Record<string, number> = {};
    (graphData.edges || []).forEach((e) => {
      const src = e.source || e.source_id || '';
      const tgt = e.target || e.target_id || '';
      outDegrees[src] = (outDegrees[src] || 0) + 1;
      inDegrees[tgt] = (inDegrees[tgt] || 0) + 1;
    });

    // Stratified column layout for clean cross-tier visual architecture
    // Column 0: Folders & Files
    // Column 1: APIs & Components
    // Column 2: Services
    // Column 3: Classes & Functions
    // Column 4: Database models
    // Column 5: Dependencies
    const tierColumns: Record<string, number> = {
      folder: 0,
      file: 0,
      component: 1,
      api: 1,
      service: 2,
      class: 3,
      interface: 3,
      function: 3,
      method: 3,
      database: 4,
      dependency: 5,
    };

    const columnBuckets: Record<number, KnowledgeNode[]> = {
      0: [],
      1: [],
      2: [],
      3: [],
      4: [],
      5: [],
    };

    graphData.nodes.forEach((n) => {
      const col = tierColumns[n.node_type.toLowerCase()] ?? 2;
      columnBuckets[col].push(n);
    });

    const COL_WIDTH = 340;
    const ROW_HEIGHT = 125;

    const nodesList = graphData.nodes.map((node) => {
      const col = tierColumns[node.node_type.toLowerCase()] ?? 2;
      const bucket = columnBuckets[col];
      const indexInCol = bucket.findIndex((b) => b.id === node.id);

      const isSearchMatch = Boolean(
        searchQuery.trim() &&
          (node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (node.file_path && node.file_path.toLowerCase().includes(searchQuery.toLowerCase())))
      );
      const isFocused = focusId === node.id;

      return {
        id: node.id,
        type: 'customKnowledge',
        position: {
          x: col * COL_WIDTH + 60,
          y: Math.max(0, indexInCol) * ROW_HEIGHT + 60,
        },
        data: {
          node,
          isSearchMatch,
          isFocused,
          inDegree: inDegrees[node.id] || 0,
          outDegree: outDegrees[node.id] || 0,
        },
      };
    });

    // Edge color mapping
    const getEdgeColor = (relType: string) => {
      switch (relType.toUpperCase()) {
        case 'QUERIES_DB':
        case 'ACCESSES_DB':
          return '#f43f5e'; // Rose
        case 'DEFINES_API':
        case 'HANDLED_BY':
          return '#06b6d4'; // Cyan
        case 'CALLS':
          return '#38bdf8'; // Sky
        case 'IMPORTS':
        case 'DEPENDS_ON':
          return '#a855f7'; // Purple
        case 'MAPS_TO_TABLE':
        case 'RELATIONSHIP_WITH':
          return '#ec4899'; // Pink
        case 'CONTAINS':
          return '#475569'; // Slate
        default:
          return '#64748b';
      }
    };

    const edgesList = (graphData.edges || []).map((edge, idx) => {
      const srcId = edge.source || edge.source_id || '';
      const tgtId = edge.target || edge.target_id || '';
      const color = getEdgeColor(edge.relationship_type);
      const isHighlighted = Boolean(
        selectedNode && (srcId === selectedNode.id || tgtId === selectedNode.id)
      );

      return {
        id: edge.id || `edge-${idx}`,
        source: srcId,
        target: tgtId,
        type: 'smoothstep',
        animated: Boolean(
          edge.relationship_type.includes('CALLS') ||
          edge.relationship_type.includes('QUERIES') ||
          edge.relationship_type.includes('ACCESSES') ||
          isHighlighted
        ),
        style: {
          stroke: isHighlighted ? '#ffffff' : color,
          strokeWidth: isHighlighted ? 2.5 : 1.5,
          opacity: isHighlighted ? 1 : 0.65,
        },
        label: edge.relationship_type,
        labelStyle: {
          fill: '#94a3b8',
          fontWeight: 600,
          fontSize: 9,
          fontFamily: 'monospace',
        },
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.8,
          rx: 4,
          ry: 4,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighlighted ? '#ffffff' : color,
          width: 14,
          height: 14,
        },
      };
    });

    return { flowNodes: nodesList, flowEdges: edgesList };
  }, [graphData, searchQuery, focusId, selectedNode]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Categories config
  const categories = [
    { id: 'ALL', label: 'All Tiers', icon: Network },
    { id: 'files', label: 'Files & Folders', icon: FileCode },
    { id: 'classes', label: 'Classes & Types', icon: Boxes },
    { id: 'apis', label: 'APIs & Endpoints', icon: Globe },
    { id: 'services', label: 'Services & Logic', icon: Cpu },
    { id: 'database', label: 'Database & Models', icon: Database },
  ];

  return (
    <div className="space-y-4">
      {/* Top Banner / Controls Header */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
                <Network className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                  Unified Project Knowledge Graph
                  {focusId && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-500/40">
                      Focus Mode Active
                    </span>
                  )}
                </h3>
                <p className="text-xs text-slate-400">
                  Cross-tier topology connecting Frontend → APIs → Services → Repositories → Database
                </p>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {focusId && (
              <button
                onClick={handleClearFocus}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition-all"
              >
                <X className="w-3.5 h-3.5" />
                <span>Exit Focus Mode</span>
              </button>
            )}

            <button
              onClick={() => loadGraph()}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handleBuildGraph}
              disabled={building}
              className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all disabled:opacity-50"
            >
              {building ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              <span>{building ? 'Synthesizing Graph...' : 'Rebuild Knowledge Graph'}</span>
            </button>
          </div>
        </div>

        {/* Graph Summary Metrics Chips */}
        {graphData?.stats && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="font-semibold text-slate-200">Nodes:</span>
              <span className="px-2 py-0.5 rounded-md bg-slate-800 font-mono text-white font-bold">
                {graphData.stats.total_nodes}
              </span>
            </div>

            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="font-semibold text-slate-200">Edges:</span>
              <span className="px-2 py-0.5 rounded-md bg-slate-800 font-mono text-brand-300 font-bold">
                {graphData.stats.total_edges}
              </span>
            </div>

            <div className="h-3 w-px bg-slate-800 hidden sm:block" />

            {/* Node types breakdown pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              {Object.entries(graphData.stats.node_types || {}).map(([type, count]) => {
                const visuals = getNodeVisuals(type as KnowledgeNodeType);
                return (
                  <span
                    key={type}
                    className={`px-2 py-0.5 rounded-md text-[10px] font-mono border ${visuals.badge}`}
                  >
                    {type}: <strong>{count}</strong>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Filter and Control Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 p-3 rounded-2xl bg-slate-900/60 border border-slate-800">
        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const isSelected = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => {
                  setActiveCategory(cat.id as FilterCategory);
                  setPageOffset(0);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                  isSelected
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                    : 'bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700/60'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        {/* Search, Focus Depth, Node Limits */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Input */}
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search entities, APIs, DB..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Depth limit selector (active when focusing) */}
          <div className="flex items-center gap-1 bg-slate-950/80 border border-slate-800 rounded-xl px-2 py-1 text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-500">Depth:</span>
            {[1, 2, 3].map((d) => (
              <button
                key={d}
                onClick={() => setDepthLimit(d)}
                className={`px-1.5 py-0.5 rounded text-[11px] font-mono font-bold transition-all ${
                  depthLimit === d
                    ? 'bg-brand-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title={`Traverse up to ${d} hops`}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Node limit selector */}
          <div className="flex items-center gap-1 bg-slate-950/80 border border-slate-800 rounded-xl px-2 py-1 text-xs">
            <span className="text-[10px] uppercase font-bold text-slate-500">Max:</span>
            {[50, 100, 200].map((lim) => (
              <button
                key={lim}
                onClick={() => {
                  setNodeLimit(lim);
                  setPageOffset(0);
                }}
                className={`px-1.5 py-0.5 rounded text-[11px] font-mono font-bold transition-all ${
                  nodeLimit === lim
                    ? 'bg-brand-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {lim}
              </button>
            ))}
          </div>

          {/* Pagination Controls */}
          {graphData && (graphData.has_more || pageOffset > 0) && (
            <div className="flex items-center gap-1">
              <button
                disabled={pageOffset === 0}
                onClick={() => setPageOffset(Math.max(0, pageOffset - nodeLimit))}
                className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 disabled:opacity-40 text-xs font-semibold"
              >
                Prev
              </button>
              <span className="text-[11px] text-slate-400 font-mono px-1">
                {pageOffset + 1}–{pageOffset + (graphData.nodes?.length || 0)}
              </span>
              <button
                disabled={!graphData.has_more}
                onClick={() => setPageOffset(pageOffset + nodeLimit)}
                className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 disabled:opacity-40 text-xs font-semibold"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Graph Canvas Area */}
      <div className="relative w-full h-[650px] bg-[#0b0f19] border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
        {loading && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 text-brand-400 animate-spin" />
            <p className="text-xs font-semibold text-slate-300">Loading Knowledge Graph...</p>
          </div>
        )}

        {/* Empty State when no nodes exist */}
        {!loading && (!graphData || graphData.nodes.length === 0) && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-8 text-center bg-slate-950/90">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/30 text-brand-400 flex items-center justify-center mb-4 shadow-xl">
              <Network className="w-8 h-8" />
            </div>
            <h4 className="text-base font-bold text-white mb-2">No Knowledge Graph Built Yet</h4>
            <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
              DocPilot AI unifies repository discovery, code AST parsing, dependencies, API endpoints,
              and database ORM models into a unified project knowledge graph.
            </p>
            <button
              onClick={handleBuildGraph}
              disabled={building}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold shadow-lg shadow-brand-600/30 transition-all"
            >
              {building ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              <span>Build Unified Knowledge Graph Now</span>
            </button>
          </div>
        )}

        {/* ReactFlow Interactive Canvas */}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
          minZoom={0.15}
          maxZoom={1.5}
        >
          <Background color="#1e293b" gap={24} size={1.2} variant={BackgroundVariant.Dots} />
          <Controls className="!bg-slate-900 !border-slate-800 !fill-white" />
          <MiniMap
            nodeColor={(n: any) => {
              const node = n.data?.node as KnowledgeNode;
              return getNodeVisuals(node?.node_type || 'class').colorHex;
            }}
            className="!bg-slate-950/90 !border-slate-800"
          />
        </ReactFlow>

        {/* Floating Tier Legend in bottom-left */}
        <div className="absolute bottom-4 left-4 z-10 p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md shadow-xl text-[10px] hidden md:block">
          <p className="font-bold text-slate-400 uppercase tracking-wider mb-1.5">Architecture Tiers</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span className="text-slate-300">API Routes</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-400" />
              <span className="text-slate-300">Services</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-300">Classes/Types</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-400" />
              <span className="text-slate-300">Database Models</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="text-slate-300">Source Files</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span className="text-slate-300">Folders</span>
            </div>
          </div>
        </div>

        {/* Selected Entity Inspector Panel (Slide-in Drawer) */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-96 max-h-[92%] bg-slate-900/95 border border-slate-700/80 rounded-2xl p-5 shadow-2xl backdrop-blur-xl z-20 overflow-y-auto text-left">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                {(() => {
                  const visuals = getNodeVisuals(selectedNode.node_type);
                  const Icon = visuals.icon;
                  return (
                    <div className={`p-2 rounded-xl border ${visuals.badge}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                  );
                })()}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {selectedNode.node_type}
                  </span>
                  <h4 className="text-sm font-bold text-white break-all">{selectedNode.label || selectedNode.name}</h4>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedNode(null);
                  setEntityDetail(null);
                }}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Actions */}
            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={() => handleFocusOnNode(selectedNode.id)}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md transition-all"
              >
                <Target className="w-3.5 h-3.5" />
                <span>Focus on Entity ({depthLimit} Hops)</span>
              </button>
            </div>

            {/* Entity metadata */}
            <div className="mt-4 space-y-2 text-xs">
              {selectedNode.file_path && (
                <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 font-mono">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-0.5">
                    File Location
                  </span>
                  <span className="text-cyan-300 break-all">{selectedNode.file_path}</span>
                </div>
              )}

              {/* Deep Knowledge Answers (What uses this? Connected APIs? Connected DB?) */}
              {loadingDetail && (
                <div className="py-6 flex flex-col items-center justify-center gap-2 text-slate-400">
                  <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
                  <span className="text-xs">Querying architectural connections...</span>
                </div>
              )}

              {entityDetail && !loadingDetail && (
                <div className="space-y-4 pt-2">
                  {/* 1. What uses this? (Incoming Calls / Importers) */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                        <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400" />
                        <span>What Uses This? ({entityDetail.incoming_edges.length})</span>
                      </span>
                    </div>
                    {entityDetail.incoming_edges.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic">No incoming usages detected</p>
                    ) : (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {entityDetail.incoming_edges.map((e, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleFocusOnNode(e.source || e.source_id || '')}
                            className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-slate-700 cursor-pointer flex items-center justify-between text-[11px]"
                          >
                            <span className="font-semibold text-slate-200 truncate">{e.source_name}</span>
                            <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-950/80 px-1.5 py-0.5 rounded border border-emerald-500/30">
                              {e.relationship_type}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 2. Connected APIs */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Connected APIs ({entityDetail.connected_apis.length})</span>
                      </span>
                    </div>
                    {entityDetail.connected_apis.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic">No direct API endpoints connected</p>
                    ) : (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {entityDetail.connected_apis.map((api, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleFocusOnNode(api.id)}
                            className="p-2 rounded-lg bg-cyan-950/40 border border-cyan-500/30 hover:border-cyan-500/60 cursor-pointer text-[11px]"
                          >
                            <div className="flex items-center gap-1 font-semibold text-cyan-200 truncate">
                              <span>{api.name}</span>
                            </div>
                            {api.file_path && (
                              <p className="text-[9px] font-mono text-slate-400 truncate mt-0.5">
                                {api.file_path}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 3. Connected Database Models */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                        <Database className="w-3.5 h-3.5 text-rose-400" />
                        <span>Connected Database Models ({entityDetail.connected_database_models.length})</span>
                      </span>
                    </div>
                    {entityDetail.connected_database_models.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic">No connected database models</p>
                    ) : (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {entityDetail.connected_database_models.map((db, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleFocusOnNode(db.id)}
                            className="p-2 rounded-lg bg-rose-950/40 border border-rose-500/30 hover:border-rose-500/60 cursor-pointer text-[11px]"
                          >
                            <span className="font-semibold text-rose-200">{db.name}</span>
                            {db.file_path && (
                              <p className="text-[9px] font-mono text-slate-400 truncate mt-0.5">
                                {db.file_path}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 4. Dependencies / Outgoing */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                        <GitFork className="w-3.5 h-3.5 text-purple-400" />
                        <span>Dependencies ({entityDetail.outgoing_edges.length})</span>
                      </span>
                    </div>
                    {entityDetail.outgoing_edges.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic">No outgoing dependencies</p>
                    ) : (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {entityDetail.outgoing_edges.map((e, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleFocusOnNode(e.target || e.target_id || '')}
                            className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-slate-700 cursor-pointer flex items-center justify-between text-[11px]"
                          >
                            <span className="font-semibold text-slate-200 truncate">{e.target_name}</span>
                            <span className="text-[9px] font-mono font-bold text-purple-400 bg-purple-950/80 px-1.5 py-0.5 rounded border border-purple-500/30">
                              {e.relationship_type}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
