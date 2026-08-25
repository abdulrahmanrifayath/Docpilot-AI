import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { useSystem } from '../context/SystemContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import {
  Bot,
  Send,
  Cpu,
  User,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export const AIChatPage: React.FC = () => {
  const { activeProject } = useProject();
  const { status } = useSystem();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `Hello! I am DocPilot AI. Ask me anything about ${
        activeProject ? activeProject.name : 'your codebase'
      }, including architecture flow, data models, or API endpoints.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');

  const samplePrompts = [
    'How is authentication handled in this project?',
    'What database models are defined and how do they relate?',
    'Explain the request lifecycle for the primary API endpoints',
    'Generate a developer onboarding summary for a junior engineer',
  ];

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const aiMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'assistant',
      text: status?.ai_provider.configured
        ? `In Phase 4, DocPilot retrieves indexed vector chunks and knowledge graph nodes from ChromaDB to answer with grounded repository citations.`
        : `AI Assistant is in Phase 1 foundation state. Please configure OPENAI_API_KEY in backend/.env to activate full LLM chat retrieval in Phase 4.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setInput('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Bot className="w-6 h-6 text-violet-400" />
            Repository-Aware AI Assistant
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Grounded AI chat with source code citations, dependency awareness, and semantic vector retrieval.
          </p>
        </div>

        {activeProject && (
          <Badge variant="primary" size="md">
            Context: {activeProject.name}
          </Badge>
        )}
      </div>

      {/* Chat Container */}
      <Card className="p-0 border-slate-800 flex flex-col h-[580px] overflow-hidden">
        {/* Chat Header */}
        <div className="px-6 py-3.5 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs">
            <Cpu className="w-4 h-4 text-violet-400" />
            <span className="text-slate-300 font-medium">Model:</span>
            <span className="font-mono text-indigo-300">{status?.ai_provider.model || 'gpt-4o-mini'}</span>
          </div>
          <Badge variant={status?.ai_provider.configured ? 'success' : 'warning'} size="sm" dot>
            {status?.ai_provider.configured ? 'Provider Ready' : 'API Key Required'}
          </Badge>
        </div>

        {/* Messages List */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.sender === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-xl p-4 rounded-2xl text-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-sm'
                }`}
              >
                <p>{msg.text}</p>
                <span
                  className={`block text-[10px] mt-2 ${
                    msg.sender === 'user' ? 'text-indigo-200 text-right' : 'text-slate-500'
                  }`}
                >
                  {msg.timestamp}
                </span>
              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300 shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Suggested Queries */}
        <div className="px-6 py-2 bg-slate-900/40 border-t border-slate-800/80 flex items-center gap-2 overflow-x-auto">
          <span className="text-[10px] text-slate-500 font-mono uppercase whitespace-nowrap">
            Suggestions:
          </span>
          {samplePrompts.slice(0, 2).map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-900/90 border-t border-slate-800 flex items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            placeholder="Ask a question about components, dependencies, or database schemas..."
            className="flex-1 px-4 py-2.5 text-xs bg-slate-950 border border-slate-700/80 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
          <Button
            variant="primary"
            size="md"
            onClick={() => handleSend()}
            disabled={!input.trim()}
            rightIcon={<Send className="w-4 h-4" />}
          >
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
};
