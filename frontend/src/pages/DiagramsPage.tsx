import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Workflow,
  Layers,
  Database,
  ArrowRight,
  FolderKanban,
  Info,
  Maximize2,
  ZoomIn,
  ZoomOut,
  GitFork,
  Loader2,
  RefreshCw,
  Sparkles,
  Share2,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import { fetchDependencyGraph, analyzeDependencies } from '../api/client';
import { DependencyGraphResponse } from '../types';
import { DependencyGraphViewer } from '../components/DependencyGraphViewer';
import { DatabaseSchemaExplorer } from '../components/DatabaseSchemaExplorer';
import { ArchitectureExplorer } from '../components/ArchitectureExplorer';

export const DiagramsPage: React.FC = () => {
  const { activeProject } = useProjects();
  const [selectedDiagram, setSelectedDiagram] = useState<string>('unified');
  const [graphData, setGraphData] = useState<DependencyGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  useEffect(() => {
    if (activeProject?.id) {
      loadGraph(activeProject.id);
    }
  }, [activeProject?.id]);

  const loadGraph = async (projId: string) => {
    setLoading(true);
    try {
      const data = await fetchDependencyGraph(projId);
      setGraphData(data);
    } catch (err) {
      console.warn('Failed to load dependency graph:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!activeProject?.id) return;
    setAnalyzing(true);
    try {
      await analyzeDependencies(activeProject.id);
      await loadGraph(activeProject.id);
    } catch (err: any) {
      alert(`Dependency analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzing(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <Workflow className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Select an active project to view or generate its architectural diagrams and data flow representations.
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

  const diagramTypes = [
    { id: 'unified', name: 'Unified Knowledge Graph', icon: Workflow, desc: 'Cross-tier architecture: Files → APIs → Services → Database' },
    { id: 'dependencies', name: 'Component Dependencies', icon: Layers, desc: 'Interactive React Flow entity & dependency graph' },
    { id: 'er', name: 'Database ER Diagram', icon: Database, desc: 'Data models & schema relations' },
    { id: 'sequence', name: 'Request Lifecycle', icon: GitFork, desc: 'End-to-end request sequence' },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Architecture & Knowledge Graph</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Unified multi-tier knowledge graph connecting directories, files, AST entities, APIs, services, and database models.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-600/20 transition-all"
          >
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            <span>{analyzing ? 'Analyzing Dependencies...' : 'Analyze Dependencies'}</span>
          </button>
        </div>
      </div>

      {/* Diagram Type Selector */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {diagramTypes.map((item) => {
          const Icon = item.icon;
          const isSelected = selectedDiagram === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setSelectedDiagram(item.id)}
              className={`p-4 rounded-2xl border text-left transition-all ${
                isSelected
                  ? 'bg-brand-600/15 border-brand-500/60 shadow-lg shadow-brand-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-4 h-4 ${isSelected ? 'text-brand-400' : 'text-slate-400'}`} />
                <span className={`text-xs font-bold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                  {item.name}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">{item.desc}</p>
            </button>
          );
        })}
      </div>

      {/* Main Canvas Area */}
      {selectedDiagram === 'unified' ? (
        <ArchitectureExplorer
          projectId={activeProject.id}
          projectName={activeProject.name}
        />
      ) : selectedDiagram === 'dependencies' ? (
        <div className="space-y-4">
          <DependencyGraphViewer
            graphData={graphData}
            onRefresh={() => loadGraph(activeProject.id)}
            isLoading={loading || analyzing}
          />
        </div>
      ) : selectedDiagram === 'er' ? (
        <DatabaseSchemaExplorer
          projectId={activeProject.id}
          projectName={activeProject.name}
          defaultView="diagram"
        />
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6 min-h-[460px] flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
              <span>Visual Canvas:</span>
              <span className="capitalize font-bold text-white">{selectedDiagram.replace('-', ' ')}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <button className="p-1.5 rounded-lg hover:bg-slate-800 hover:text-white transition-colors" title="Zoom In">
                <ZoomIn className="w-4 h-4" />
              </button>
              <button className="p-1.5 rounded-lg hover:bg-slate-800 hover:text-white transition-colors" title="Zoom Out">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button className="p-1.5 rounded-lg hover:bg-slate-800 hover:text-white transition-colors" title="Fullscreen">
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-brand-400 mb-3 shadow-inner">
              <Share2 className="w-8 h-8" />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">
              {activeProject.name} — {selectedDiagram.toUpperCase()} Diagram View
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
              Switch to "Component Dependencies" to interact with the full React Flow node-edge graph parsed from repository source code.
            </p>
            <button
              onClick={() => setSelectedDiagram('dependencies')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-all"
            >
              <Layers className="w-4 h-4" />
              <span>View Component Dependencies Graph</span>
            </button>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
            <span>Renderer: React Flow & Directed Graph Engine</span>
            <span>Status: Ready</span>
          </div>
        </div>
      )}
    </div>
  );
};
