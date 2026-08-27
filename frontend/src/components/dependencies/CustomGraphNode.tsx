import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import {
  Server,
  Box,
  Code2,
  Package,
  FileCode,
} from 'lucide-react';

export interface CustomNodeData {
  label: string;
  type: string;
  file_path?: string;
  line_number?: number;
  is_internal?: boolean;
  metadata?: Record<string, any>;
}

const getNodeStyles = (type: string, isInternal = true) => {
  if (!isInternal) {
    return {
      border: 'border-purple-500/40 hover:border-purple-400',
      bg: 'bg-purple-950/40',
      badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      text: 'text-purple-200',
      icon: <Package className="w-3.5 h-3.5 text-purple-400" />,
      tag: 'external pkg',
    };
  }

  switch (type.toLowerCase()) {
    case 'service':
      return {
        border: 'border-cyan-500/40 hover:border-cyan-400',
        bg: 'bg-slate-900/90',
        badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
        text: 'text-cyan-200',
        icon: <Server className="w-3.5 h-3.5 text-cyan-400" />,
        tag: 'service',
      };
    case 'class':
      return {
        border: 'border-emerald-500/40 hover:border-emerald-400',
        bg: 'bg-slate-900/90',
        badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        text: 'text-emerald-200',
        icon: <Box className="w-3.5 h-3.5 text-emerald-400" />,
        tag: 'class',
      };
    case 'function':
      return {
        border: 'border-blue-500/40 hover:border-blue-400',
        bg: 'bg-slate-900/90',
        badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
        text: 'text-blue-200',
        icon: <Code2 className="w-3.5 h-3.5 text-blue-400" />,
        tag: 'function',
      };
    case 'file':
    default:
      return {
        border: 'border-indigo-500/30 hover:border-indigo-400',
        bg: 'bg-slate-900/90',
        badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
        text: 'text-slate-200',
        icon: <FileCode className="w-3.5 h-3.5 text-indigo-400" />,
        tag: 'file',
      };
  }
};

export const CustomGraphNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as unknown as CustomNodeData;
  const styles = getNodeStyles(nodeData.type, nodeData.is_internal ?? true);

  return (
    <div
      className={`min-w-[190px] max-w-[240px] p-3 rounded-xl border ${styles.bg} ${styles.border} transition-all duration-200 shadow-lg ${
        selected ? 'ring-2 ring-indigo-400 shadow-indigo-500/20' : ''
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-indigo-500 border border-slate-900 rounded-full !top-[-5px]"
      />

      <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-slate-800">
        <div className="flex items-center gap-1.5 truncate">
          {styles.icon}
          <span className={`text-[11px] font-bold font-mono truncate ${styles.text}`}>
            {nodeData.label}
          </span>
        </div>
        <span
          className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border uppercase shrink-0 ${styles.badge}`}
        >
          {styles.tag}
        </span>
      </div>

      {nodeData.file_path && (
        <div className="text-[10px] text-slate-400 font-mono truncate mt-1.5">
          {nodeData.file_path}
          {nodeData.line_number && <span className="text-slate-500">:{nodeData.line_number}</span>}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-indigo-500 border border-slate-900 rounded-full !bottom-[-5px]"
      />
    </div>
  );
});

CustomGraphNode.displayName = 'CustomGraphNode';
