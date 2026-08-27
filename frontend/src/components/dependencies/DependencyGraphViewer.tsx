import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Node,
  Edge,
  BackgroundVariant,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

import { projectsApi } from '../../api/projects';
import {
  DependencyGraphResponse,
  AnalyzeDependenciesResponse,
  GraphNode as ApiGraphNode,
} from '../../types';
import { CustomGraphNode } from './CustomGraphNode';
import { Button } from '../common/Button';
import {
  GitBranch,
  Search,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  X,
  Sliders,
} from 'lucide-react';

interface DependencyGraphViewerProps {
  projectId: string;
}

const nodeTypes = {
  custom: CustomGraphNode,
};

const getEdgeColor = (type: string) => {
  switch (type) {
    case 'EXTENDS':
    case 'IMPLEMENTS':
      return '#10B981'; // emerald
    case 'DEPENDS_ON':
    case 'USES':
      return '#06B6D4'; // cyan
    case 'CALLS':
      return '#3B82F6'; // blue
    case 'IMPORTS':
    default:
      return '#6366F1'; // indigo
  }
};

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction = 'TB'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 40,
    ranksep: 70,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 75 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - 110,
        y: nodeWithPosition.y - 37.5,
      },
    };
  });

  return { nodes: newNodes, edges };
};

export const DependencyGraphViewer: React.FC<DependencyGraphViewerProps> = ({
  projectId,
}) => {
  const [graphData, setGraphData] = useState<DependencyGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [includeExternal, setIncludeExternal] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRelTypes, setSelectedRelTypes] = useState<Set<string>>(
    new Set(['IMPORTS', 'CALLS', 'EXTENDS', 'DEPENDS_ON', 'USES', 'IMPLEMENTS'])
  );
  const [selectedNode, setSelectedNode] = useState<ApiGraphNode | null>(null);
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeDependenciesResponse | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const fetchGraph = async () => {
    try {
      setIsLoading(true);
      const data = await projectsApi.getDependencyGraph(projectId, includeExternal);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load dependency graph:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [projectId, includeExternal]);

  const handleRunAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      const res = await projectsApi.analyzeDependencies(projectId);
      setAnalyzeResult(res);
      await fetchGraph();
    } catch (err) {
      console.error('Failed to analyze dependencies:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Convert API Graph to React Flow Nodes & Edges
  useEffect(() => {
    if (!graphData) return;

    // Filter edges by active relationship types
    const filteredEdges = graphData.edges.filter((e) =>
      selectedRelTypes.has(e.relationship_type)
    );

    // Filter nodes by search
    const rfNodes: Node[] = graphData.nodes.map((n) => {
      const matchesSearch =
        !searchQuery.trim() ||
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (n.file_path && n.file_path.toLowerCase().includes(searchQuery.toLowerCase()));

      return {
        id: n.id,
        type: 'custom',
        position: { x: n.position.x || 0, y: n.position.y || 0 },
        data: {
          label: n.label,
          type: n.type,
          file_path: n.file_path,
          line_number: n.line_number,
          is_internal: n.is_internal,
          metadata: n.metadata,
        },
        selected: selectedNode?.id === n.id,
        style: {
          opacity: matchesSearch ? 1 : 0.25,
        },
      };
    });

    const rfEdges: Edge[] = filteredEdges.map((e) => {
      const color = getEdgeColor(e.relationship_type);
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: e.relationship_type === 'CALLS' || e.relationship_type === 'USES',
        label: e.label || e.relationship_type,
        labelStyle: { fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' },
        labelBgStyle: { fill: '#0b0f17', fillOpacity: 0.85 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
        style: { stroke: color, strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: color,
          width: 15,
          height: 15,
        },
      };
    });

    // Run automated Dagre layout
    const layouted = getLayoutedElements(rfNodes, rfEdges, 'LR');
    setNodes(layouted.nodes);
    setEdges(layouted.edges);
  }, [graphData, selectedRelTypes, searchQuery, selectedNode]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (!graphData) return;
      const found = graphData.nodes.find((n) => n.id === node.id);
      setSelectedNode(found || null);
    },
    [graphData]
  );

  const toggleRelType = (type: string) => {
    setSelectedRelTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        if (next.size > 1) next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const handleAutoArrange = () => {
    const layouted = getLayoutedElements(nodes, edges, 'LR');
    setNodes([...layouted.nodes]);
    setEdges([...layouted.edges]);
  };

  // Node details (incoming/outgoing)
  const nodeConnections = useMemo(() => {
    if (!selectedNode || !graphData) return { incoming: [], outgoing: [] };
    const incoming = graphData.edges.filter((e) => e.target === selectedNode.id);
    const outgoing = graphData.edges.filter((e) => e.source === selectedNode.id);
    return { incoming, outgoing };
  }, [selectedNode, graphData]);

  return (
    <div className="space-y-4">
      {/* Top Header Controls Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <GitBranch className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight uppercase">
                Dependency & Architecture Graph
              </h3>
              <p className="text-xs text-slate-400">
                Static relationship mapping between services, classes, functions, and packages
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-mono">
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
              <strong className="text-white">{graphData?.total_nodes || 0}</strong> Nodes
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-indigo-300">
              <strong className="text-indigo-400">{graphData?.internal_edges_count || 0}</strong> Internal Edges
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-purple-300">
              <strong className="text-purple-400">{graphData?.external_edges_count || 0}</strong> Package Edges
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {analyzeResult && (
            <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Analyzed in {analyzeResult.duration_ms}ms
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleAutoArrange}
            leftIcon={<Sliders className="w-3.5 h-3.5" />}
          >
            Auto-Arrange
          </Button>

          <Button
            variant="primary"
            size="sm"
            isLoading={isAnalyzing}
            onClick={handleRunAnalysis}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />}
          >
            Re-analyze Graph
          </Button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-mono text-slate-400 uppercase mr-1">
            Relationships:
          </span>
          {['IMPORTS', 'CALLS', 'EXTENDS', 'DEPENDS_ON', 'USES'].map((type) => {
            const isActive = selectedRelTypes.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleRelType(type)}
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border transition-all ${
                  isActive
                    ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50'
                    : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'
                }`}
              >
                {type}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeExternal}
              onChange={(e) => setIncludeExternal(e.target.checked)}
              className="rounded bg-slate-950 border-slate-800 text-indigo-500 focus:ring-indigo-500"
            />
            <span className="text-[11px] font-mono">Include Packages</span>
          </label>

          <div className="relative w-48">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes..."
              className="w-full pl-8 pr-2.5 py-1 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Canvas & Sidebar Split Container */}
      <div className="relative w-full h-[600px] rounded-2xl bg-[#090D16] border border-slate-800 overflow-hidden shadow-2xl">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm z-20">
            <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center z-10">
            <GitBranch className="w-12 h-12 text-slate-600 mb-3" />
            <h4 className="text-sm font-bold text-white">No Dependency Graph Generated Yet</h4>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Click "Re-analyze Graph" to trigger static import and relationship analysis.
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunAnalysis}
              className="mt-4"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Analyze Dependencies Now
            </Button>
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
            minZoom={0.2}
            maxZoom={2.0}
            className="react-flow-dark"
          >
            <Background color="#1e293b" gap={20} size={1.5} variant={BackgroundVariant.Dots} />
            <Controls className="!bg-slate-900 !border !border-slate-800 !rounded-xl !shadow-xl !fill-slate-400" />
            <MiniMap
              nodeColor={(n) => {
                if (n.data?.type === 'service') return '#06B6D4';
                if (n.data?.type === 'class') return '#10B981';
                if (n.data?.type === 'function') return '#3B82F6';
                if (n.data?.type === 'package') return '#A855F7';
                return '#6366F1';
              }}
              className="!bg-slate-950/90 !border !border-slate-800 !rounded-xl"
              maskColor="rgba(11, 15, 23, 0.7)"
            />
          </ReactFlow>
        )}

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-80 max-h-[550px] p-4 rounded-2xl bg-slate-950/95 border border-slate-800 shadow-2xl backdrop-blur-md overflow-y-auto space-y-3 z-30">
            <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                  {selectedNode.type}
                </span>
                <h4 className="text-sm font-bold text-white font-mono mt-1 truncate">
                  {selectedNode.label}
                </h4>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {selectedNode.file_path && (
              <div className="text-xs text-slate-300 font-mono bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                <div className="text-[10px] text-slate-500 uppercase">File Location:</div>
                <div className="truncate mt-0.5">{selectedNode.file_path}</div>
              </div>
            )}

            <div className="p-2 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-[11px] text-emerald-300 flex items-center gap-1.5 font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Static analysis detected (100% confidence)</span>
            </div>

            {/* Outgoing Connections */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-mono text-slate-400 uppercase font-bold">
                Dependencies ({nodeConnections.outgoing.length}):
              </div>
              {nodeConnections.outgoing.length === 0 ? (
                <div className="text-[11px] text-slate-500 italic">No outgoing dependencies</div>
              ) : (
                nodeConnections.outgoing.map((edge) => (
                  <div
                    key={edge.id}
                    className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono flex items-center justify-between gap-1"
                  >
                    <span className="text-slate-400 flex items-center gap-1 truncate">
                      <ArrowRight className="w-3 h-3 text-indigo-400 shrink-0" />
                      <strong className="text-white truncate">{edge.target.split(':').slice(1).join(':')}</strong>
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/40 shrink-0">
                      {edge.relationship_type}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Incoming Connections */}
            <div className="space-y-1.5 pt-2 border-t border-slate-800">
              <div className="text-[11px] font-mono text-slate-400 uppercase font-bold">
                Referenced By ({nodeConnections.incoming.length}):
              </div>
              {nodeConnections.incoming.length === 0 ? (
                <div className="text-[11px] text-slate-500 italic">No incoming references</div>
              ) : (
                nodeConnections.incoming.map((edge) => (
                  <div
                    key={edge.id}
                    className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono flex items-center justify-between gap-1"
                  >
                    <span className="text-slate-400 flex items-center gap-1 truncate">
                      <ArrowRight className="w-3 h-3 text-emerald-400 shrink-0" />
                      <strong className="text-white truncate">{edge.source.split(':').slice(1).join(':')}</strong>
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/40 shrink-0">
                      {edge.relationship_type}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
