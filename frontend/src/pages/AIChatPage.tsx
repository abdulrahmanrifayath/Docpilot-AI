import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Send,
  FolderKanban,
  Bot,
  User,
  Info,
  ExternalLink,
  BookOpen,
  Code2,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';

export const AIChatPage: React.FC = () => {
  const { activeProject } = useProjects();
  const [messages, setMessages] = useState<
    Array<{ id: string; role: 'user' | 'assistant'; content: string; time: string }>
  >([
    {
      id: '1',
      role: 'assistant',
      content:
        'Hello! I am DocPilot AI. Once code analysis and vector indexing are executed in Phase 3 & Phase 5, you can ask me anything about the codebase: architecture patterns, endpoint routes, database schemas, or debugging advice.',
      time: 'Just now',
    },
  ]);
  const [inputVal, setInputVal] = useState<string>('');

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userMsg = {
      id: Date.now().toString(),
      role: 'user' as const,
      content: inputVal.trim(),
      time: 'Just now',
    };

    setMessages((prev) => [
      ...prev,
      userMsg,
      {
        id: (Date.now() + 1).toString(),
        role: 'assistant' as const,
        content: `I received your query about "${inputVal.trim()}". In Phase 5, this will perform semantic hybrid vector search across the AST index of "${activeProject?.name || 'the project'}" and return exact file citations and line numbers.`,
        time: 'Just now',
      },
    ]);

    setInputVal('');
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Please select a project to chat with the DocPilot AI assistant about its source code.
        </p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
        >
          <FolderKanban className="w-4 h-4" />
          <span>Select Project</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-5xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">AI Codebase Assistant</h1>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {activeProject.name}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Interactive conversational intelligence grounded in repository code
            </p>
          </div>
        </div>

        <Link
          to={`/projects/${activeProject.id}`}
          className="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1"
        >
          <span>Repository Files</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Notice */}
      <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs flex items-center gap-2 shrink-0">
        <Info className="w-4 h-4 shrink-0 text-indigo-400" />
        <span>
          Repository sandbox isolation active. Full RAG semantic search & citation retrieval will connect in Phase 5.
        </span>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-3 max-w-2xl ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          >
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                m.role === 'user'
                  ? 'bg-brand-600 text-white'
                  : 'bg-slate-800 text-brand-400 border border-slate-700'
              }`}
            >
              {m.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div
              className={`p-3.5 rounded-2xl text-xs leading-relaxed ${
                m.role === 'user'
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
                  : 'bg-slate-900 border border-slate-800 text-slate-200'
              }`}
            >
              <p>{m.content}</p>
              <span className="text-[10px] opacity-60 block mt-1 text-right">{m.time}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} className="shrink-0 flex items-center gap-2">
        <input
          type="text"
          placeholder={`Ask anything about ${activeProject.name}...`}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          className="flex-1 px-4 py-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
        />
        <button
          type="submit"
          className="p-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-600/25 transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
