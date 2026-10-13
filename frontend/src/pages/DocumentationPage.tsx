import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  BookOpen,
  Code2,
  Workflow,
  Sparkles,
  Layers,
  FolderKanban,
  Search,
  ExternalLink,
  Info,
  Clock,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

export const DocumentationPage: React.FC = () => {
  const { activeProject, projects } = useProjects();
  const [activeTab, setActiveTab] = useState<'overview' | 'api' | 'architecture' | 'onboarding'>('overview');
  const [searchQuery, setSearchQuery] = useState<string>('');

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Please select an existing project from the top selector or create a new project to inspect its documentation.
        </p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
        >
          <FolderKanban className="w-4 h-4" />
          <span>Go to Projects</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Project Documentation</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Structured technical guides, architecture specifications, API references, and developer onboarding
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/projects/${activeProject.id}`}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-all"
          >
            <span>View Files</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Phase 3 Notice Banner */}
      <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-start gap-3">
        <Info className="w-5 h-5 shrink-0 text-indigo-400 mt-0.5" />
        <div>
          <h4 className="font-bold text-white mb-0.5">Automated Documentation Pipeline</h4>
          <p className="text-indigo-200/90 leading-relaxed">
            Project repository ingestion and isolated sandboxing are ready (Phase 2). Automated multi-language AST
            parsing and AI-powered document generation will be executed in Phase 3. Below is the preview layout for your
            generated documentation.
          </p>
        </div>
      </div>

      {/* Main Doc Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Nav */}
        <div className="lg:col-span-1 space-y-1">
          <div className="p-3 mb-2 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Documentation Sections
            </span>
            <div className="space-y-1">
              {[
                { id: 'overview', name: 'Overview & README', icon: BookOpen },
                { id: 'architecture', name: 'System Architecture', icon: Workflow },
                { id: 'api', name: 'API Reference', icon: Code2 },
                { id: 'onboarding', name: 'Developer Onboarding', icon: Sparkles },
              ].map((tab) => {
                const Icon = tab.icon;
                const isSelected = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left ${
                      isSelected
                        ? 'bg-brand-600 text-white font-semibold shadow-sm'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{tab.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-2">
            <span className="font-semibold text-slate-300 block">Repository Context</span>
            <p>
              Source: <span className="text-white capitalize">{activeProject.source_type}</span>
            </p>
            <p>
              Status: <span className="text-emerald-400 font-semibold">{activeProject.status}</span>
            </p>
            <p className="truncate" title={activeProject.repository_path}>
              Path: <span className="font-mono text-[10px] text-slate-400">{activeProject.repository_path}</span>
            </p>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="lg:col-span-3 rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6 sm:p-8">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-3">
                {activeProject.name} – Project Overview
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                {activeProject.description ||
                  'No description provided. DocPilot AI will generate comprehensive module summaries and dependency maps upon Phase 3 pipeline execution.'}
              </p>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-xs text-slate-300 space-y-2">
                <p className="text-brand-400 font-bold"># DocPilot Project Digest</p>
                <p>Repository: {activeProject.name}</p>
                <p>Status: {activeProject.status}</p>
                <p>Isolated Directory: {activeProject.repository_path}</p>
                <p>Created: {new Date(activeProject.created_at).toUTCString()}</p>
              </div>
            </div>
          )}

          {activeTab === 'architecture' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-3">
                System Architecture Specification
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                Automated component topology mapping will extract packages, modules, database entities, and inter-service dependencies.
              </p>
              <div className="p-8 rounded-xl bg-slate-950 border border-slate-800 text-center">
                <Workflow className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-white">Architecture Mapping Planned for Phase 4</p>
                <p className="text-[11px] text-slate-500 mt-1">Interactive ReactFlow and Mermaid diagrams will be rendered here.</p>
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-3">
                API Endpoint Specifications
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                Discovers REST, GraphQL, and gRPC endpoints automatically from source annotations and routing decorators.
              </p>
              <div className="p-8 rounded-xl bg-slate-950 border border-slate-800 text-center">
                <Code2 className="w-10 h-10 text-brand-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-white">Endpoint Extraction Active in Phase 3</p>
                <p className="text-[11px] text-slate-500 mt-1">Routes, parameters, models, and example payloads will be cataloged.</p>
              </div>
            </div>
          )}

          {activeTab === 'onboarding' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-3">
                Developer Onboarding Guide
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                Step-by-step setup guides, required toolchains, environment variables, and initial runbooks generated for new team members.
              </p>
              <div className="p-8 rounded-xl bg-slate-950 border border-slate-800 text-center">
                <Sparkles className="w-10 h-10 text-amber-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-white">Onboarding Synthesis</p>
                <p className="text-[11px] text-slate-500 mt-1">Accelerates developer time-to-first-commit from days to minutes.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
