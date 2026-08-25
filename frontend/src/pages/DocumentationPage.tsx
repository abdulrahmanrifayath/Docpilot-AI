import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import {
  BookOpen,
  Sparkles,
  Code,
} from 'lucide-react';

export const DocumentationPage: React.FC = () => {
  const { activeProject } = useProject();
  const [selectedDocSection, setSelectedDocSection] = useState('overview');

  const docSections = [
    { id: 'overview', title: 'System Overview', badge: 'Auto' },
    { id: 'onboarding', title: 'Developer Onboarding Guide', badge: 'Guide' },
    { id: 'architecture', title: 'Component Architecture', badge: 'Core' },
    { id: 'api_endpoints', title: 'API Endpoints & Contracts', badge: 'REST' },
    { id: 'data_models', title: 'Data Models & Schemas', badge: 'DB' },
    { id: 'dependencies', title: 'Third-party Dependencies', badge: 'Deps' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-indigo-400" />
            Software Documentation
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Structured, multi-layer developer documentation generated from code analysis and AST extraction.
          </p>
        </div>

        {activeProject && (
          <div className="flex items-center gap-2">
            <Badge variant="primary" size="md">
              Target: {activeProject.name}
            </Badge>
          </div>
        )}
      </div>

      {/* Main Documentation Split View */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Left Navigation Tree */}
        <div className="md:col-span-1 space-y-3">
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
            <div className="text-[11px] font-mono uppercase text-slate-500 px-2 py-1">
              Doc Modules
            </div>
            {docSections.map((sec) => (
              <button
                key={sec.id}
                onClick={() => setSelectedDocSection(sec.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  selectedDocSection === sec.id
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <span>{sec.title}</span>
                <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-800 text-slate-400">
                  {sec.badge}
                </span>
              </button>
            ))}
          </div>

          <Card className="p-4 bg-slate-900/40">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Incremental Generation</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed">
              When code changes occur, DocPilot only re-analyzes modified modules and regenerates affected documentation sections.
            </p>
          </Card>
        </div>

        {/* Right Content Panel */}
        <div className="md:col-span-3">
          <Card className="p-8 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-[11px] font-mono text-indigo-400 uppercase">
                  {activeProject?.name || 'Workspace'} Documentation
                </span>
                <h2 className="text-xl font-bold text-white mt-1 capitalize">
                  {selectedDocSection.replace('_', ' ')}
                </h2>
              </div>
              <Badge variant="neutral">Phase 3 Integration</Badge>
            </div>

            <div className="prose prose-invert max-w-none text-xs text-slate-300 space-y-4 leading-relaxed">
              <p>
                This section will automatically render synthesized developer guides, module summaries, and class-level documentation extracted by the DocPilot parser pipeline.
              </p>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 font-mono text-xs text-slate-400">
                <div className="text-indigo-400 font-semibold mb-2 flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  Documentation Pipeline Specifications
                </div>
                <ul className="list-disc list-inside space-y-1 text-slate-400">
                  <li>Automated Architecture & Sequence overview generation</li>
                  <li>Developer Onboarding Guide tailored to stack & dependencies</li>
                  <li>FastAPI / Express / Django endpoint specifications</li>
                  <li>SQLAlchemy / Prisma / Mongoose data models</li>
                </ul>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
