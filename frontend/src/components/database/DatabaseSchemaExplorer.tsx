import React, { useState, useEffect, useMemo } from 'react';
import { projectsApi } from '../../api/projects';
import {
  DatabaseModelListResponse,
  DatabaseDiagramResponse,
  DatabaseAnalyzeResponse,
} from '../../types';
import { MermaidViewer } from './MermaidViewer';
import { ModelTableCard } from './ModelTableCard';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import {
  Database,
  Search,
  RefreshCw,
  Table2,
  GitGraph,
  CheckCircle2,
} from 'lucide-react';

interface DatabaseSchemaExplorerProps {
  projectId: string;
  initialView?: 'diagram' | 'tables';
}

export const DatabaseSchemaExplorer: React.FC<DatabaseSchemaExplorerProps> = ({
  projectId,
  initialView = 'diagram',
}) => {
  const [modelsData, setModelsData] = useState<DatabaseModelListResponse | null>(null);
  const [diagramData, setDiagramData] = useState<DatabaseDiagramResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<DatabaseAnalyzeResponse | null>(null);

  const [activeView, setActiveView] = useState<'diagram' | 'tables'>(initialView);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFramework, setSelectedFramework] = useState<string>('ALL');

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [mRes, dRes] = await Promise.all([
        projectsApi.getDbModels(projectId),
        projectsApi.getDbDiagram(projectId),
      ]);
      setModelsData(mRes);
      setDiagramData(dRes);
    } catch (err) {
      console.error('Failed to load database schema:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleRunAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      const res = await projectsApi.analyzeDatabase(projectId);
      setAnalyzeResult(res);
      await fetchData();
    } catch (err) {
      console.error('Failed to analyze database schema:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const filteredModels = useMemo(() => {
    if (!modelsData) return [];
    return modelsData.models.filter((m) => {
      if (selectedFramework !== 'ALL' && m.orm_framework !== selectedFramework) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTable = m.table_name.toLowerCase().includes(q);
        const matchesModel = m.model_name.toLowerCase().includes(q);
        const matchesField = m.fields.some((f) => f.name.toLowerCase().includes(q));
        if (!matchesTable && !matchesModel && !matchesField) return false;
      }
      return true;
    });
  }, [modelsData, selectedFramework, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight uppercase">
                Database Schema & ER Explorer
              </h3>
              <p className="text-xs text-slate-400">
                Statically discovered ORM models, tables, constraints, foreign keys, and ER cardinality
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-200">
              <strong className="text-white">{modelsData?.total_models || 0}</strong> Tables / Models
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-indigo-300">
              <strong className="text-indigo-400">{diagramData?.total_relationships || 0}</strong> Relationships
            </span>
            {modelsData &&
              Object.entries(modelsData.frameworks_count).map(([fw, count]) => (
                <span
                  key={fw}
                  className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300"
                >
                  <strong className="text-cyan-400">{count}</strong> {fw}
                </span>
              ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {analyzeResult && (
            <div className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>
                Parsed {analyzeResult.total_models} models & {analyzeResult.total_relationships} rels in{' '}
                {analyzeResult.duration_ms}ms
              </span>
            </div>
          )}

          <Button
            variant="primary"
            size="sm"
            isLoading={isAnalyzing}
            onClick={handleRunAnalysis}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />}
          >
            Re-scan Database
          </Button>
        </div>
      </div>

      {/* View Switcher & Toolbar */}
      <div className="p-3 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Toggle Mode */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveView('diagram')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
              activeView === 'diagram'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <GitGraph className="w-3.5 h-3.5" />
            <span>Mermaid ER Diagram</span>
          </button>
          <button
            onClick={() => setActiveView('tables')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
              activeView === 'tables'
                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Table2 className="w-3.5 h-3.5" />
            <span>Table Schema Cards</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900 text-slate-400">
              {modelsData?.total_models || 0}
            </span>
          </button>
        </div>

        {/* Filters if in table mode */}
        {activeView === 'tables' && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* Framework filter */}
            {modelsData && Object.keys(modelsData.frameworks_count).length > 1 && (
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
                <button
                  onClick={() => setSelectedFramework('ALL')}
                  className={`px-2 py-0.5 rounded-lg transition-colors ${
                    selectedFramework === 'ALL' ? 'bg-slate-800 text-white' : 'text-slate-400'
                  }`}
                >
                  All
                </button>
                {Object.keys(modelsData.frameworks_count).map((fw) => (
                  <button
                    key={fw}
                    onClick={() => setSelectedFramework(fw)}
                    className={`px-2 py-0.5 rounded-lg transition-colors ${
                      selectedFramework === fw ? 'bg-indigo-600/30 text-indigo-300' : 'text-slate-400'
                    }`}
                  >
                    {fw}
                  </button>
                ))}
              </div>
            )}

            {/* Search Input */}
            <div className="relative w-56">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tables or columns..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>
        )}
      </div>

      {/* Main Content View */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
        </div>
      ) : modelsData?.total_models === 0 ? (
        <Card className="p-12 text-center border-dashed">
          <Database className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h4 className="text-sm font-bold text-white">No Database Models Found</h4>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            DocPilot supports SQLAlchemy models, Django ORM, and raw SQL schema definitions.
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRunAnalysis}
            className="mt-4"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Scan for Database Models
          </Button>
        </Card>
      ) : activeView === 'diagram' ? (
        <MermaidViewer chart={diagramData?.mermaid_code || 'erDiagram'} />
      ) : (
        <div className="space-y-4">
          {filteredModels.map((model) => (
            <ModelTableCard key={model.id} model={model} />
          ))}
        </div>
      )}
    </div>
  );
};
