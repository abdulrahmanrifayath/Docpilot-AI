import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Workflow,
  Layers,
  Database,
  GitFork,
  Server,
  FolderTree,
  FileCode2,
  RefreshCw,
  Loader2,
  Sparkles,
  Download,
  AlertTriangle,
  FolderKanban,
  CheckCircle2,
  ExternalLink,
  Info,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import {
  fetchProjectDiagrams,
  generateDiagrams,
  regenerateProjectDiagram,
  fetchDependencyGraph,
} from '../api/client';
import { DiagramItem, DependencyGraphResponse, ArchitectureDiagramType } from '../types';
import { MermaidViewer } from '../components/MermaidViewer';
import { DependencyGraphViewer } from '../components/DependencyGraphViewer';
import { ArchitectureExplorer } from '../components/ArchitectureExplorer';

export const DiagramsPage: React.FC = () => {
  const { activeProject, projects, setActiveProject } = useProjects();
  const [selectedType, setSelectedType] = useState<string>('SYSTEM_ARCHITECTURE');
  const [diagrams, setDiagrams] = useState<DiagramItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Dependency graph fallback data for interactive view
  const [graphData, setGraphData] = useState<DependencyGraphResponse | null>(null);

  useEffect(() => {
    if (activeProject?.id) {
      loadDiagrams(activeProject.id);
    }
  }, [activeProject?.id]);

  const loadDiagrams = async (projId: string) => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchProjectDiagrams(projId);
      setDiagrams(items);
      if (items.length > 0) {
        // If the currently selected type is not available, default to the first one
        const types = items.map((d) => d.diagram_type.toUpperCase());
        if (!types.includes(selectedType) && selectedType !== 'unified' && selectedType !== 'interactive_flow') {
          setSelectedType(items[0].diagram_type.toUpperCase());
        }
      }
    } catch (err: any) {
      console.warn('Failed to load diagrams:', err);
      setError(err?.message || 'Failed to fetch diagrams');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAll = async () => {
    if (!activeProject?.id) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await generateDiagrams(activeProject.id, {
        include_flow_data: true,
        use_llm_enhancement: false,
        force_regenerate: false,
      });
      setDiagrams(res.diagrams);
      if (res.diagrams.length > 0) {
        setSelectedType(res.diagrams[0].diagram_type.toUpperCase());
      }
    } catch (err: any) {
      setError(err?.message || 'Diagram generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerateCurrent = async (diagramId: string) => {
    if (!activeProject?.id) return;
    setRegeneratingId(diagramId);
    setError(null);
    try {
      const updated = await regenerateProjectDiagram(activeProject.id, diagramId);
      setDiagrams((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err: any) {
      setError(err?.message || 'Failed to regenerate diagram');
    } finally {
      setRegeneratingId(null);
    }
  };

  const loadInteractiveGraph = async () => {
    if (!activeProject?.id || graphData) return;
    try {
      const data = await fetchDependencyGraph(activeProject.id);
      setGraphData(data);
    } catch (e) {
      console.warn('Failed to load interactive dependency graph', e);
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-24 text-center">
        <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-brand-500/5">
          <Workflow className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6 max-w-sm mx-auto">
          Select or register a repository project to automatically generate and explore architectural diagrams.
        </p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
        >
          <FolderKanban className="w-4 h-4" />
          <span>Select Project</span>
        </Link>
      </div>
    );
  }

  // Diagram types definitions for the Explorer
  const diagramTabs = [
    {
      id: 'SYSTEM_ARCHITECTURE',
      name: 'System Architecture',
      icon: Server,
      desc: 'High-level topology: Clients → APIs → Services → DB',
    },
    {
      id: 'MODULE_ARCHITECTURE',
      name: 'Module Architecture',
      icon: FolderTree,
      desc: 'Package subsystems & inter-module dependencies',
    },
    {
      id: 'DEPENDENCY_DIAGRAM',
      name: 'Component Dependencies',
      icon: Layers,
      desc: 'Static code entities, imports, calls & inheritance',
    },
    {
      id: 'API_SERVICE_RELATIONSHIP',
      name: 'API Request Flow',
      icon: GitFork,
      desc: 'Endpoints → Handlers → Services → Database Models',
    },
    {
      id: 'DATABASE_ER',
      name: 'Database ER Diagram',
      icon: Database,
      desc: 'Relational schema, tables, fields & cardinalities',
    },
    {
      id: 'interactive_flow',
      name: 'Interactive React Flow',
      icon: Workflow,
      desc: 'Physics-based interactive entity canvas',
    },
    {
      id: 'unified',
      name: 'Knowledge Graph Explorer',
      icon: Sparkles,
      desc: 'Unified multi-tier cross-repository graph',
    },
  ];

  // Find active diagram object for the selected tab
  const activeDiagram = diagrams.find(
    (d) =>
      d.diagram_type.toUpperCase() === selectedType ||
      (selectedType === 'DATABASE_ER' && d.diagram_type.toLowerCase() === 'er') ||
      (selectedType === 'SYSTEM_ARCHITECTURE' && d.diagram_type.toLowerCase() === 'architecture') ||
      (selectedType === 'DEPENDENCY_DIAGRAM' && d.diagram_type.toLowerCase() === 'dependency')
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Header & Project Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Automatic Diagram Explorer</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Grounded architectural diagrams synthesized directly from static AST, dependencies, APIs, and ORM analysis.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Project Switcher */}
          {projects && projects.length > 1 && (
            <select
              value={activeProject.id}
              onChange={(e) => {
                const found = projects.find((p) => p.id === e.target.value);
                if (found) setActiveProject(found);
              }}
              className="bg-slate-900 border border-slate-800 text-xs rounded-xl px-3 py-2 text-slate-300 focus:outline-none focus:border-brand-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}

          {/* Generate All Diagrams Button */}
          <button
            onClick={handleGenerateAll}
            disabled={generating || loading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-brand-600/25 transition-all"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            <span>{generating ? 'Synthesizing Diagrams...' : 'Generate All Diagrams'}</span>
          </button>
        </div>
      </div>

      {/* Error Alert Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold text-rose-200">Diagram Pipeline Error: </span>
            {error}
          </div>
          <button
            onClick={() => setError(null)}
            className="text-slate-400 hover:text-white text-xs font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Diagram Type Selector Navigation Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2.5">
        {diagramTabs.map((tab) => {
          const Icon = tab.icon;
          const isSelected = selectedType === tab.id;
          const hasGenerated = diagrams.some(
            (d) =>
              d.diagram_type.toUpperCase() === tab.id ||
              (tab.id === 'DATABASE_ER' && d.diagram_type.toLowerCase() === 'er') ||
              (tab.id === 'SYSTEM_ARCHITECTURE' && d.diagram_type.toLowerCase() === 'architecture') ||
              (tab.id === 'DEPENDENCY_DIAGRAM' && d.diagram_type.toLowerCase() === 'dependency')
          );

          return (
            <button
              key={tab.id}
              onClick={() => {
                setSelectedType(tab.id);
                if (tab.id === 'interactive_flow') {
                  loadInteractiveGraph();
                }
              }}
              className={`p-3 rounded-2xl border text-left transition-all relative flex flex-col justify-between ${
                isSelected
                  ? 'bg-brand-600/15 border-brand-500/60 shadow-lg shadow-brand-500/10'
                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Icon
                    className={`w-4 h-4 ${isSelected ? 'text-brand-400' : 'text-slate-400'}`}
                  />
                  {hasGenerated && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Diagram available" />
                  )}
                </div>
                <h3
                  className={`text-xs font-bold leading-tight ${
                    isSelected ? 'text-white' : 'text-slate-300'
                  }`}
                >
                  {tab.name}
                </h3>
              </div>
              <p className="text-[10px] text-slate-400 mt-1 line-clamp-2">{tab.desc}</p>
            </button>
          );
        })}
      </div>

      {/* Main Canvas Presentation View */}
      {selectedType === 'unified' ? (
        <ArchitectureExplorer
          projectId={activeProject.id}
          projectName={activeProject.name}
        />
      ) : selectedType === 'interactive_flow' ? (
        <div className="space-y-4">
          <DependencyGraphViewer
            graphData={graphData}
            onRefresh={loadInteractiveGraph}
            isLoading={loading}
          />
        </div>
      ) : loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-20 text-center flex flex-col items-center justify-center min-h-[460px]">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin mb-3" />
          <h3 className="text-sm font-semibold text-white">Loading Diagrams...</h3>
          <p className="text-xs text-slate-400 mt-1">Retrieving stored Mermaid models and graph data</p>
        </div>
      ) : activeDiagram ? (
        <div className="space-y-4">
          {/* Enhanced Mermaid Diagram Viewer with Zoom, Fullscreen, SVG Export, and Regeneration */}
          <MermaidViewer
            code={activeDiagram.mermaid_code}
            title={activeDiagram.title}
            description={activeDiagram.description}
            version={activeDiagram.version}
            onRegenerate={() => handleRegenerateCurrent(activeDiagram.id)}
            isRegenerating={regeneratingId === activeDiagram.id}
          />

          {/* Grounding Source Entities & Metadata Bar */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  Grounded Source References ({activeDiagram.source_entities?.length || 0}):
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
                {activeDiagram.source_entities && activeDiagram.source_entities.length > 0 ? (
                  activeDiagram.source_entities.map((ent, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] font-mono text-slate-300"
                    >
                      {ent}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-500 italic">Static repository components</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0 text-[11px] text-slate-400 font-mono">
              <span>Version: <strong className="text-white">v{activeDiagram.version}</strong></span>
              <span>•</span>
              <span>Updated: <strong className="text-slate-300">{activeDiagram.updated_at ? new Date(activeDiagram.updated_at).toLocaleTimeString() : 'N/A'}</strong></span>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State when Diagram of this type has not been generated yet */
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm p-16 text-center flex flex-col items-center justify-center min-h-[460px]">
          <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-brand-400 mb-4 shadow-inner">
            <Server className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1.5">
            {diagramTabs.find((t) => t.id === selectedType)?.name || 'Diagram'} Not Generated Yet
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Automatic architecture diagrams are compiled deterministically from your static code entities,
            dependencies, REST APIs, and database schemas.
          </p>
          <button
            onClick={handleGenerateAll}
            disabled={generating}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            <span>Generate Architecture Diagrams</span>
          </button>
        </div>
      )}
    </div>
  );
};
