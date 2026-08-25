import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  BookOpen,
  GitBranch,
  Bot,
  Settings,
  Sparkles,
  Layers,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', path: '/projects', icon: FolderGit2 },
  { name: 'Documentation', path: '/documentation', icon: BookOpen },
  { name: 'Architecture', path: '/diagrams', icon: GitBranch },
  { name: 'AI Assistant', path: '/chat', icon: Bot },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 border-r border-slate-800/80 bg-[#0B0F17] flex flex-col justify-between shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div>
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800/80">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-glow text-white font-bold">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-tight flex items-center gap-1.5">
              <span>DocPilot AI</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Intelligent Documentation</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-600/20 to-indigo-600/5 text-white border border-indigo-500/30 shadow-sm font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={`w-4 h-4 transition-colors ${
                        isActive ? 'text-indigo-400' : 'text-slate-500'
                      }`}
                    />
                    <span>{item.name}</span>
                    {isActive && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-glow" />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Info / Version info */}
      <div className="p-4 border-t border-slate-800/80">
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Developer Knowledge</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
            Repository-aware code analysis, graph modeling, and AI diagrams.
          </p>
        </div>
      </div>
    </aside>
  );
};
