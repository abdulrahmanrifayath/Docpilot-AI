import React, { useState, useEffect, useMemo } from 'react';
import {
  Code2,
  Lock,
  Unlock,
  Search,
  Filter,
  RefreshCw,
  Layers,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Sparkles,
  Server,
  FileCode,
  ShieldAlert,
  ArrowRight,
  Boxes,
  Database,
  Cpu,
  Hash,
} from 'lucide-react';
import { APIEndpoint, APIEndpointDetail, APIAnalysisResponse } from '../types';
import { analyzeProjectApis, fetchProjectApis, fetchProjectApiDetail } from '../api/client';

interface APIExplorerProps {
  projectId: string;
  projectName?: string;
  onRefreshProject?: () => void;
}

export const APIExplorer: React.FC<APIExplorerProps> = ({
  projectId,
  projectName,
  onRefreshProject,
}) => {
  const [endpoints, setEndpoints] = useState<APIEndpoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [selectedApiId, setSelectedApiId] = useState<string | null>(null);
  const [apiDetail, setApiDetail] = useState<APIEndpointDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedMethod, setSelectedMethod] = useState<string>('ALL');
  const [selectedTag, setSelectedTag] = useState<string>('ALL');
  const [authFilter, setAuthFilter] = useState<'ALL' | 'AUTH' | 'PUBLIC'>('ALL');
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [expandedEndpoints, setExpandedEndpoints] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (projectId) {
      loadApis();
    }
  }, [projectId]);

  const loadApis = async () => {
    setLoading(true);
    try {
      const data = await fetchProjectApis(projectId);
      setEndpoints(data);
      if (data.length > 0 && !selectedApiId) {
        // Expand first endpoint by default
        setExpandedEndpoints(new Set([data[0].id]));
      }
    } catch (err) {
      console.warn('Failed to load APIs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const res: APIAnalysisResponse = await analyzeProjectApis(projectId);
      setEndpoints(res.endpoints || []);
      if (res.endpoints?.length > 0) {
        setExpandedEndpoints(new Set([res.endpoints[0].id]));
      }
      if (onRefreshProject) {
        onRefreshProject();
      }
    } catch (err: any) {
      alert(`API Analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleToggleExpand = async (ep: APIEndpoint) => {
    const next = new Set(expandedEndpoints);
    if (next.has(ep.id)) {
      next.delete(ep.id);
    } else {
      next.add(ep.id);
      // Fetch rich detail with related components if not already selected
      fetchDetail(ep.id);
    }
    setExpandedEndpoints(next);
  };

  const fetchDetail = async (apiId: string) => {
    setSelectedApiId(apiId);
    setLoadingDetail(true);
    try {
      const detail = await fetchProjectApiDetail(projectId, apiId);
      setApiDetail(detail);
    } catch (err) {
      console.warn('Failed to load endpoint detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPath(text);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  // Distinct tags list
  const allTags = useMemo(() => {
    const tagsSet = new Set<string>();
    endpoints.forEach((ep) => {
      (ep.tags || []).forEach((t) => tagsSet.add(t));
    });
    return Array.from(tagsSet).sort();
  }, [endpoints]);

  // Method distribution stats
  const methodStats = useMemo(() => {
    const counts: Record<string, number> = {};
    endpoints.forEach((ep) => {
      const m = ep.method.toUpperCase();
      counts[m] = (counts[m] || 0) + 1;
    });
    return counts;
  }, [endpoints]);

  // Filtered endpoints
  const filteredEndpoints = useMemo(() => {
    return endpoints.filter((ep) => {
      // Method filter
      if (selectedMethod !== 'ALL' && ep.method.toUpperCase() !== selectedMethod) {
        return false;
      }
      // Tag filter
      if (selectedTag !== 'ALL' && !(ep.tags || []).includes(selectedTag)) {
        return false;
      }
      // Auth filter
      if (authFilter === 'AUTH' && !ep.authentication_required) return false;
      if (authFilter === 'PUBLIC' && ep.authentication_required) return false;

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesPath = ep.path.toLowerCase().includes(q);
        const matchesHandler = ep.handler_name.toLowerCase().includes(q);
        const matchesFile = ep.file_path.toLowerCase().includes(q);
        const matchesTag = (ep.tags || []).some((t) => t.toLowerCase().includes(q));
        if (!matchesPath && !matchesHandler && !matchesFile && !matchesTag) {
          return false;
        }
      }

      return true;
    });
  }, [endpoints, selectedMethod, selectedTag, authFilter, searchQuery]);

  const getMethodBadgeStyle = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'POST':
        return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
      case 'PUT':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'DELETE':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'PATCH':
        return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-700/40 text-slate-300 border-slate-600';
    }
  };

  const authenticatedCount = endpoints.filter((e) => e.authentication_required).length;
  const publicCount = endpoints.length - authenticatedCount;

  return (
    <div className="space-y-6">
      {/* 1. TOP METRICS & STATS BAR */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total APIs</span>
          <p className="text-xl font-extrabold text-white mt-0.5">{endpoints.length}</p>
          <span className="text-[10px] text-slate-500 block">Discovered routes</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
            <Lock className="w-3 h-3" />
            <span>Protected</span>
          </span>
          <p className="text-xl font-extrabold text-amber-300 mt-0.5">{authenticatedCount}</p>
          <span className="text-[10px] text-slate-500 block">Auth required</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
            <Unlock className="w-3 h-3" />
            <span>Public</span>
          </span>
          <p className="text-xl font-extrabold text-emerald-300 mt-0.5">{publicCount}</p>
          <span className="text-[10px] text-slate-500 block">Unrestricted access</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">GET / POST</span>
          <p className="text-xl font-extrabold text-indigo-300 mt-0.5">
            {methodStats['GET'] || 0} / {methodStats['POST'] || 0}
          </p>
          <span className="text-[10px] text-slate-500 block">Read & Write Ops</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Route Tags</span>
          <p className="text-xl font-extrabold text-white mt-0.5">{allTags.length}</p>
          <span className="text-[10px] text-slate-500 block">Domain groups</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Discovery Engine</span>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="w-full mt-1.5 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-[11px] font-semibold transition-all disabled:opacity-50 shadow-md shadow-brand-600/20"
          >
            <RefreshCw className={`w-3 h-3 ${analyzing ? 'animate-spin' : ''}`} />
            <span>{analyzing ? 'Scanning...' : 'Scan APIs'}</span>
          </button>
        </div>
      </div>

      {/* 2. FILTER & SEARCH TOOLBAR */}
      <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by route path, handler function, tag, or file location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          {/* Auth Filter Toggle */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setAuthFilter('ALL')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                authFilter === 'ALL' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setAuthFilter('AUTH')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg font-medium transition-all ${
                authFilter === 'AUTH'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Lock className="w-3 h-3" />
              <span>Auth Only</span>
            </button>
            <button
              onClick={() => setAuthFilter('PUBLIC')}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg font-medium transition-all ${
                authFilter === 'PUBLIC'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Unlock className="w-3 h-3" />
              <span>Public Only</span>
            </button>
          </div>
        </div>

        {/* Method & Tag Pills Bar */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80 text-xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1">Method:</span>
          {['ALL', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((method) => {
            const isSelected = selectedMethod === method;
            return (
              <button
                key={method}
                onClick={() => setSelectedMethod(method)}
                className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold transition-all ${
                  isSelected
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                {method}
              </button>
            );
          })}

          {allTags.length > 0 && (
            <>
              <div className="h-4 w-px bg-slate-800 mx-2" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1">Tag:</span>
              <button
                onClick={() => setSelectedTag('ALL')}
                className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold transition-all ${
                  selectedTag === 'ALL'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                All Tags
              </button>
              {allTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setSelectedTag(tag)}
                  className={`px-2.5 py-0.5 rounded-lg text-[11px] font-semibold transition-all ${
                    selectedTag === tag
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-white'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </>
          )}
        </div>
      </div>

      {/* 3. ENDPOINTS LIST */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <RefreshCw className="w-8 h-8 animate-spin text-brand-500 mb-3" />
          <span className="text-xs">Scanning backend files and analyzing routes...</span>
        </div>
      ) : filteredEndpoints.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/50 border border-slate-800 text-center">
          <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-brand-400 mx-auto mb-3">
            <Code2 className="w-7 h-7" />
          </div>
          <h3 className="text-sm font-bold text-white mb-1">No API Endpoints Detected</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
            {searchQuery || selectedMethod !== 'ALL' || authFilter !== 'ALL'
              ? 'No endpoints matched your filter criteria.'
              : 'DocPilot AI supports FastAPI, Flask, and Express. Click below to analyze project routes.'}
          </p>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
            <span>Discover API Endpoints</span>
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEndpoints.map((ep) => {
            const isExpanded = expandedEndpoints.has(ep.id);
            const badgeClass = getMethodBadgeStyle(ep.method);
            const framework = ep.metadata?.framework || 'FastAPI';
            const purpose =
              ep.metadata?.docstring ||
              ep.metadata?.purpose ||
              'Static analysis detected API endpoint. Purpose documentation will be automatically generated by AI.';
            const params = ep.request_schema?.parameters || [];
            const bodyModel = ep.request_schema?.body_model;
            const responseModel = ep.response_schema?.model;
            const statusCode = ep.response_schema?.status_code || 200;
            const dependencies = ep.metadata?.dependencies || [];
            const relatedComps = ep.metadata?.related_components || [];

            return (
              <div
                key={ep.id}
                className={`rounded-2xl border transition-all overflow-hidden ${
                  isExpanded
                    ? 'bg-slate-900/90 border-brand-500/40 shadow-xl shadow-brand-500/5'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                }`}
              >
                {/* Header Row */}
                <div
                  onClick={() => handleToggleExpand(ep)}
                  className="p-4 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 select-none"
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    {/* Method Badge */}
                    <span
                      className={`px-3 py-1 rounded-lg text-xs font-mono font-bold tracking-wider border uppercase ${badgeClass}`}
                    >
                      {ep.method}
                    </span>

                    {/* Route Path */}
                    <div className="flex items-center gap-2 font-mono text-xs font-bold text-white tracking-tight">
                      <span>{ep.path}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(ep.path);
                        }}
                        className="p-1 rounded-md text-slate-500 hover:text-slate-300 transition-colors"
                        title="Copy route path"
                      >
                        {copiedPath === ep.path ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>

                    {/* Auth Status Badge */}
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                        ep.authentication_required
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      }`}
                    >
                      {ep.authentication_required ? (
                        <>
                          <Lock className="w-3 h-3" />
                          <span>Protected</span>
                        </>
                      ) : (
                        <>
                          <Unlock className="w-3 h-3" />
                          <span>Public</span>
                        </>
                      )}
                    </span>

                    {/* Tags */}
                    {(ep.tags || []).map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700"
                      >
                        {t}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    {/* Handler & File Location */}
                    <div className="text-right hidden sm:block">
                      <span className="text-xs font-mono text-brand-300 block font-semibold">
                        {ep.handler_name}()
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {ep.file_path}:{ep.metadata?.start_line || 1}
                      </span>
                    </div>

                    {/* Framework indicator */}
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-500/30">
                      {framework}
                    </span>

                    {/* Expand icon */}
                    <div className="text-slate-400">
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Section */}
                {isExpanded && (
                  <div className="p-5 pt-0 border-t border-slate-800/80 space-y-5 bg-slate-950/40">
                    {/* A. PURPOSE PLACEHOLDER (AI documentation hook) */}
                    <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/25 space-y-1.5">
                      <div className="flex items-center gap-2 text-indigo-300 text-xs font-bold">
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                        <span>Endpoint Purpose & Semantic Intent</span>
                        <span className="text-[10px] font-normal text-indigo-400/80 font-mono">
                          (Static Analysis Detected · AI Enrichment Target)
                        </span>
                      </div>
                      <p className="text-xs text-indigo-100/90 leading-relaxed font-sans">
                        {purpose}
                      </p>
                    </div>

                    {/* B. SCHEMAS: REQUEST & RESPONSE */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* Request Schema */}
                      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                          <span className="text-xs font-bold text-white flex items-center gap-2">
                            <Layers className="w-3.5 h-3.5 text-brand-400" />
                            <span>Request Specification</span>
                          </span>
                          {bodyModel && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                              Body: {bodyModel}
                            </span>
                          )}
                        </div>

                        {params.length > 0 ? (
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-[11px] font-mono">
                              <thead>
                                <tr className="text-slate-400 border-b border-slate-800">
                                  <th className="pb-1.5 font-semibold">Parameter</th>
                                  <th className="pb-1.5 font-semibold">In</th>
                                  <th className="pb-1.5 font-semibold">Type</th>
                                  <th className="pb-1.5 font-semibold">Required</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60">
                                {params.map((p, idx) => (
                                  <tr key={idx} className="hover:bg-slate-800/30">
                                    <td className="py-1.5 text-white font-bold">{p.name}</td>
                                    <td className="py-1.5">
                                      <span
                                        className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                          p.in === 'path'
                                            ? 'bg-amber-500/20 text-amber-300'
                                            : p.in === 'body'
                                            ? 'bg-indigo-500/20 text-indigo-300'
                                            : 'bg-slate-800 text-slate-300'
                                        }`}
                                      >
                                        {p.in}
                                      </span>
                                    </td>
                                    <td className="py-1.5 text-slate-300">{p.type}</td>
                                    <td className="py-1.5">
                                      {p.required ? (
                                        <span className="text-rose-400 font-bold">Yes</span>
                                      ) : (
                                        <span className="text-slate-500">Optional</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500 italic py-2">
                            No body or query parameters declared in signature.
                          </p>
                        )}
                      </div>

                      {/* Response Schema */}
                      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                          <span className="text-xs font-bold text-white flex items-center gap-2">
                            <Server className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Response Specification</span>
                          </span>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                              statusCode >= 200 && statusCode < 300
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            HTTP {statusCode}
                          </span>
                        </div>

                        <div className="space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Response Model:</span>
                            <span className="font-mono text-emerald-300 font-bold">
                              {responseModel || 'dict / Any'}
                            </span>
                          </div>
                          {ep.response_schema?.return_type && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400">Return Annotation:</span>
                              <span className="font-mono text-cyan-300">
                                {ep.response_schema.return_type}
                              </span>
                            </div>
                          )}
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Content Type:</span>
                            <span className="font-mono text-slate-300">application/json</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* C. EXECUTION & DEPENDENCIES DETAILS */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      {/* Handler & File Location */}
                      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                          Source Code Location
                        </span>
                        <div className="flex items-center gap-2 text-slate-300 font-mono text-xs">
                          <FileCode className="w-4 h-4 text-brand-400 shrink-0" />
                          <span className="truncate">{ep.file_path}</span>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                            L{ep.metadata?.start_line || 1} - L{ep.metadata?.end_line || 1}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-slate-300 font-mono text-xs pt-1">
                          <Code2 className="w-4 h-4 text-indigo-400 shrink-0" />
                          <span>Handler: </span>
                          <span className="text-white font-bold">{ep.handler_name}()</span>
                        </div>
                      </div>

                      {/* Dependencies & Injections */}
                      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                          Dependency Injections
                        </span>
                        {dependencies.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {dependencies.map((dep, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[11px] font-mono text-slate-300"
                              >
                                {dep}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500 italic">No framework dependencies injected.</span>
                        )}
                      </div>
                    </div>

                    {/* D. RELATED ARCHITECTURE COMPONENTS */}
                    {relatedComps.length > 0 && (
                      <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                            <Boxes className="w-3.5 h-3.5 text-brand-400" />
                            <span>Related Architecture Components</span>
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Statically referenced services, models, and repositories
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2 pt-1">
                          {relatedComps.map((comp, idx) => {
                            const name = typeof comp === 'string' ? comp : comp.name;
                            const type = typeof comp === 'string' ? 'component' : comp.type || 'component';
                            return (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-800/80 border border-slate-700 text-xs font-mono text-slate-200"
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
                                <strong>{name}</strong>
                                <span className="text-[10px] text-slate-400">({type})</span>
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
