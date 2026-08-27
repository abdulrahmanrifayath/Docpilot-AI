import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { DependencyGraphViewer } from '../components/dependencies/DependencyGraphViewer';
import {
  GitBranch,
  Database,
  ArrowRightLeft,
  Info,
} from 'lucide-react';

export const DiagramsPage: React.FC = () => {
  const { activeProject } = useProject();
  const [selectedDiagram, setSelectedDiagram] = useState<'architecture' | 'sequence' | 'er'>('architecture');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <GitBranch className="w-6 h-6 text-cyan-400" />
            Architecture & Visual Diagrams
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Interactive system architecture, sequence flows, and entity relationship diagrams.
          </p>
        </div>

        {/* Diagram Type Selector */}
        <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setSelectedDiagram('architecture')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedDiagram === 'architecture'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Architecture & Dependencies
          </button>
          <button
            onClick={() => setSelectedDiagram('sequence')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedDiagram === 'sequence'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sequence Flows
          </button>
          <button
            onClick={() => setSelectedDiagram('er')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedDiagram === 'er'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Database & ER
          </button>
        </div>
      </div>

      {selectedDiagram === 'architecture' ? (
        activeProject ? (
          <DependencyGraphViewer projectId={activeProject.id} />
        ) : (
          <Card className="p-12 text-center border-dashed">
            <Info className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <h3 className="text-sm font-bold text-white">No Project Selected</h3>
            <p className="text-xs text-slate-400 mt-1">
              Select or create a project to explore its interactive dependency graph.
            </p>
          </Card>
        )
      ) : (
        /* Sequence and ER diagram placeholder cards */
        <Card className="p-8 border-slate-800 min-h-[460px] flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Badge variant="accent" dot>
                {selectedDiagram.toUpperCase()} VIEW
              </Badge>
              <span className="text-xs text-slate-400">
                {activeProject ? `Repository: ${activeProject.name}` : 'No Project Active'}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="neutral">Deterministic Static Visualizer</Badge>
            </div>
          </div>

          <div className="my-8 p-12 rounded-2xl bg-[#0F172A]/70 border border-dashed border-slate-800 text-center flex flex-col items-center justify-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shadow-glow-cyan">
              {selectedDiagram === 'sequence' && <ArrowRightLeft className="w-8 h-8" />}
              {selectedDiagram === 'er' && <Database className="w-8 h-8" />}
            </div>

            <div className="max-w-md">
              <h3 className="text-sm font-semibold text-white">
                Automated {selectedDiagram === 'sequence' ? 'Execution Sequence' : 'Entity-Relationship'} Diagram
              </h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Visual flow diagrams extracted from route handlers, API callers, and database model entities.
              </p>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Powered by DocPilot AI Static Parser</span>
            <span>Deterministic Analysis</span>
          </div>
        </Card>
      )}
    </div>
  );
};
