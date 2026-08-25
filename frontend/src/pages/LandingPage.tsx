import React from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Sparkles,
  ArrowRight,
  GitBranch,
  FileCode2,
  Bot,
} from 'lucide-react';
import { Button } from '../components/common/Button';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col justify-between selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top Navbar */}
      <nav className="border-b border-slate-800/80 bg-[#0B0F17]/80 backdrop-blur-md px-6 md:px-12 h-16 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-glow text-white font-bold">
            <Layers className="w-5 h-5" />
          </div>
          <span className="font-bold text-base text-white tracking-tight">DocPilot AI</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/dashboard">
            <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Open Platform
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative px-6 py-20 md:py-28 max-w-6xl mx-auto text-center">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-indigo-600/15 blur-[120px] rounded-full pointer-events-none -z-10" />

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Transform Repositories into Living Knowledge</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight md:leading-tight">
          Intelligent Software Documentation & <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-cyan-300 to-indigo-300">Architecture Insights</span>
        </h1>

        <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto mt-6 leading-relaxed">
          DocPilot AI parses codebases with AST precision, builds structured knowledge graphs, generates living architecture diagrams, and powers repository-aware AI chat.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 mt-8">
          <Link to="/dashboard">
            <Button variant="primary" size="lg" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Get Started Free
            </Button>
          </Link>
          <Link to="/projects">
            <Button variant="outline" size="lg" leftIcon={<FileCode2 className="w-4 h-4" />}>
              Browse Repositories
            </Button>
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 text-left">
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
              <FileCode2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Structured AST Code Parsing</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Incremental analysis of Python, TypeScript, and JavaScript. Extracts modules, classes, functions, and API models with high fidelity.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-4">
              <GitBranch className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Architecture & Sequence Diagrams</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Auto-generate visual component dependencies, ER diagrams, and sequence diagrams powered by Mermaid and interactive graph flow.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-4">
              <Bot className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Repository-Aware AI Assistant</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Ask deep questions about code patterns, edge cases, and call hierarchies with grounded vector embeddings and knowledge graph context.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-8 px-6 text-center text-xs text-slate-500">
        <p>DocPilot AI — Intelligent Software Documentation Platform. Built for engineering teams & architects.</p>
      </footer>
    </div>
  );
};
