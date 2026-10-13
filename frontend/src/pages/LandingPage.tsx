import React from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  ArrowRight,
  FolderKanban,
  FileCode2,
  Workflow,
  Sparkles,
  ShieldCheck,
  HardDrive,
  Cpu,
  Layers,
  CheckCircle2,
  Activity,
  Terminal,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

export const LandingPage: React.FC = () => {
  const { systemStatus, projects } = useProjects();
  const isOperational = systemStatus?.status === 'operational';

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col selection:bg-brand-500/30">
      {/* Top Navigation */}
      <header className="h-16 border-b border-slate-800 bg-[#0f172a]/70 backdrop-blur-md px-6 md:px-12 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-brand-500 to-cyan-400 p-0.5 shadow-md shadow-brand-500/20">
            <div className="w-full h-full bg-[#0b0f19] rounded-[10px] flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-brand-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base text-white tracking-tight">DocPilot</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                AI
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div
            className={`hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold border ${
              isOperational
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{isOperational ? 'Platform Operational' : 'Connecting to Core API...'}</span>
          </div>

          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
          >
            <span>Open Console</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="relative pt-20 pb-24 px-6 md:px-12 overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-brand-600/15 blur-[120px] rounded-full pointer-events-none" />

          <div className="max-w-5xl mx-auto text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/80 text-xs font-semibold text-slate-300 mb-8 backdrop-blur-sm">
              <Sparkles className="w-3.5 h-3.5 text-brand-400" />
              <span>DocPilot AI – Intelligent Software Documentation Platform</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
              Understand Any Codebase.{' '}
              <span className="bg-gradient-to-r from-brand-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
                Instantly & Securely.
              </span>
            </h1>

            <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-400 mb-10 leading-relaxed">
              DocPilot AI acts as an AI engineer on your team. Upload a ZIP or link a public GitHub repository to
              automatically extract project structure, explore file trees, and generate comprehensive documentation.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/projects"
                className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm shadow-lg shadow-brand-600/30 transition-all"
              >
                <FolderKanban className="w-4 h-4" />
                <span>Create New Project</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Link>
              <Link
                to="/dashboard"
                className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-sm transition-all"
              >
                <span>View Dashboard</span>
              </Link>
            </div>

            {/* Quick Metrics Bar */}
            <div className="mt-14 max-w-3xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm text-left">
              <div className="p-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Active Projects</span>
                <p className="text-2xl font-bold text-white mt-1">{projects.length}</p>
              </div>
              <div className="p-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Security Sandbox</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-5 h-5 inline" />
                  <span>Isolated</span>
                </p>
              </div>
              <div className="p-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Backend Database</span>
                <p className="text-xl font-bold text-white mt-1 capitalize">
                  {systemStatus?.database?.type || 'SQLite'}
                </p>
              </div>
              <div className="p-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">AI Provider</span>
                <p className="text-xl font-bold text-brand-300 mt-1 capitalize">
                  {systemStatus?.ai_provider?.provider || 'Configured'}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="py-16 px-6 md:px-12 border-t border-slate-800/80 bg-[#0d1322]">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Enterprise-Grade Repository Foundation
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-2">
                Designed for high performance, zero-execution security, and deep software analysis
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1 */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-4">
                  <HardDrive className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">ZIP & Git Repository Ingestion</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Upload project ZIP archives or clone public GitHub repositories. Automatic extraction filters out heavy artifacts like node_modules and .venv.
                </p>
              </div>

              {/* Card 2 */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Zip-Slip & Path Defense</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Strict path traversal verification protects your infrastructure. Uploaded source code is never executed, only statically inspected.
                </p>
              </div>

              {/* Card 3 */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
                  <Terminal className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Hierarchical File Tree Browser</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Instantly browse project file trees with size calculation, directory isolation, and file format intelligence.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="py-6 px-6 md:px-12 border-t border-slate-800 text-center text-xs text-slate-500">
        DocPilot AI Platform • Phase 1 & Phase 2 Foundation Ready • Developer Intelligence
      </footer>
    </div>
  );
};
