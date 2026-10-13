import React, { useState } from 'react';
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
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

export const DiagramsPage: React.FC = () => {
  const { activeProject } = useProjects();
  const [selectedDiagram, setSelectedDiagram] = useState<string>('architecture');

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
    { id: 'architecture', name: 'High-Level Architecture', icon: Workflow, desc: 'Overall system layout & services' },
    { id: 'dependencies', name: 'Component Dependencies', icon: Layers, desc: 'Module & package graph' },
    { id: 'er', name: 'Entity Relationship (ER)', icon: Database, desc: 'Data models & schema relations' },
    { id: 'sequence', name: 'Request Lifecycle', icon: GitFork, desc: 'End-to-end request sequence' },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">System Architecture & Diagrams</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Visual representations of code organization, service relationships, and database models
          </p>
        </div>
      </div>

      {/* Phase 4 Notice */}
      <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-start gap-3">
        <Info className="w-5 h-5 shrink-0 text-indigo-400 mt-0.5" />
        <div>
          <h4 className="font-bold text-white mb-0.5">Architecture Visualization Engine</h4>
          <p className="text-indigo-200/90 leading-relaxed">
            Automatic interactive ReactFlow graph generation and Mermaid syntax compilation will be hooked up in Phase
            4. Below is the interactive workbench canvas.
          </p>
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

      {/* Canvas Workspace */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6 min-h-[420px] flex flex-col justify-between">
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

        {/* Mock Canvas View */}
        <div className="flex-1 flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-brand-400 mb-3 shadow-inner">
            <Workflow className="w-8 h-8" />
          </div>
          <h3 className="text-sm font-bold text-white mb-1">
            {activeProject.name} — Visual Diagram Ready for Phase 4
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Repository files are cataloged in sandbox isolation. Phase 4 will parse dependencies to generate high-fidelity
            Mermaid and ReactFlow interactive network diagrams.
          </p>
        </div>

        <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
          <span>Renderer: Mermaid 10.x & ReactFlow 11.x</span>
          <span>Status: Schema Ready</span>
        </div>
      </div>
    </div>
  );
};
