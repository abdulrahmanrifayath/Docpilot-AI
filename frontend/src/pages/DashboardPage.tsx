import React from 'react';
import { Link } from 'react-router-dom';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  Database,
  Cpu,
  Layers,
  Activity,
  HardDrive,
  Plus,
  GitBranch,
  Archive,
  RefreshCw,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

export const DashboardPage: React.FC = () => {
  const { projects, systemStatus, refreshProjects, refreshStatus, loading } = useProjects();

  const isOperational = systemStatus?.status === 'operational';
  const readyProjects = projects.filter((p) => p.status === 'READY');
  const pendingProjects = projects.filter((p) => p.status === 'UPLOADING' || p.status === 'CLONING');
  const failedProjects = projects.filter((p) => p.status === 'FAILED');

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System & Project Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time status of the DocPilot AI core engine, databases, and managed repositories
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              refreshProjects();
              refreshStatus();
            }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-all"
            title="Refresh Status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <Link
            to="/projects"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </Link>
        </div>
      </div>

      {/* System Infrastructure Cards */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-brand-400" />
          <span>System Infrastructure Status</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Core Service */}
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs mb-3">
              <span className="text-slate-400 font-semibold">Core API Service</span>
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isOperational ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'
                }`}
              />
            </div>
            <div>
              <p className="text-lg font-bold text-white tracking-tight">
                {systemStatus?.application?.name || 'DocPilot AI API'}
              </p>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                <span>Version {systemStatus?.application?.version || '1.0.0'}</span>
                <span>•</span>
                <span className="capitalize">{systemStatus?.application?.environment || 'Production'}</span>
              </div>
            </div>
          </div>

          {/* Database */}
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs mb-3">
              <span className="text-slate-400 font-semibold">Primary Database</span>
              <Database className="w-4 h-4 text-brand-400" />
            </div>
            <div>
              <p className="text-lg font-bold text-white tracking-tight capitalize">
                {systemStatus?.database?.type || 'SQLite (Local)'}
              </p>
              <div className="flex items-center gap-1.5 mt-1 text-[11px] text-emerald-400 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Status: {systemStatus?.database?.status || 'connected'}</span>
              </div>
            </div>
          </div>

          {/* AI Provider */}
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs mb-3">
              <span className="text-slate-400 font-semibold">AI Intelligence Engine</span>
              <Cpu className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <p className="text-lg font-bold text-white tracking-tight capitalize">
                {systemStatus?.ai_provider?.provider || 'Google Gemini / OpenAI'}
              </p>
              <div className="flex items-center gap-1.5 mt-1 text-[11px] text-slate-400">
                <span className="font-mono text-[10px] text-brand-300">
                  {systemStatus?.ai_provider?.model || 'gemini-2.5-pro'}
                </span>
                <span>•</span>
                <span className={systemStatus?.ai_provider?.is_configured ? 'text-emerald-400' : 'text-slate-400'}>
                  {systemStatus?.ai_provider?.is_configured ? 'Configured' : 'Offline'}
                </span>
              </div>
            </div>
          </div>

          {/* Vector Storage */}
          <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs mb-3">
              <span className="text-slate-400 font-semibold">Vector Database</span>
              <Layers className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <p className="text-lg font-bold text-white tracking-tight capitalize">
                {systemStatus?.vector_database?.type || 'ChromaDB'}
              </p>
              <div className="flex items-center gap-1.5 mt-1 text-[11px] text-emerald-400 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="capitalize">{systemStatus?.vector_database?.status || 'ready'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Projects Analytics Cards */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <FolderKanban className="w-3.5 h-3.5 text-brand-400" />
          <span>Project Statistics</span>
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
            <span className="text-xs font-semibold text-slate-400">Total Projects</span>
            <p className="text-3xl font-extrabold text-white mt-2">{projects.length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Ready for Analysis</span>
            </span>
            <p className="text-3xl font-extrabold text-emerald-400 mt-2">{readyProjects.length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
            <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Processing / Ingesting</span>
            </span>
            <p className="text-3xl font-extrabold text-amber-400 mt-2">{pendingProjects.length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
            <span className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Failed / Issues</span>
            </span>
            <p className="text-3xl font-extrabold text-rose-400 mt-2">{failedProjects.length}</p>
          </div>
        </div>
      </div>

      {/* Recent Projects Table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-brand-400" />
            <span>Recently Added Projects</span>
          </h2>
          <Link
            to="/projects"
            className="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1"
          >
            <span>View All Projects</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {projects.length === 0 ? (
          <div className="p-10 rounded-2xl bg-slate-900/40 border border-slate-800 text-center">
            <div className="w-12 h-12 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-3">
              <FolderKanban className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-white mb-1">No Projects Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-5">
              Get started by uploading a ZIP archive or connecting a public GitHub repository.
            </p>
            <Link
              to="/projects"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Project</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-semibold">
                <tr>
                  <th className="px-5 py-3.5">Project Name</th>
                  <th className="px-5 py-3.5">Source Type</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Created Date</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {projects.slice(0, 5).map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-3.5">
                      <Link to={`/projects/${p.id}`} className="font-bold text-white hover:text-brand-400">
                        {p.name}
                      </Link>
                      {p.description && (
                        <p className="text-[11px] text-slate-400 truncate max-w-xs">{p.description}</p>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] font-semibold text-slate-300 capitalize">
                        {p.source_type === 'zip' ? (
                          <Archive className="w-3 h-3 text-brand-400" />
                        ) : p.source_type === 'git' ? (
                          <GitBranch className="w-3 h-3 text-indigo-400" />
                        ) : (
                          <HardDrive className="w-3 h-3 text-cyan-400" />
                        )}
                        <span>{p.source_type}</span>
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
                          p.status === 'READY' || p.status === 'ANALYZED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : p.status === 'UPLOADING' || p.status === 'CLONING'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
                            : p.status === 'FAILED'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">
                      {new Date(p.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/projects/${p.id}`}
                        className="inline-flex items-center gap-1 text-brand-400 hover:text-brand-300 font-semibold"
                      >
                        <span>Details</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
