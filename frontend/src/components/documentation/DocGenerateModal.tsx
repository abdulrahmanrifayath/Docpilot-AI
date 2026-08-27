import React, { useState, useEffect } from 'react';
import { projectsApi } from '../../api/projects';
import { DocStatusResponse } from '../../types';
import { Button } from '../common/Button';
import {
  X,
  Sparkles,
  CheckSquare,
  Square,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Layers,
  Globe,
  Database,
  Box,
  Code2,
  Folder,
  FileCode,
  RefreshCw,
} from 'lucide-react';

interface DocGenerateModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const ALL_DOC_TYPES = [
  { id: 'PROJECT_OVERVIEW', label: 'Project Technical Overview', desc: 'Executive summary, tech stack, and module architecture', icon: Sparkles },
  { id: 'README', label: 'README.md', desc: 'Standard repository README with quickstart and API tables', icon: FileText },
  { id: 'ARCHITECTURE_OVERVIEW', label: 'Architecture Overview', desc: 'System layering, component topology, and data flow', icon: Layers },
  { id: 'API_DOCUMENTATION', label: 'REST API Documentation', desc: 'Endpoint parameters, schemas, handlers, and auth specs', icon: Globe },
  { id: 'DATABASE_DOCUMENTATION', label: 'Database Schema & ER', desc: 'Relational tables, columns, data types, and foreign keys', icon: Database },
  { id: 'FOLDER_DOC', label: 'Folder Hierarchy Guide', desc: 'Directory structure and architectural responsibilities', icon: Folder },
  { id: 'FILE_DOC', label: 'File Specifications', desc: 'Declared modules, classes, and exported interfaces by file', icon: FileCode },
  { id: 'CLASS_DOC', label: 'Class & Interface Catalog', desc: 'Object-oriented classes, inheritance, and methods', icon: Box },
  { id: 'FUNCTION_DOC', label: 'Function & Routine Catalog', desc: 'Function signatures, parameter types, and return values', icon: Code2 },
];

export const DocGenerateModal: React.FC<DocGenerateModalProps> = ({
  projectId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [selectedTypes, setSelectedTypes] = useState<string[]>(ALL_DOC_TYPES.map((d) => d.id));
  const [forceRegenerate, setForceRegenerate] = useState(false);
  const [usePreviewMock, setUsePreviewMock] = useState(false);
  const [status, setStatus] = useState<DocStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchStatus = async () => {
      try {
        setIsLoadingStatus(true);
        const data = await projectsApi.getDocStatus(projectId);
        if (isMounted) {
          setStatus(data);
          // If LLM is not configured, default preview mock mode to true so user can test
          if (!data.llm_configured) {
            setUsePreviewMock(true);
          }
        }
      } catch (err) {
        console.error('Failed to load doc status:', err);
      } finally {
        if (isMounted) setIsLoadingStatus(false);
      }
    };

    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, [projectId, isOpen]);

  if (!isOpen) return null;

  const toggleType = (id: string) => {
    if (selectedTypes.includes(id)) {
      setSelectedTypes(selectedTypes.filter((t) => t !== id));
    } else {
      setSelectedTypes([...selectedTypes, id]);
    }
  };

  const selectAll = () => {
    setSelectedTypes(ALL_DOC_TYPES.map((d) => d.id));
  };

  const deselectAll = () => {
    setSelectedTypes([]);
  };

  const handleGenerate = async () => {
    if (selectedTypes.length === 0) return;

    try {
      setIsGenerating(true);
      setError(null);

      await projectsApi.generateDocs(projectId, {
        document_types: selectedTypes,
        force_regenerate: forceRegenerate,
        provider: usePreviewMock ? 'mock' : undefined,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error('Failed to generate documentation:', err);
      setError(err?.response?.data?.detail || err.message || 'Documentation generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                AI Documentation Generator
              </h3>
              <p className="text-xs text-slate-400">
                Generate production-grade developer documentation grounded in repository facts
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* LLM Status Banner */}
          {isLoadingStatus ? (
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2 text-xs font-mono text-slate-400">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" />
              <span>Checking AI provider status...</span>
            </div>
          ) : status?.llm_configured ? (
            <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-emerald-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>
                  <strong>AI Provider Active:</strong> {status.provider} ({status.model})
                </span>
              </div>
              <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200">
                <input
                  type="checkbox"
                  checked={usePreviewMock}
                  onChange={(e) => setUsePreviewMock(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                />
                <span className="text-[11px]">Use Fast Mock Mode</span>
              </label>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/30 space-y-2 text-xs">
              <div className="flex items-center gap-2 text-amber-300 font-mono">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  <strong>LLM API Key Not Configured:</strong> Set <code>LLM_API_KEY</code> or <code>OPENAI_API_KEY</code> in your environment for live LLM completions.
                </span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-amber-500/20 font-mono">
                <span className="text-slate-400 text-[11px]">
                  You can generate using <strong>Local Fact-Grounded Mock Engine</strong> for testing.
                </span>
                <label className="flex items-center gap-1.5 cursor-pointer text-amber-300 font-bold">
                  <input
                    type="checkbox"
                    checked={usePreviewMock}
                    onChange={(e) => setUsePreviewMock(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0"
                  />
                  <span>Enable Mock Mode</span>
                </label>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-red-950/50 border border-red-500/30 text-xs font-mono text-red-300">
              {error}
            </div>
          )}

          {/* Type Selector Toolbar */}
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
              Select Document Types ({selectedTypes.length}/{ALL_DOC_TYPES.length})
            </h4>
            <div className="flex items-center gap-2 text-xs font-mono">
              <button
                onClick={selectAll}
                className="text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Select All
              </button>
              <span className="text-slate-600">•</span>
              <button
                onClick={deselectAll}
                className="text-slate-400 hover:text-slate-300 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Grid of Document Types */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {ALL_DOC_TYPES.map((item) => {
              const isSelected = selectedTypes.includes(item.id);
              const Icon = item.icon;

              return (
                <div
                  key={item.id}
                  onClick={() => toggleType(item.id)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                    isSelected
                      ? 'bg-indigo-600/15 border-indigo-500/50 shadow-sm'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="pt-0.5 text-indigo-400">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-indigo-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-xs font-bold text-white font-mono">{item.label}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5 leading-snug">
                      {item.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Force Regenerate Option */}
          <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-mono text-slate-300">
              <input
                type="checkbox"
                checked={forceRegenerate}
                onChange={(e) => setForceRegenerate(e.target.checked)}
                className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
              />
              <span>Force Overwrite & Increment Version</span>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between gap-3">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isGenerating}>
            Cancel
          </Button>

          <Button
            variant="primary"
            size="sm"
            isLoading={isGenerating}
            disabled={selectedTypes.length === 0}
            onClick={handleGenerate}
            leftIcon={<Sparkles className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />}
          >
            {isGenerating
              ? `Generating ${selectedTypes.length} Documents...`
              : `Generate ${selectedTypes.length} Document${selectedTypes.length !== 1 ? 's' : ''}`}
          </Button>
        </div>
      </div>
    </div>
  );
};
