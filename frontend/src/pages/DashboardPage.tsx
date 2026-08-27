import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { useSystem } from '../context/SystemContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { CreateProjectModal } from '../components/projects/CreateProjectModal';
import { Link, useNavigate } from 'react-router-dom';
import {
  FolderGit2,
  BookOpen,
  GitBranch,
  Bot,
  Activity,
  Plus,
  ArrowRight,
  Database,
  Cpu,
  HardDrive,
  Sparkles,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { projects, activeProject, setActiveProject } = useProject();
  const { status } = useSystem();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* Top Banner / Welcome */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-900/40 via-slate-900/60 to-slate-900/90 border border-indigo-500/20 p-6 md:p-8 backdrop-blur-xl">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-medium mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Developer Knowledge Workspace</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
            DocPilot AI Control Center
          </h1>
          <p className="text-sm text-slate-300 mt-2 leading-relaxed">
            Ingest software repositories, detect architectures, construct interactive dependency graphs, and generate comprehensive documentation.
          </p>
          <div className="flex items-center gap-3 mt-5">
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsCreateOpen(true)}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Analyze New Repository
            </Button>
            <Link to="/projects">
              <Button variant="outline" size="md">
                View All Repositories
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <FolderGit2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Tracked Repositories</div>
            <div className="text-2xl font-bold text-white mt-0.5">{projects.length}</div>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Database Engine</div>
            <div className="text-lg font-bold text-white mt-0.5 uppercase">
              {status?.database.engine || 'SQLite'}
            </div>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">AI Model</div>
            <div className="text-sm font-bold text-white mt-0.5 font-mono truncate max-w-[140px]">
              {status?.ai_provider.model || 'gpt-4o-mini'}
            </div>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Vector Index</div>
            <div className="text-lg font-bold text-white mt-0.5">
              {status?.vector_db.status === 'ready' ? 'Active' : 'Standby'}
            </div>
          </div>
        </Card>
      </div>

      {/* Active Project Highlight & Quick Navigation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Active Project Overview */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-indigo-400" />
              Active Project Focus
            </h2>
            {activeProject && (
              <Link
                to={`/projects/${activeProject.id}`}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
              >
                Project Details <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>

          {activeProject ? (
            <Card className="p-6 border-indigo-500/20">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-lg font-bold text-white">{activeProject.name}</h3>
                    <Badge variant={activeProject.status === 'READY' ? 'success' : 'neutral'} dot>
                      {activeProject.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 max-w-xl">
                    {activeProject.description || 'No description provided for this repository.'}
                  </p>
                </div>
                <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 capitalize border border-slate-700">
                  {activeProject.source_type}
                </span>
              </div>

              {/* Quick Actions for Active Project */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6 pt-6 border-t border-slate-800/80">
                <Link
                  to="/documentation"
                  className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/60 transition-all text-xs font-medium text-slate-200"
                >
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  <span>Documentation</span>
                </Link>
                <Link
                  to="/diagrams"
                  className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/60 transition-all text-xs font-medium text-slate-200"
                >
                  <GitBranch className="w-4 h-4 text-cyan-400" />
                  <span>Architecture</span>
                </Link>
                <Link
                  to="/chat"
                  className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/60 transition-all text-xs font-medium text-slate-200"
                >
                  <Bot className="w-4 h-4 text-violet-400" />
                  <span>AI Assistant</span>
                </Link>
              </div>
            </Card>
          ) : (
            <Card className="p-8 text-center border-dashed">
              <FolderGit2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-300">No Active Project Selected</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Create a new project or select an existing repository to start automated analysis and documentation generation.
              </p>
              <Button
                variant="primary"
                size="sm"
                className="mt-4"
                onClick={() => setIsCreateOpen(true)}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                Add Your First Project
              </Button>
            </Card>
          )}

          {/* Recent Projects List */}
          <div>
            <h2 className="text-base font-semibold text-white tracking-tight mb-4">
              All Projects ({projects.length})
            </h2>
            {projects.length === 0 ? (
              <div className="text-xs text-slate-500 italic">No repositories added yet.</div>
            ) : (
              <div className="space-y-2.5">
                {projects.slice(0, 5).map((project) => (
                  <div
                    key={project.id}
                    onClick={() => {
                      setActiveProject(project);
                      navigate(`/projects/${project.id}`);
                    }}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer ${
                      activeProject?.id === project.id
                        ? 'bg-slate-800/80 border-indigo-500/40 text-white'
                        : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-800/50 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <FolderGit2 className="w-4 h-4 text-indigo-400" />
                      <div>
                        <div className="text-xs font-semibold">{project.name}</div>
                        <div className="text-[11px] text-slate-500 truncate max-w-xs md:max-w-md">
                          {project.description || 'No description'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={project.status === 'READY' ? 'success' : 'neutral'} size="sm">
                        {project.status}
                      </Badge>
                      <ArrowRight className="w-4 h-4 text-slate-500" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Analysis Pipeline Status */}
        <div className="space-y-6">
          <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Analysis Pipeline Steps
          </h2>

          <Card className="space-y-4">
            <div className="text-xs text-slate-400 leading-relaxed">
              DocPilot AI transforms raw code into semantic intelligence through a structured multi-stage pipeline:
            </div>

            <ol className="space-y-3 relative border-l border-slate-800 ml-2 pl-4 text-xs">
              <li className="space-y-0.5">
                <span className="font-semibold text-white block">1. Repository Extraction</span>
                <span className="text-slate-400 text-[11px]">Git clone or ZIP archive unpacking.</span>
              </li>
              <li className="space-y-0.5">
                <span className="font-semibold text-white block">2. File Discovery & Language Detection</span>
                <span className="text-slate-400 text-[11px]">Identifies Python, JS, TS and framework markers.</span>
              </li>
              <li className="space-y-0.5">
                <span className="font-semibold text-white block">3. Code Parsing & AST Metadata</span>
                <span className="text-slate-400 text-[11px]">Extracts classes, methods, imports, and decorators.</span>
              </li>
              <li className="space-y-0.5">
                <span className="font-semibold text-white block">4. Knowledge Graph & Diagrams</span>
                <span className="text-slate-400 text-[11px]">Builds component relationships and Mermaid diagrams.</span>
              </li>
              <li className="space-y-0.5">
                <span className="font-semibold text-white block">5. Vector Embeddings & AI Chat</span>
                <span className="text-slate-400 text-[11px]">Indexed knowledge retrieval for targeted Q&A.</span>
              </li>
            </ol>
          </Card>
        </div>
      </div>

      <CreateProjectModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </div>
  );
};
