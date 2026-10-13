import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  Workflow,
  Sparkles,
  Settings as SettingsIcon,
  BookOpen,
  ChevronDown,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Github,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { projects, activeProject, setActiveProject, systemStatus } = useProjects();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Projects', path: '/projects', icon: FolderKanban },
    { name: 'Documentation', path: '/documentation', icon: FileText },
    { name: 'Architecture', path: '/architecture', icon: Workflow },
    { name: 'AI Assistant', path: '/chat', icon: Sparkles },
    { name: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  const isOperational = systemStatus?.status === 'operational';

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-[#0f172a] border-r border-slate-800 flex flex-col shrink-0 z-30">
        {/* Brand */}
        <div className="h-16 px-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-600 via-indigo-600 to-cyan-500 p-0.5 shadow-md shadow-brand-500/20">
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
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Dev Intelligence</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.path ||
              (item.path === '/projects' && location.pathname.startsWith('/projects'));

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/25'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Bottom System Status Mini Card */}
        <div className="p-4 border-t border-slate-800/80">
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isOperational ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
              <span className="text-slate-300 font-medium text-[11px]">
                {isOperational ? 'System Ready' : 'Connecting...'}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">v1.0.0</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Area */}
        <header className="h-16 px-6 border-b border-slate-800 bg-[#0b0f19]/90 backdrop-blur-md flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-bold text-white tracking-tight hidden sm:block">
              DocPilot AI Platform
            </h2>

            {/* Current Project Selector Dropdown */}
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
              <span className="text-slate-400 text-[11px] font-semibold">Active Project:</span>
              <div className="relative">
                <select
                  value={activeProject?.id || ''}
                  onChange={(e) => {
                    const sel = projects.find((p) => p.id === e.target.value) || null;
                    setActiveProject(sel);
                  }}
                  className="bg-transparent text-white font-semibold text-xs pr-6 focus:outline-none cursor-pointer"
                >
                  {projects.length === 0 && <option value="">No Projects Created</option>}
                  {projects.map((p) => (
                    <option key={p.id} value={p.id} className="bg-slate-900 text-white">
                      {p.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 pointer-events-none absolute right-0 top-1/2 -translate-y-1/2" />
              </div>
            </div>
          </div>

          {/* Right Header Status Area */}
          <div className="flex items-center gap-3">
            {/* System status badge */}
            <div
              className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 border ${
                isOperational
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">
                {isOperational ? 'All Systems Operational' : 'System Degraded'}
              </span>
            </div>

            <a
              href="https://github.com/abdulrahmanrifayath/Docpilot-AI"
              target="_blank"
              rel="noreferrer"
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="GitHub Repository"
            >
              <Github className="w-4 h-4" />
            </a>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
};
