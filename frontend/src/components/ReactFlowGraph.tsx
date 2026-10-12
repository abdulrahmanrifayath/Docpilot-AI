import React, { useState, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Box, Layers, Database, Globe, Info } from 'lucide-react';

interface ReactFlowGraphProps {
  flowData: {
    nodes: any[];
    edges: any[];
  };
}

// Custom Node Component
const CustomNode: React.FC<NodeProps> = ({ data, selected }) => {
  const category = (data.category as string) || 'core';
  const color = (data.color as string) || '#8b5cf6';

  const getIcon = () => {
    switch (category) {
      case 'api':
        return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      case 'service':
        return <Layers className="w-3.5 h-3.5 text-emerald-400" />;
      case 'model':
        return <Database className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Box className="w-3.5 h-3.5 text-violet-400" />;
    }
  };

  return (
    <div
      className={`px-3.5 py-2.5 rounded-xl border bg-slate-900/90 shadow-lg min-w-[200px] transition-all cursor-pointer ${
        selected ? 'ring-2 ring-brand-500 shadow-brand-500/30' : 'hover:border-slate-600'
      }`}
      style={{ borderColor: selected ? '#8b5cf6' : `${color}40` }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-500 !w-2 !h-2" />
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          {getIcon()}
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{category}</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {Number(data.in_degree || 0)} in · {Number(data.out_degree || 0)} out
        </span>
      </div>
      <p className="text-xs font-semibold text-white truncate">{String(data.label || '')}</p>
      <p className="text-[10px] text-slate-400 font-mono truncate mt-0.5">{String(data.path || '')}</p>
      <Handle type="source" position={Position.Right} className="!bg-brand-500 !w-2 !h-2" />
    </div>
  );
};

export const ReactFlowGraph: React.FC<ReactFlowGraphProps> = ({ flowData }) => {
  const nodeTypes = useMemo(() => ({ custom: CustomNode }), []);
  const [nodes, , onNodesChange] = useNodesState(flowData.nodes || []);
  const [edges, , onEdgesChange] = useEdgesState(flowData.edges || []);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);

  const onNodeClick = (_: any, node: any) => {
    setSelectedNode(node);
  };

  return (
    <div className="w-full h-[620px] bg-[#0b0f19] border border-slate-800 rounded-2xl overflow-hidden relative shadow-2xl">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls className="!bg-slate-900 !border-slate-800 !fill-white" />
        <MiniMap
          nodeColor={(node: any) => node.data?.color || '#8b5cf6'}
          className="!bg-slate-950/80 !border-slate-800"
        />
      </ReactFlow>

      {/* Selected Node Details Sidebar Drawer */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-72 bg-slate-900/95 border border-slate-700/80 rounded-xl p-4 shadow-2xl backdrop-blur-md z-10 text-left">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-brand-400" />
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-300">Node Inspector</h5>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-500 hover:text-white text-xs px-1"
            >
              ✕
            </button>
          </div>

          <div className="mt-3 space-y-2.5">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-500">Symbol / Label</p>
              <p className="text-sm font-semibold text-white">{selectedNode.data.label}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-500">File Path</p>
              <p className="text-xs font-mono text-cyan-300 break-all">{selectedNode.data.path}</p>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs">
              <div className="bg-slate-800/50 p-2 rounded-lg">
                <p className="text-[10px] text-slate-400">Inbound Dependents</p>
                <p className="text-base font-bold text-emerald-400">{selectedNode.data.in_degree}</p>
              </div>
              <div className="bg-slate-800/50 p-2 rounded-lg">
                <p className="text-[10px] text-slate-400">Outbound Imports</p>
                <p className="text-base font-bold text-brand-400">{selectedNode.data.out_degree}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
