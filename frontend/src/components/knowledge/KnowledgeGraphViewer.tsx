import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  NodeProps,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { projectsApi } from '../../api/projects';
import {
  KnowledgeGraphResponse,
  KnowledgeNode,
  KnowledgeBuildResponse,
} from '../../types';
import { KnowledgeNodeInspector } from './KnowledgeNodeInspector';
import { Button } from '../common/Button';
import {
  Network,
  Search,
  RefreshCw,
  Target,
  CheckCircle2,
  SlidersHorizontal,
  X,
} from 'lucide-react';

interface KnowledgeGraphViewerProps {
  projectId: string;
}

const getCategoryColor = (category: string) => {
  switch (category?.toUpperCase()) {
    case 'API':
      return {
        bg: 'bg-cyan-950/80',
        border: 'border-cyan-500/60',
        text: 'text-cyan-300',
        badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
        shadow: 'shadow-cyan-500/20',
      };
    case 'DATABASE_TABLE':
      return {
        bg: 'bg-emerald-950/80',
        border: 'border-emerald-500/60',
        text: 'text-emerald-300',
        badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        shadow: 'shadow-emerald-500/20',
      };
    case 'CLASS':
      return {
        bg: 'bg-indigo-950/80',
        border: 'border-indigo-500/60',
        text: 'text-indigo-300',
        badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
        shadow: 'shadow-indigo-500/20',
      };
    case 'FUNCTION':
    case 'METHOD':
      return {
        bg: 'bg-blue-950/80',
        border: 'border-blue-500/60',
        text: 'text-blue-300',
        badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
        shadow: 'shadow-blue-500/20',
      };
    case 'FILE':
      return {
        bg: 'bg-slate-900/90',
        border: 'border-slate-700',
        text: 'text-slate-200',
        badge: 'bg-slate-800 text-slate-300 border-slate-700',
        shadow: 'shadow-slate-500/10',
      };
    case 'FOLDER':
      return {
        bg: 'bg-purple-950/80',
        border: 'border-purple-500/60',
        text: 'text-purple-300',
        badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
        shadow: 'shadow-purple-500/20',
      };
    default:
      return {
        bg: 'bg-slate-900',
        border: 'border-slate-700',
        text: 'text-slate-300',
        badge: 'bg-slate-800 text-slate-300 border-slate-700',
        shadow: '',
      };
  }
};

const CustomKnowledgeNode: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as KnowledgeNode;
  const colors = getCategoryColor(nodeData.category);

  return (
    <div
      className={`px-3.5 py-2.5 rounded-2xl border-2 transition-all font-mono min-w-[200px] max-w-[260px] cursor-pointer shadow-lg backdrop-blur-md ${
        colors.bg
      } ${colors.border} ${
        selected ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-950' : ''
      }`}
    >
      <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-indigo-500 border-2 border-slate-900" />

      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className={`text-[10px] px-2 py-0.2 rounded-md border font-bold uppercase tracking-wider ${colors.badge}`}>
          {nodeData.category}
        </span>
        <div className="flex items-center gap-1 text-[10px] text-slate-400">
          <span>↓{nodeData.in_degree}</span>
          <span>↑{nodeData.out_degree}</span>
        </div>
      </div>

      <div className={`text-xs font-bold truncate ${colors.text}`}>
        {nodeData.name}
      </div>

      {nodeData.file_path && (
        <div className="text-[10px] text-slate-400 truncate mt-1">
          {nodeData.file_path}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-2.5 h-2.5 bg-cyan-500 border-2 border-slate-900" />
    </div>
  );
};

const nodeTypes = {
  knowledgeNode: CustomKnowledgeNode,
};

export const KnowledgeGraphViewer: React.FC<KnowledgeGraphViewerProps> = ({ projectId }) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildResult, setBuildResult] = useState<KnowledgeBuildResponse | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [focusNodeKey, setFocusNodeKey] = useState<string | null>(null);
  const [selectedDepth, setSelectedDepth] = useState<number>(2);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);

  const fetchGraph = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: any = {
        depth: selectedDepth,
      };
      if (selectedCategory !== 'ALL') {
        params.categories = selectedCategory;
      }
      if (focusNodeKey) {
        params.focus_node_id = focusNodeKey;
      }
      if (searchQuery.trim()) {
        params.q = searchQuery.trim();
      }

      const data = await projectsApi.getKnowledgeGraph(projectId, params);
      setGraphData(data);

      // Convert to React Flow Nodes
      const rfNodes: Node[] = data.nodes.map((n) => ({
        id: n.node_key,
        type: 'knowledgeNode',
        position: n.position || { x: 0, y: 0 },
        data: n as any,
      }));

      // Convert to React Flow Edges
      const rfEdges: Edge[] = data.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || e.relationship.toLowerCase().replace('_', ' '),
        animated: e.relationship === 'CALLS' || e.relationship === 'HANDLES_ROUTE',
        style: {
          stroke:
            e.relationship === 'HANDLES_ROUTE'
              ? '#06b6d4'
              : e.relationship === 'QUERIES_TABLE'
              ? '#10b981'
              : e.relationship === 'DECLARES'
              ? '#6366f1'
              : '#475569',
          strokeWidth: 1.5,
        },
        labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color:
            e.relationship === 'HANDLES_ROUTE'
              ? '#06b6d4'
              : e.relationship === 'QUERIES_TABLE'
              ? '#10b981'
              : '#6366f1',
          width: 14,
          height: 14,
        },
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
    } catch (err) {
      console.error('Failed to load knowledge graph:', err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, selectedCategory, focusNodeKey, selectedDepth, searchQuery, setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const handleRunBuild = async () => {
    try {
      setIsBuilding(true);
      const res = await projectsApi.buildKnowledgeGraph(projectId);
      setBuildResult(res);
      await fetchGraph();
    } catch (err) {
      console.error('Failed to build knowledge graph:', err);
    } finally {
      setIsBuilding(false);
    }
  };

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode(node.data as unknown as KnowledgeNode);
  };

  const handleFocusNode = (key: string) => {
    setFocusNodeKey(key);
  };

  const handleClearFocus = () => {
    setFocusNodeKey(null);
  };

  const allCategories = useMemo(() => {
    return [
      'ALL',
      'API',
      'DATABASE_TABLE',
      'CLASS',
      'FUNCTION',
      'FILE',
      'FOLDER',
      'COMPONENT',
    ];
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight uppercase">
                Unified Project Knowledge Graph
              </h3>
              <p className="text-xs text-slate-400">
                Interconnected graph model linking folders, files, classes, functions, APIs, and database tables
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-200">
              <strong className="text-white">{graphData?.total_nodes || 0}</strong> Nodes
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-indigo-300">
              <strong className="text-indigo-400">{graphData?.total_edges || 0}</strong> Edges
            </span>
            {graphData &&
              Object.entries(graphData.counts_by_category).map(([cat, count]) => (
                <span
                  key={cat}
                  className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400"
                >
                  <strong className="text-slate-200">{count}</strong> {cat}
                </span>
              ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {buildResult && (
            <div className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>
                Compiled {buildResult.total_nodes} nodes & {buildResult.total_edges} edges in{' '}
                {buildResult.duration_ms}ms
              </span>
            </div>
          )}

          <Button
            variant="primary"
            size="sm"
            isLoading={isBuilding}
            onClick={handleRunBuild}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isBuilding ? 'animate-spin' : ''}`} />}
          >
            Re-build Knowledge Graph
          </Button>
        </div>
      </div>

      {/* Focus Mode Banner */}
      {focusNodeKey && (
        <div className="p-3 rounded-2xl bg-indigo-950/70 border border-indigo-500/40 flex items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2 text-indigo-300">
            <Target className="w-4 h-4 text-indigo-400" />
            <span>
              <strong>Focus Mode:</strong> Centered on <code className="text-white">{focusNodeKey}</code> (Depth: {selectedDepth})
            </span>
          </div>
          <button
            onClick={handleClearFocus}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 border border-indigo-700 text-slate-200 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            <span>Clear Focus</span>
          </button>
        </div>
      )}

      {/* Toolbar & Filter Bar */}
      <div className="p-3 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {allCategories.map((cat) => {
            const count =
              cat === 'ALL'
                ? graphData?.total_nodes || 0
                : graphData?.counts_by_category[cat] || 0;

            const isSelected = selectedCategory === cat;

            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-xs font-mono font-bold px-2.5 py-1.5 rounded-xl border transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50 shadow-sm'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                <span>{cat}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900 text-slate-400">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Depth & Search */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Depth Selector */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
            <span className="text-[10px] text-slate-500 px-2 flex items-center gap-1">
              <SlidersHorizontal className="w-3 h-3" />
              Depth
            </span>
            {[1, 2, 3].map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDepth(d)}
                className={`px-2 py-0.5 rounded-lg transition-colors ${
                  selectedDepth === d ? 'bg-slate-800 text-white' : 'text-slate-400'
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Search bar */}
          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter nodes by name..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="relative rounded-2xl bg-slate-950 border border-slate-800 h-[640px] overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <Network className="w-12 h-12 text-slate-600 mb-3" />
            <h4 className="text-sm font-bold text-white">No Matching Knowledge Nodes</h4>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Try adjusting category filters, clearing your search, or clicking "Re-build Knowledge Graph".
            </p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={2.5}
            className="bg-[#070b14]"
          >
            <Background color="#1e293b" gap={24} size={1} />
            <Controls className="bg-slate-900 border border-slate-800 text-slate-300" />
            <MiniMap
              nodeColor={(n) => {
                const cat = (n.data as any)?.category?.toUpperCase();
                if (cat === 'API') return '#06b6d4';
                if (cat === 'DATABASE_TABLE') return '#10b981';
                if (cat === 'CLASS') return '#6366f1';
                if (cat === 'FUNCTION') return '#3b82f6';
                if (cat === 'FOLDER') return '#a855f7';
                return '#64748b';
              }}
              maskColor="rgba(15, 23, 42, 0.7)"
              className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden"
            />
          </ReactFlow>
        )}

        {/* Slide-out Node Inspector */}
        {selectedNode && (
          <KnowledgeNodeInspector
            projectId={projectId}
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onFocusNode={handleFocusNode}
          />
        )}
      </div>
    </div>
  );
};
