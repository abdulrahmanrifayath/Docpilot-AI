import React, { useEffect, useState } from 'react';
import { projectsApi } from '../../api/projects';
import { KnowledgeNode, KnowledgeEntityDetail } from '../../types';
import { Button } from '../common/Button';
import {
  X,
  Target,
  Globe,
  Database,
  ArrowRight,
  FileCode,
  Folder,
  Layers,
  Code2,
  Box,
  CornerDownRight,
  ExternalLink,
} from 'lucide-react';

interface KnowledgeNodeInspectorProps {
  projectId: string;
  node: KnowledgeNode;
  onClose: () => void;
  onFocusNode: (nodeKey: string) => void;
}

const getCategoryIcon = (category: string) => {
  switch (category.toUpperCase()) {
    case 'API':
      return <Globe className="w-4 h-4 text-cyan-400" />;
    case 'DATABASE_TABLE':
      return <Database className="w-4 h-4 text-emerald-400" />;
    case 'CLASS':
      return <Box className="w-4 h-4 text-indigo-400" />;
    case 'FUNCTION':
    case 'METHOD':
      return <Code2 className="w-4 h-4 text-blue-400" />;
    case 'FILE':
      return <FileCode className="w-4 h-4 text-slate-300" />;
    case 'FOLDER':
      return <Folder className="w-4 h-4 text-purple-400" />;
    default:
      return <Layers className="w-4 h-4 text-amber-400" />;
  }
};

const getCategoryBadgeClass = (category: string) => {
  switch (category.toUpperCase()) {
    case 'API':
      return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    case 'DATABASE_TABLE':
      return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
    case 'CLASS':
      return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
    case 'FUNCTION':
    case 'METHOD':
      return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
    case 'FILE':
      return 'bg-slate-800 text-slate-300 border-slate-700';
    case 'FOLDER':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
    default:
      return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
  }
};

export const KnowledgeNodeInspector: React.FC<KnowledgeNodeInspectorProps> = ({
  projectId,
  node,
  onClose,
  onFocusNode,
}) => {
  const [detail, setDetail] = useState<KnowledgeEntityDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchDetail = async () => {
      try {
        setIsLoading(true);
        const data = await projectsApi.getKnowledgeEntity(projectId, node.id);
        if (isMounted) {
          setDetail(data);
        }
      } catch (err) {
        console.error('Failed to load entity detail:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [projectId, node.id]);

  return (
    <div className="absolute top-4 right-4 bottom-4 w-96 bg-slate-900/95 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-xl flex flex-col z-30 overflow-hidden font-mono">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between gap-3 bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center">
            {getCategoryIcon(node.category)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.2 rounded-md border text-[10px] font-bold ${getCategoryBadgeClass(node.category)}`}>
                {node.category}
              </span>
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight mt-0.5 break-all">
              {node.name}
            </h3>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Action Toolbar */}
      <div className="px-4 py-2 bg-slate-950 border-b border-slate-800 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>In: <strong className="text-white">{node.in_degree}</strong></span>
          <span>•</span>
          <span>Out: <strong className="text-white">{node.out_degree}</strong></span>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => onFocusNode(node.node_key)}
          leftIcon={<Target className="w-3 h-3" />}
        >
          Focus Node
        </Button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Location */}
        {node.file_path && (
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[11px] text-slate-500 uppercase font-bold tracking-wider block mb-1">
              Source Location
            </span>
            <div className="text-slate-300 flex items-center gap-1.5 break-all">
              <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span>{node.file_path}{node.line_number ? `:${node.line_number}` : ''}</span>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
          </div>
        ) : (
          detail && (
            <>
              {/* Connected APIs */}
              {detail.connected_apis.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5" />
                    Connected APIs ({detail.connected_apis.length})
                  </h4>
                  <div className="space-y-1.5">
                    {detail.connected_apis.map((api) => (
                      <div
                        key={api.id}
                        onClick={() => onFocusNode(api.node_key)}
                        className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-cyan-500/40 cursor-pointer transition-colors flex items-center justify-between text-slate-200"
                      >
                        <span className="truncate">{api.name}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Connected Database Tables */}
              {detail.connected_database_tables.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5" />
                    Connected Database Tables ({detail.connected_database_tables.length})
                  </h4>
                  <div className="space-y-1.5">
                    {detail.connected_database_tables.map((tbl) => (
                      <div
                        key={tbl.id}
                        onClick={() => onFocusNode(tbl.node_key)}
                        className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-emerald-500/40 cursor-pointer transition-colors flex items-center justify-between text-slate-200"
                      >
                        <span className="truncate">{tbl.name}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upstream Callers */}
              {detail.upstream_callers.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                    <CornerDownRight className="w-3.5 h-3.5" />
                    Upstream Callers ({detail.upstream_callers.length})
                  </h4>
                  <div className="space-y-1.5">
                    {detail.upstream_callers.map((up) => (
                      <div
                        key={up.id}
                        onClick={() => onFocusNode(up.node_key)}
                        className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500/40 cursor-pointer transition-colors flex items-center justify-between text-slate-300"
                      >
                        <div className="flex items-center gap-2 truncate">
                          {getCategoryIcon(up.category)}
                          <span className="truncate">{up.name}</span>
                        </div>
                        <span className="text-[10px] text-slate-500">{up.category}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Downstream Dependencies */}
              {detail.downstream_dependencies.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[11px] font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                    <ArrowRight className="w-3.5 h-3.5" />
                    Downstream Dependencies ({detail.downstream_dependencies.length})
                  </h4>
                  <div className="space-y-1.5">
                    {detail.downstream_dependencies.map((down) => (
                      <div
                        key={down.id}
                        onClick={() => onFocusNode(down.node_key)}
                        className="p-2 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/40 cursor-pointer transition-colors flex items-center justify-between text-slate-300"
                      >
                        <div className="flex items-center gap-2 truncate">
                          {getCategoryIcon(down.category)}
                          <span className="truncate">{down.name}</span>
                        </div>
                        <span className="text-[10px] text-slate-500">{down.category}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata JSON */}
              {node.metadata && Object.keys(node.metadata).length > 0 && (
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[11px] text-slate-500 uppercase font-bold tracking-wider block mb-2">
                    Node Metadata
                  </span>
                  <pre className="text-[10px] text-slate-400 overflow-x-auto max-h-40 p-2 bg-slate-900 rounded-lg">
                    {JSON.stringify(node.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )
        )}
      </div>
    </div>
  );
};
