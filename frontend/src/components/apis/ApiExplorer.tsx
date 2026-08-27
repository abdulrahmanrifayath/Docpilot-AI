import React, { useState, useEffect, useMemo } from 'react';
import { projectsApi } from '../../api/projects';
import {
  ApiEndpointListResponse,
  ApiAnalyzeResponse,
} from '../../types';
import { ApiEndpointCard } from './ApiEndpointCard';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import {
  Globe,
  Search,
  RefreshCw,
  Lock,
  Unlock,
  CheckCircle2,
} from 'lucide-react';

interface ApiExplorerProps {
  projectId: string;
}

export const ApiExplorer: React.FC<ApiExplorerProps> = ({ projectId }) => {
  const [apiData, setApiData] = useState<ApiEndpointListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<ApiAnalyzeResponse | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMethod, setSelectedMethod] = useState<string>('ALL');
  const [selectedAuth, setSelectedAuth] = useState<'ALL' | 'AUTH' | 'PUBLIC'>('ALL');
  const [selectedTag, setSelectedTag] = useState<string>('ALL');

  const fetchApis = async () => {
    try {
      setIsLoading(true);
      const data = await projectsApi.getApis(projectId);
      setApiData(data);
    } catch (err) {
      console.error('Failed to load APIs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApis();
  }, [projectId]);

  const handleRunAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      const res = await projectsApi.analyzeApis(projectId);
      setAnalyzeResult(res);
      await fetchApis();
    } catch (err) {
      console.error('Failed to analyze APIs:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Collect all unique tags
  const allTags = useMemo(() => {
    if (!apiData) return [];
    const set = new Set<string>();
    apiData.apis.forEach((a) => a.tags.forEach((t) => set.add(t)));
    return Array.from(set);
  }, [apiData]);

  // Filtered APIs
  const filteredApis = useMemo(() => {
    if (!apiData) return [];
    return apiData.apis.filter((api) => {
      // Method filter
      if (selectedMethod !== 'ALL' && api.method.toUpperCase() !== selectedMethod) {
        return false;
      }
      // Auth filter
      if (selectedAuth === 'AUTH' && !api.authentication_required) return false;
      if (selectedAuth === 'PUBLIC' && api.authentication_required) return false;

      // Tag filter
      if (selectedTag !== 'ALL' && !api.tags.includes(selectedTag)) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesPath = api.path.toLowerCase().includes(q);
        const matchesHandler = api.handler_name.toLowerCase().includes(q);
        const matchesSummary = api.summary && api.summary.toLowerCase().includes(q);
        const matchesTag = api.tags.some((t) => t.toLowerCase().includes(q));
        if (!matchesPath && !matchesHandler && !matchesSummary && !matchesTag) {
          return false;
        }
      }

      return true;
    });
  }, [apiData, selectedMethod, selectedAuth, selectedTag, searchQuery]);

  const securedCount = useMemo(() => {
    if (!apiData) return 0;
    return apiData.apis.filter((a) => a.authentication_required).length;
  }, [apiData]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight uppercase">
                Automatic API Explorer
              </h3>
              <p className="text-xs text-slate-400">
                Statically discovered backend API endpoints, route handlers, parameters, and auth requirements
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-200">
              <strong className="text-white">{apiData?.total_apis || 0}</strong> Endpoints
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-amber-300">
              <strong className="text-amber-400">{securedCount}</strong> Secured
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300">
              <strong className="text-cyan-400">{apiData?.methods_count['GET'] || 0}</strong> GET
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-emerald-300">
              <strong className="text-emerald-400">{apiData?.methods_count['POST'] || 0}</strong> POST
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {analyzeResult && (
            <div className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Analyzed {analyzeResult.total_apis} endpoints in {analyzeResult.duration_ms}ms</span>
            </div>
          )}

          <Button
            variant="primary"
            size="sm"
            isLoading={isAnalyzing}
            onClick={handleRunAnalysis}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />}
          >
            Re-discover APIs
          </Button>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="p-3 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Method Filter Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {['ALL', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((method) => {
            const count =
              method === 'ALL'
                ? apiData?.total_apis || 0
                : apiData?.methods_count[method] || 0;

            const isSelected = selectedMethod === method;

            return (
              <button
                key={method}
                onClick={() => setSelectedMethod(method)}
                className={`text-xs font-mono font-bold px-3 py-1.5 rounded-xl border transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50 shadow-sm'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                <span>{method}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900 text-slate-400">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search, Auth, and Tag Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Auth filter */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setSelectedAuth('ALL')}
              className={`px-2 py-0.5 rounded-lg transition-colors ${
                selectedAuth === 'ALL' ? 'bg-slate-800 text-white' : 'text-slate-400'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setSelectedAuth('AUTH')}
              className={`px-2 py-0.5 rounded-lg flex items-center gap-1 transition-colors ${
                selectedAuth === 'AUTH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'text-slate-400'
              }`}
            >
              <Lock className="w-3 h-3" />
              Auth
            </button>
            <button
              onClick={() => setSelectedAuth('PUBLIC')}
              className={`px-2 py-0.5 rounded-lg flex items-center gap-1 transition-colors ${
                selectedAuth === 'PUBLIC' ? 'bg-slate-800 text-white' : 'text-slate-400'
              }`}
            >
              <Unlock className="w-3 h-3" />
              Public
            </button>
          </div>

          {/* Tag filter */}
          {allTags.length > 0 && (
            <select
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="ALL">All Tags</option>
              {allTags.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          )}

          {/* Search bar */}
          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by path or handler..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Endpoints List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
        </div>
      ) : filteredApis.length === 0 ? (
        <Card className="p-12 text-center border-dashed">
          <Globe className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h4 className="text-sm font-bold text-white">No Matching API Endpoints Found</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            {apiData?.total_apis === 0
              ? 'Click "Re-discover APIs" to run static route detection on your FastAPI, Flask, or Express codebase.'
              : 'Try clearing your search query or adjusting the HTTP method filters.'}
          </p>
          {apiData?.total_apis === 0 && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunAnalysis}
              className="mt-4"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Discover APIs Now
            </Button>
          )}
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredApis.map((endpoint) => (
            <ApiEndpointCard key={endpoint.id} endpoint={endpoint} />
          ))}
        </div>
      )}
    </div>
  );
};
