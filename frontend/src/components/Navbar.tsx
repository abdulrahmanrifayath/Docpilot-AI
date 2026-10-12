import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Sparkles, Settings as SettingsIcon, Layers, Github } from 'lucide-react';

interface NavbarProps {
  onToggleChat?: () => void;
  isChatOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleChat, isChatOpen }) => {
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#0b0f19]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-600 via-indigo-600 to-cyan-500 p-0.5 shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow">
            <div className="w-full h-full bg-[#0b0f19] rounded-[10px] flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-brand-400 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">DocPilot</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/30">AI</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase hidden sm:block">Intelligent Software Documentation</p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            to="/"
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
              location.pathname === '/'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Repositories</span>
          </Link>

          <Link
            to="/settings"
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
              location.pathname === '/settings'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <SettingsIcon className="w-4 h-4" />
            <span>Settings</span>
          </Link>

          {/* AI Chat Drawer Toggle */}
          {onToggleChat && (
            <button
              onClick={onToggleChat}
              className={`ml-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border ${
                isChatOpen
                  ? 'bg-brand-600 text-white border-brand-500 shadow-md shadow-brand-500/25'
                  : 'bg-brand-500/10 text-brand-300 border-brand-500/30 hover:bg-brand-500/20'
              }`}
            >
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>AI Assistant</span>
            </button>
          )}

          <a
            href="https://github.com/abdulrahmanrifayath/Docpilot-AI"
            target="_blank"
            rel="noreferrer"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors ml-1"
            title="GitHub Repository"
          >
            <Github className="w-5 h-5" />
          </a>
        </nav>
      </div>
    </header>
  );
};
