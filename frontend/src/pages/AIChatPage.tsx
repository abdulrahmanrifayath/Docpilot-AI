import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Send,
  FolderKanban,
  Bot,
  User,
  Info,
  ExternalLink,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  FileCode,
  Layers,
  Database,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Boxes,
  HelpCircle,
  Copy,
  Check,
  Compass,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import {
  fetchChatHistory,
  sendChatMessage,
  clearChatHistory,
} from '../api/client';
import { ChatMessage, ChatCitation } from '../types';

export const AIChatPage: React.FC = () => {
  const { activeProject, projects, setActiveProject } = useProjects();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isFetchingHistory, setIsFetchingHistory] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Suggested Prompts
  const SUGGESTED_QUESTIONS = [
    { text: 'Explain authentication.', label: 'Authentication', icon: ShieldAlert },
    { text: 'How does login work?', label: 'Login Flow', icon: RefreshCw },
    { text: 'Which APIs use the UserService?', label: 'API Usage', icon: Layers },
    { text: 'Where is payment processing implemented?', label: 'Payment Code', icon: FileCode },
    { text: 'What happens when an order is created?', label: 'Order Lifecycle', icon: Boxes },
    { text: 'Explain the project architecture.', label: 'Architecture', icon: Compass },
  ];

  // Auto-scroll to bottom of conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load project chat history strictly for the active project
  useEffect(() => {
    let isCancelled = false;

    if (!activeProject?.id) {
      setMessages([]);
      return;
    }

    const loadHistory = async () => {
      setIsFetchingHistory(true);
      setErrorMsg(null);
      try {
        const history = await fetchChatHistory(activeProject.id);
        if (!isCancelled) {
          setMessages(history);
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error('Failed to load chat history:', err);
          setErrorMsg('Failed to load conversation history for this project.');
        }
      } finally {
        if (!isCancelled) {
          setIsFetchingHistory(false);
        }
      }
    };

    loadHistory();

    return () => {
      isCancelled = true;
    };
  }, [activeProject?.id]);

  const handleSend = async (contentToSend?: string) => {
    const query = (contentToSend || inputVal).trim();
    if (!query || !activeProject || isLoading) return;

    setInputVal('');
    setErrorMsg(null);

    // Optimistically add user message
    const tempUserMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      project_id: activeProject.id,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const assistantMsg = await sendChatMessage(activeProject.id, query);
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('Chat error:', err);
      setErrorMsg(err.message || 'Failed to generate response. Please try again.');
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleClearHistory = async () => {
    if (!activeProject?.id) return;
    try {
      await clearChatHistory(activeProject.id);
      setMessages([]);
      setShowClearConfirm(false);
    } catch (err: any) {
      console.error('Failed to clear history:', err);
      setErrorMsg('Failed to clear conversation history.');
    }
  };

  const toggleCitations = (messageId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const renderConfidenceBadge = (confidence?: string | null) => {
    if (!confidence) return null;
    const isHigh = confidence.toLowerCase().includes('high');
    const isLow = confidence.toLowerCase().includes('low') || confidence.toLowerCase().includes('insufficient');

    let badgeClass = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    if (isHigh) {
      badgeClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    } else if (isLow) {
      badgeClass = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }

    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${badgeClass}`}
      >
        {isHigh ? (
          <CheckCircle2 className="w-3 h-3 shrink-0" />
        ) : isLow ? (
          <AlertTriangle className="w-3 h-3 shrink-0" />
        ) : (
          <Info className="w-3 h-3 shrink-0" />
        )}
        <span>{confidence}</span>
      </span>
    );
  };

  const renderIntentBadge = (intent?: string | null) => {
    if (!intent || intent === 'GENERAL_QA') return null;
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-brand-500/10 text-brand-400 border border-brand-500/20 text-[10px] font-semibold uppercase tracking-wider">
        <Sparkles className="w-2.5 h-2.5" />
        <span>{intent.replace(/_/g, ' ')}</span>
      </span>
    );
  };

  const getCitationTypeBadge = (type: string) => {
    const t = type.toLowerCase();
    switch (t) {
      case 'api':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'model':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'class':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'function':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'sequence':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'doc':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Select an analyzed repository project to interact with the repository-aware assistant.
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
    <div className="space-y-3 max-w-5xl mx-auto h-[calc(100vh-7.5rem)] flex flex-col">
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 p-0.5 shadow-lg shadow-brand-600/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center text-brand-400">
              <Bot className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">Repository-Aware AI Assistant</h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Phase 12 Live
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Grounded code Q&A, AST entities, sequence flows & vector knowledge retrieval
            </p>
          </div>
        </div>

        {/* Project Switcher & Actions */}
        <div className="flex items-center gap-2">
          {/* Project Switcher Dropdown */}
          <div className="relative">
            <select
              value={activeProject.id}
              onChange={(e) => {
                const target = projects.find((p) => p.id === e.target.value);
                if (target) setActiveProject(target);
              }}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium text-slate-200 focus:outline-none focus:border-brand-500 cursor-pointer transition-colors"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  📁 {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Clear History Button */}
          {messages.length > 0 && (
            <button
              onClick={() => setShowClearConfirm(true)}
              title="Clear conversation history"
              className="p-2 rounded-xl bg-slate-900 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 text-slate-400 hover:text-rose-400 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          {/* Link to Project Codebase Details */}
          <Link
            to={`/projects/${activeProject.id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium transition-colors border border-slate-700"
          >
            <span>Explore Code</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Clear Confirmation Modal */}
      {showClearConfirm && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between shrink-0 animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>Are you sure you want to clear chat history for <strong>{activeProject.name}</strong>?</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClearHistory}
              className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[11px] transition-colors"
            >
              Confirm Clear
            </button>
            <button
              onClick={() => setShowClearConfirm(false)}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-[11px] underline hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Stream Container */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-md">
        {isFetchingHistory ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3">
            <RefreshCw className="w-6 h-6 animate-spin text-brand-400" />
            <p className="text-xs">Loading verified conversation history for {activeProject.name}...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-[340px] text-center p-6 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center shadow-inner">
              <Bot className="w-8 h-8" />
            </div>
            <div className="max-w-md">
              <h2 className="text-base font-bold text-white mb-1">
                Ask anything about {activeProject.name}
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Answers are grounded in static AST analysis, API routes, database schemas, sequence flows, and project vector embeddings.
              </p>
            </div>

            {/* Suggested Question Pills */}
            <div className="w-full max-w-2xl pt-2">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5">
                Suggested questions for this repository
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {SUGGESTED_QUESTIONS.map((q, idx) => {
                  const Icon = q.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(q.text)}
                      className="group p-3 rounded-xl bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 hover:border-brand-500/40 transition-all flex items-start gap-3 shadow-sm hover:shadow-brand-500/5 text-left"
                    >
                      <div className="w-7 h-7 rounded-lg bg-slate-800 group-hover:bg-brand-500/10 text-slate-400 group-hover:text-brand-400 border border-slate-700/60 group-hover:border-brand-500/30 flex items-center justify-center shrink-0 transition-colors">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-semibold text-white group-hover:text-brand-300 transition-colors">
                          {q.label}
                        </div>
                        <div className="text-[10px] text-slate-400 truncate">
                          "{q.text}"
                        </div>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-brand-400 shrink-0 self-center transition-colors" />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          messages.map((m) => {
            const isUser = m.role === 'user';
            const citations = m.sources || [];
            const isExpanded = !!expandedCitations[m.id];

            return (
              <div
                key={m.id}
                className={`flex items-start gap-3 max-w-3xl ${
                  isUser ? 'ml-auto flex-row-reverse' : ''
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-md ${
                    isUser
                      ? 'bg-gradient-to-tr from-brand-600 to-indigo-600 text-white'
                      : 'bg-slate-900 border border-slate-700/80 text-brand-400'
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className="flex-1 space-y-2">
                  <div
                    className={`p-4 rounded-2xl text-xs leading-relaxed space-y-2.5 ${
                      isUser
                        ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
                        : 'bg-slate-900/95 border border-slate-800 text-slate-200 shadow-sm'
                    }`}
                  >
                    {/* Header info for Assistant response */}
                    {!isUser && (
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-[11px]">DocPilot AI</span>
                          {renderIntentBadge(m.intent)}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {renderConfidenceBadge(m.confidence)}
                          <button
                            onClick={() => copyToClipboard(m.content, m.id)}
                            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                            title="Copy response"
                          >
                            {copiedId === m.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Verified Components Chips */}
                    {!isUser && m.relevant_components && m.relevant_components.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {m.relevant_components.map((comp, cIdx) => (
                          <span
                            key={cIdx}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800/90 text-slate-300 border border-slate-700/70 text-[10px] font-mono"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{comp}</span>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Formatted Content */}
                    <div className="prose prose-invert prose-xs max-w-none space-y-2 whitespace-pre-wrap font-sans">
                      {m.content}
                    </div>

                    {/* Timestamp */}
                    <div
                      className={`text-[10px] pt-1 ${
                        isUser ? 'text-brand-200/80 text-right' : 'text-slate-500 text-left'
                      }`}
                    >
                      {m.created_at
                        ? new Date(m.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Just now'}
                    </div>
                  </div>

                  {/* Expandable Citations & Code References */}
                  {!isUser && citations.length > 0 && (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden">
                      <button
                        onClick={() => toggleCitations(m.id)}
                        className="w-full px-3 py-2 flex items-center justify-between text-[11px] font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <FileCode className="w-3.5 h-3.5 text-brand-400" />
                          <span>
                            {citations.length} Grounded Source Reference{citations.length > 1 ? 's' : ''}
                          </span>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="p-3 border-t border-slate-800/80 space-y-2 divide-y divide-slate-800/40">
                          {citations.map((cite, cIdx) => (
                            <div key={cIdx} className="pt-2 first:pt-0 space-y-1">
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 truncate">
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase border ${getCitationTypeBadge(
                                      cite.type
                                    )}`}
                                  >
                                    {cite.type}
                                  </span>
                                  <span className="font-semibold text-white text-[11px] truncate">
                                    {cite.title}
                                  </span>
                                </div>
                                {cite.relevance !== undefined && (
                                  <span className="text-[10px] text-slate-500 font-mono shrink-0">
                                    Score: {(cite.relevance * 100).toFixed(0)}%
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                                <span className="text-brand-400">{cite.file}</span>
                                <span>:</span>
                                <span className="text-slate-500">L{cite.lines}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Loading State Skeleton */}
        {isLoading && (
          <div className="flex items-start gap-3 max-w-2xl">
            <div className="w-8 h-8 rounded-xl bg-slate-900 border border-brand-500/30 text-brand-400 flex items-center justify-center shrink-0 shadow-lg shadow-brand-500/10 animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-xs text-slate-300 space-y-2 flex-1 shadow-sm">
              <div className="flex items-center gap-2 text-brand-400 font-semibold text-[11px]">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>DocPilot is analyzing repository knowledge & retrieving grounded sources...</span>
              </div>
              <div className="space-y-1.5 pt-1">
                <div className="h-2 rounded bg-slate-800 animate-pulse w-3/4"></div>
                <div className="h-2 rounded bg-slate-800 animate-pulse w-5/6"></div>
                <div className="h-2 rounded bg-slate-800 animate-pulse w-2/3"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts Pills (Quick access above input) */}
      {messages.length > 0 && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 shrink-0 scrollbar-none text-[11px]">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1 mr-1">
            <Sparkles className="w-3 h-3 text-brand-400" />
            <span>Pills:</span>
          </span>
          {SUGGESTED_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q.text)}
              disabled={isLoading}
              className="px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 hover:border-brand-500/40 text-[10px] whitespace-nowrap transition-all shrink-0"
            >
              {q.text}
            </button>
          ))}
        </div>
      )}

      {/* Fixed Bottom Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="shrink-0 flex items-center gap-2 relative"
      >
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            placeholder={`Ask anything about ${activeProject.name} (e.g. "Explain authentication", "Where is payment implemented?")...`}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            disabled={isLoading}
            className="w-full pl-4 pr-10 py-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors shadow-inner disabled:opacity-60"
          />
        </div>

        <button
          type="submit"
          disabled={!inputVal.trim() || isLoading}
          className="p-3 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-md shadow-brand-600/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </form>

      {/* Grounded Evidence Footer Disclaimer */}
      <div className="flex items-center justify-between text-[10px] text-slate-500 px-1 shrink-0">
        <div className="flex items-center gap-1.5">
          <ShieldAlert className="w-3 h-3 text-emerald-400" />
          <span>Grounded strictly in repository AST, dependencies, APIs, schemas & sequence flows.</span>
        </div>
        <span>Never invents unverified code knowledge</span>
      </div>
    </div>
  );
};
