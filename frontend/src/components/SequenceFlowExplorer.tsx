import React, { useState, useEffect, useMemo } from 'react';
import {
  Workflow,
  Sparkles,
  RefreshCw,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Lock,
  UserCheck,
  ShoppingCart,
  CreditCard,
  Database,
  ArrowRight,
  Server,
  Layers,
  Search,
  ExternalLink,
  ShieldCheck,
  Cpu,
  Clock,
  Info,
  ChevronRight,
  SlidersHorizontal,
} from 'lucide-react';
import { SequenceDiagramItem, SequenceStep, SequenceFlowCategory } from '../types';
import {
  fetchProjectSequences,
  generateSequences,
  regenerateProjectSequence,
} from '../api/client';
import { MermaidViewer } from './MermaidViewer';

interface SequenceFlowExplorerProps {
  projectId: string;
  projectName?: string;
  onRefreshProject?: () => void;
}

export const SequenceFlowExplorer: React.FC<SequenceFlowExplorerProps> = ({
  projectId,
  projectName,
  onRefreshProject,
}) => {
  const [sequences, setSequences] = useState<SequenceDiagramItem[]>([]);
  const [selectedSequenceId, setSelectedSequenceId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'diagram' | 'steps' | 'components'>('diagram');

  useEffect(() => {
    if (projectId) {
      loadSequences();
    }
  }, [projectId]);

  const loadSequences = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjectSequences(projectId);
      setSequences(data);
      if (data.length > 0) {
        if (!selectedSequenceId || !data.some((s) => s.id === selectedSequenceId)) {
          setSelectedSequenceId(data[0].id);
        }
      } else {
        setSelectedSequenceId(null);
      }
    } catch (err: any) {
      console.warn('Failed to load sequence flows:', err);
      setError(err?.message || 'Failed to load sequence flows');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAll = async (force: boolean = false) => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generateSequences(projectId, {
        force_regenerate: force,
      });
      setSequences(res.sequences);
      if (res.sequences.length > 0) {
        setSelectedSequenceId(res.sequences[0].id);
      }
      if (onRefreshProject) {
        onRefreshProject();
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to generate sequence diagrams');
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerate = async (sequenceId: string) => {
    setRegeneratingId(sequenceId);
    setError(null);
    try {
      const updated = await regenerateProjectSequence(projectId, sequenceId);
      setSequences((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s))
      );
    } catch (err: any) {
      setError(err?.message || 'Failed to regenerate sequence diagram');
    } finally {
      setRegeneratingId(null);
    }
  };

  // Filter sequences
  const filteredSequences = useMemo(() => {
    return sequences.filter((seq) => {
      const matchesCategory =
        selectedCategory === 'ALL' ||
        seq.flow_category.toUpperCase() === selectedCategory.toUpperCase();
      const matchesSearch =
        !searchQuery ||
        seq.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (seq.trigger_endpoint &&
          seq.trigger_endpoint.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (seq.involved_components &&
          seq.involved_components.some((c) =>
            c.toLowerCase().includes(searchQuery.toLowerCase())
          ));
      return matchesCategory && matchesSearch;
    });
  }, [sequences, selectedCategory, searchQuery]);

  // Active selected sequence
  const activeSequence = useMemo(() => {
    return (
      sequences.find((s) => s.id === selectedSequenceId) ||
      (filteredSequences.length > 0 ? filteredSequences[0] : null)
    );
  }, [sequences, selectedSequenceId, filteredSequences]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      ALL: sequences.length,
      AUTHENTICATION: 0,
      REGISTRATION: 0,
      ORDER: 0,
      PAYMENT: 0,
      DATA_MUTATION: 0,
      GENERAL_FLOW: 0,
    };
    sequences.forEach((s) => {
      const cat = s.flow_category.toUpperCase();
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [sequences]);

  const getCategoryBadge = (category: string) => {
    switch (category.toUpperCase()) {
      case 'AUTHENTICATION':
        return {
          icon: Lock,
          label: 'Auth',
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        };
      case 'REGISTRATION':
        return {
          icon: UserCheck,
          label: 'Registration',
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        };
      case 'ORDER':
        return {
          icon: ShoppingCart,
          label: 'Order',
          bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        };
      case 'PAYMENT':
        return {
          icon: CreditCard,
          label: 'Payment',
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        };
      case 'DATA_MUTATION':
        return {
          icon: Database,
          label: 'Mutation',
          bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
        };
      default:
        return {
          icon: Workflow,
          label: 'Flow',
          bg: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
        };
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.9) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
    if (conf >= 0.8) return 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10';
    if (conf >= 0.7) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
  };

  return (
    <div className="space-y-5">
      {/* Top Header Card */}
      <div className="bg-[#0f172a]/95 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <div className="w-8 h-8 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-400 flex items-center justify-center">
                <Workflow className="w-4 h-4" />
              </div>
              <h3 className="text-lg font-bold text-white tracking-tight">
                Automatic Sequence Flow Generator
              </h3>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Phase 11
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Static Analysis-Based
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl">
              Synthesizes probable execution sequences for key application flows (Authentication, Registration, Orders, Payments) using detected route handlers, function invocations, service dependencies, and database models.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => handleGenerateAll(false)}
              disabled={generating || loading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-brand-600/25 transition-all"
            >
              {generating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span>{generating ? 'Inferring Flows...' : 'Generate Sequences'}</span>
            </button>

            {sequences.length > 0 && (
              <button
                onClick={() => handleGenerateAll(true)}
                disabled={generating || loading}
                title="Force re-analysis and overwrite stored sequence diagrams"
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 transition-all"
              >
                <span>Force Regenerate All</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold text-rose-200">Sequence Engine Error: </span>
            {error}
          </div>
          <button
            onClick={() => setError(null)}
            className="text-slate-400 hover:text-white text-xs font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Category Pills & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {[
            { id: 'ALL', label: 'All Flows' },
            { id: 'AUTHENTICATION', label: 'Login & Auth' },
            { id: 'REGISTRATION', label: 'Registration' },
            { id: 'ORDER', label: 'Orders' },
            { id: 'PAYMENT', label: 'Payments' },
            { id: 'DATA_MUTATION', label: 'Mutations' },
          ].map((cat) => {
            const isSelected = selectedCategory === cat.id;
            const count = categoryCounts[cat.id] || 0;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border ${
                  isSelected
                    ? 'bg-brand-600 text-white border-brand-500 shadow-sm shadow-brand-500/25'
                    : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
                }`}
              >
                <span>{cat.label}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isSelected
                      ? 'bg-white/20 text-white'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Bar */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search flows, endpoints, components..."
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
          />
        </div>
      </div>

      {/* Main Content: Split Master-Detail Layout */}
      {loading ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-20 text-center flex flex-col items-center justify-center min-h-[460px]">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin mb-3" />
          <h4 className="text-sm font-semibold text-white">Loading Sequence Diagrams...</h4>
          <p className="text-xs text-slate-400 mt-1">
            Retrieving inferred execution flows and Mermaid models
          </p>
        </div>
      ) : sequences.length === 0 ? (
        /* Empty State */
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm p-16 text-center flex flex-col items-center justify-center min-h-[460px]">
          <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-4 shadow-lg shadow-brand-500/10">
            <Workflow className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1.5">
            No Sequence Diagrams Generated Yet
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            DocPilot AI can inspect detected backend APIs, route handlers, call dependencies, and ORM models to automatically compile probable runtime sequence flows.
          </p>
          <button
            onClick={() => handleGenerateAll(false)}
            disabled={generating}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>Generate Application Sequence Flows</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Master List: Flow Selector */}
          <div className="lg:col-span-4 space-y-2.5">
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Discovered Flows ({filteredSequences.length})
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                Click to inspect
              </span>
            </div>

            <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
              {filteredSequences.map((seq) => {
                const isSelected = seq.id === activeSequence?.id;
                const badge = getCategoryBadge(seq.flow_category);
                const BadgeIcon = badge.icon;
                const confPercent = Math.round(seq.overall_confidence * 100);

                return (
                  <button
                    key={seq.id}
                    onClick={() => setSelectedSequenceId(seq.id)}
                    className={`w-full p-3.5 rounded-2xl border text-left transition-all relative flex flex-col gap-2 ${
                      isSelected
                        ? 'bg-brand-600/15 border-brand-500/60 shadow-lg shadow-brand-500/10'
                        : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border flex items-center gap-1 shrink-0 ${badge.bg}`}
                        >
                          <BadgeIcon className="w-2.5 h-2.5" />
                          <span>{badge.label}</span>
                        </span>
                        <h4
                          className={`text-xs font-bold truncate ${
                            isSelected ? 'text-white' : 'text-slate-200'
                          }`}
                        >
                          {seq.name}
                        </h4>
                      </div>

                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 shrink-0">
                        v{seq.version}
                      </span>
                    </div>

                    {/* Trigger route */}
                    {seq.trigger_endpoint && (
                      <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300">
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                            seq.trigger_method === 'POST'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : seq.trigger_method === 'PUT'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          }`}
                        >
                          {seq.trigger_method || 'API'}
                        </span>
                        <span className="truncate">{seq.trigger_endpoint}</span>
                      </div>
                    )}

                    {/* Footer stats: components & confidence */}
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/50">
                      <span>{seq.steps?.length || 0} interaction steps</span>
                      <span
                        className={`px-1.5 py-0.2 rounded border font-semibold ${getConfidenceColor(
                          seq.overall_confidence
                        )}`}
                      >
                        {confPercent}% Probable
                      </span>
                    </div>
                  </button>
                );
              })}

              {filteredSequences.length === 0 && (
                <div className="p-8 text-center bg-slate-900/40 border border-slate-800/80 rounded-2xl">
                  <p className="text-xs text-slate-400">No matching sequence flows found</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Detail Panel: Mermaid Diagram, Timeline, Components */}
          <div className="lg:col-span-8 space-y-4">
            {activeSequence ? (
              <>
                {/* Active Flow Header & Actions */}
                <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-4 shadow-md space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-base font-bold text-white tracking-tight">
                          {activeSequence.name}
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                            getCategoryBadge(activeSequence.flow_category).bg
                          }`}
                        >
                          {getCategoryBadge(activeSequence.flow_category).label}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getConfidenceColor(
                            activeSequence.overall_confidence
                          )}`}
                        >
                          {Math.round(activeSequence.overall_confidence * 100)}% Confidence
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          v{activeSequence.version}
                        </span>
                      </div>
                      {activeSequence.description && (
                        <p className="text-xs text-slate-400">{activeSequence.description}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRegenerate(activeSequence.id)}
                        disabled={regeneratingId === activeSequence.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-semibold border border-slate-700 shadow-sm transition-all"
                      >
                        {regeneratingId === activeSequence.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        <span>{regeneratingId === activeSequence.id ? 'Regenerating...' : 'Regenerate'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Disclaimer banner for Static Analysis Inference */}
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-xs text-amber-300 flex items-start gap-2.5">
                    <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div className="space-y-0.5 text-[11px] leading-relaxed">
                      <strong className="text-amber-200">
                        {activeSequence.execution_type || 'Static analysis-based interaction flow'}:
                      </strong>{' '}
                      Probable execution sequence inferred from static AST call relationships, route handlers, and database interactions. Runtime order and behavior is static analysis-derived and not guaranteed.
                    </div>
                  </div>

                  {/* View Mode Switcher: Diagram vs Steps vs Components */}
                  <div className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                    <button
                      onClick={() => setViewMode('diagram')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                        viewMode === 'diagram'
                          ? 'bg-brand-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      Sequence Diagram
                    </button>
                    <button
                      onClick={() => setViewMode('steps')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                        viewMode === 'steps'
                          ? 'bg-brand-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      <span>Execution Timeline</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 font-mono">
                        {activeSequence.steps?.length || 0}
                      </span>
                    </button>
                    <button
                      onClick={() => setViewMode('components')}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                        viewMode === 'components'
                          ? 'bg-brand-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      <span>Involved Components</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800 font-mono">
                        {activeSequence.involved_components?.length || 0}
                      </span>
                    </button>
                  </div>
                </div>

                {/* View 1: Mermaid Sequence Diagram */}
                {viewMode === 'diagram' && (
                  <div className="space-y-3">
                    <MermaidViewer
                      code={activeSequence.mermaid_code}
                      title={activeSequence.name}
                      description={activeSequence.description || undefined}
                      version={activeSequence.version}
                      onRegenerate={() => handleRegenerate(activeSequence.id)}
                      isRegenerating={regeneratingId === activeSequence.id}
                    />

                    {/* Quick chips of involved components */}
                    <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-brand-400" />
                          Participants ({activeSequence.involved_components?.length || 0}):
                        </span>
                        {activeSequence.involved_components?.map((comp, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[11px] font-mono text-slate-300"
                          >
                            {comp}
                          </span>
                        ))}
                      </div>

                      <div className="text-[11px] font-mono text-slate-400 shrink-0">
                        Trigger: <strong className="text-white">{activeSequence.trigger_method} {activeSequence.trigger_endpoint}</strong>
                      </div>
                    </div>
                  </div>
                )}

                {/* View 2: Step-by-Step Execution Timeline Table */}
                {viewMode === 'steps' && (
                  <div className="bg-[#0f172a] border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
                    <div className="px-5 py-3.5 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-brand-400" />
                        <span>Inferred Step-by-Step Interaction Sequence</span>
                      </h4>
                      <span className="text-[11px] text-slate-400">
                        {activeSequence.steps?.length || 0} interaction steps
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 bg-slate-900/50 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                            <th className="py-3 px-4">#</th>
                            <th className="py-3 px-4">From</th>
                            <th className="py-3 px-4">To</th>
                            <th className="py-3 px-4">Action / Call</th>
                            <th className="py-3 px-4">Return</th>
                            <th className="py-3 px-4">Type</th>
                            <th className="py-3 px-4 text-right">Confidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                          {activeSequence.steps?.map((step: SequenceStep) => {
                            const stepConf = Math.round((step.confidence || 0.85) * 100);
                            return (
                              <tr
                                key={step.step_number}
                                className="hover:bg-slate-850/40 transition-colors"
                              >
                                <td className="py-3 px-4 text-slate-400 font-bold">
                                  {step.step_number}
                                </td>
                                <td className="py-3 px-4 text-cyan-300 font-semibold">
                                  {step.source}
                                </td>
                                <td className="py-3 px-4 text-purple-300 font-semibold">
                                  {step.target}
                                </td>
                                <td className="py-3 px-4 text-slate-200 font-sans">
                                  {step.action}
                                </td>
                                <td className="py-3 px-4 text-slate-400 font-sans">
                                  {step.return_action || '—'}
                                </td>
                                <td className="py-3 px-4">
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                    {step.step_type}
                                  </span>
                                </td>
                                <td className="py-3 px-4 text-right">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getConfidenceColor(
                                      step.confidence
                                    )}`}
                                  >
                                    {stepConf}%
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* View 3: Involved Components Breakdown */}
                {viewMode === 'components' && (
                  <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
                    <div className="border-b border-slate-800 pb-3">
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        <Layers className="w-4 h-4 text-brand-400" />
                        <span>Involved Application Architecture Components</span>
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Components participating in the {activeSequence.name} execution path.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {activeSequence.involved_components?.map((componentName, idx) => {
                        const isDb =
                          componentName.toLowerCase().includes('db') ||
                          componentName.toLowerCase().includes('database') ||
                          componentName.toLowerCase().includes('model');
                        const isApi =
                          componentName.toLowerCase().includes('api') ||
                          componentName.toLowerCase().includes('router') ||
                          componentName.toLowerCase().includes('endpoint');
                        const isService =
                          componentName.toLowerCase().includes('service') ||
                          componentName.toLowerCase().includes('auth') ||
                          componentName.toLowerCase().includes('handler');
                        const isClient =
                          componentName.toLowerCase().includes('user') ||
                          componentName.toLowerCase().includes('client') ||
                          componentName.toLowerCase().includes('frontend');

                        return (
                          <div
                            key={idx}
                            className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 flex items-start gap-3"
                          >
                            <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                              {isDb ? (
                                <Database className="w-4 h-4 text-amber-400" />
                              ) : isApi ? (
                                <Server className="w-4 h-4 text-blue-400" />
                              ) : isService ? (
                                <Cpu className="w-4 h-4 text-purple-400" />
                              ) : (
                                <Workflow className="w-4 h-4 text-emerald-400" />
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-2">
                                <h5 className="text-xs font-bold text-white truncate">
                                  {componentName}
                                </h5>
                                <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                                  {isDb
                                    ? 'Database'
                                    : isApi
                                    ? 'API'
                                    : isService
                                    ? 'Service'
                                    : isClient
                                    ? 'Client'
                                    : 'Subsystem'}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                                Participates as a verified caller/callee in the probable execution sequence.
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center">
                <p className="text-xs text-slate-400">Select a sequence flow from the list to view its diagram</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
