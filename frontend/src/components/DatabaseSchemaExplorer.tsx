import React, { useState, useEffect } from 'react';
import {
  Database,
  Table,
  Key,
  Link2,
  Search,
  Filter,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Layers,
  ArrowRight,
  Code2,
  FileCode,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Hash,
} from 'lucide-react';
import {
  DatabaseModel,
  DatabaseRelationship,
  DatabaseDiagramResponse,
  DatabaseField,
} from '../types';
import {
  fetchDatabaseModels,
  fetchDatabaseRelationships,
  fetchDatabaseDiagram,
  analyzeProjectDatabase,
} from '../api/client';
import { MermaidViewer } from './MermaidViewer';

interface DatabaseSchemaExplorerProps {
  projectId: string;
  projectName?: string;
  onRefreshProject?: () => void;
  defaultView?: 'diagram' | 'models' | 'relationships';
}

export const DatabaseSchemaExplorer: React.FC<DatabaseSchemaExplorerProps> = ({
  projectId,
  projectName,
  onRefreshProject,
  defaultView = 'diagram',
}) => {
  const [activeTab, setActiveTab] = useState<'diagram' | 'models' | 'relationships'>(defaultView);
  const [models, setModels] = useState<DatabaseModel[]>([]);
  const [relationships, setRelationships] = useState<DatabaseRelationship[]>([]);
  const [diagram, setDiagram] = useState<DatabaseDiagramResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [analyzeSuccess, setAnalyzeSuccess] = useState<boolean>(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedOrm, setSelectedOrm] = useState<string>('ALL');
  const [selectedRelType, setSelectedRelType] = useState<string>('ALL');
  const [expandedModelId, setExpandedModelId] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadDatabaseData();
    }
  }, [projectId]);

  const loadDatabaseData = async () => {
    setLoading(true);
    try {
      const [modelsData, relsData, diagData] = await Promise.all([
        fetchDatabaseModels(projectId),
        fetchDatabaseRelationships(projectId),
        fetchDatabaseDiagram(projectId),
      ]);
      setModels(modelsData || []);
      setRelationships(relsData || []);
      setDiagram(diagData || null);
      if (modelsData && modelsData.length > 0 && !expandedModelId) {
        setExpandedModelId(modelsData[0].id);
      }
    } catch (err) {
      console.warn('Failed to load database schema data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalyzeSuccess(false);
    try {
      const result = await analyzeProjectDatabase(projectId);
      setModels(result.models || []);
      setRelationships(result.relationships || []);
      const diagData = await fetchDatabaseDiagram(projectId);
      setDiagram(diagData);
      setAnalyzeSuccess(true);
      if (onRefreshProject) onRefreshProject();
      setTimeout(() => setAnalyzeSuccess(false), 3500);
    } catch (err: any) {
      alert(`Database structure analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzing(false);
    }
  };

  // Filtered models
  const filteredModels = models.filter((m) => {
    const matchesOrm = selectedOrm === 'ALL' || m.orm_type.toLowerCase() === selectedOrm.toLowerCase();
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      m.name.toLowerCase().includes(q) ||
      m.table_name.toLowerCase().includes(q) ||
      m.fields.some((f) => f.name.toLowerCase().includes(q) || f.data_type.toLowerCase().includes(q));
    return matchesOrm && matchesSearch;
  });

  // Filtered relationships
  const filteredRelationships = relationships.filter((r) => {
    const matchesType = selectedRelType === 'ALL' || r.relationship_type === selectedRelType;
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      r.source_model.toLowerCase().includes(q) ||
      r.target_model.toLowerCase().includes(q) ||
      (r.description && r.description.toLowerCase().includes(q));
    return matchesType && matchesSearch;
  });

  // Total fields count
  const totalFields = models.reduce((acc, m) => acc + (m.fields?.length || 0), 0);

  // ORM breakdown count
  const ormCounts = models.reduce((acc: Record<string, number>, m) => {
    acc[m.orm_type] = (acc[m.orm_type] || 0) + 1;
    return acc;
  }, {});

  const getRelBadgeStyle = (type: string) => {
    switch (type) {
      case 'ONE_TO_ONE':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      case 'ONE_TO_MANY':
        return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30';
      case 'MANY_TO_MANY':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'FOREIGN_KEY':
      default:
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30';
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner with Stats & Analyze Trigger */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white">Database Structure & Relationships</h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                Phase 7 Static Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Static detection across SQLAlchemy (classic & 2.0 mapped_column), Django ORM, and raw SQL schemas.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {analyzeSuccess && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-xl font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Models Detected</span>
            </span>
          )}
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-amber-600/20 transition-all"
          >
            {analyzing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            <span>{analyzing ? 'Analyzing Schema...' : 'Analyze Database'}</span>
          </button>
        </div>
      </div>

      {/* Metrics Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Database Models</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-white">{models.length}</span>
            <span className="text-[11px] text-slate-500">tables mapped</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider">Total Fields</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-cyan-300">{totalFields}</span>
            <span className="text-[11px] text-slate-500">columns</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider">Relationships</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-purple-300">{relationships.length}</span>
            <span className="text-[11px] text-slate-500">links & FKs</span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">Frameworks</span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {Object.keys(ormCounts).length === 0 ? (
              <span className="text-xs text-slate-500">None detected</span>
            ) : (
              Object.entries(ormCounts).map(([orm, count]) => (
                <span
                  key={orm}
                  className="px-2 py-0.5 rounded-md bg-slate-800 text-amber-300 border border-amber-500/20 text-[10px] font-mono"
                >
                  {orm}: {count}
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('diagram')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'diagram'
                ? 'bg-amber-600 text-white shadow-sm shadow-amber-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Mermaid ER Diagram</span>
          </button>

          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'models'
                ? 'bg-amber-600 text-white shadow-sm shadow-amber-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Models & Fields ({models.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('relationships')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'relationships'
                ? 'bg-amber-600 text-white shadow-sm shadow-amber-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Link2 className="w-3.5 h-3.5" />
            <span>Relationships ({relationships.length})</span>
          </button>
        </div>

        {/* Search input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search models, fields, types..."
            className="w-full bg-slate-900/70 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
          />
        </div>
      </div>

      {/* Main Tab Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Loader2 className="w-7 h-7 animate-spin text-amber-500 mb-2" />
          <span className="text-xs">Loading database architecture metadata...</span>
        </div>
      ) : models.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-3">
            <Database className="w-7 h-7" />
          </div>
          <h4 className="text-sm font-bold text-white mb-1">No Database Models Detected</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
            DocPilot AI statically scans for SQLAlchemy declarative models, SQLAlchemy 2.0 mapped_column, Django ORM, and SQL CREATE TABLE statements.
          </p>
          <button
            onClick={handleAnalyze}
            disabled={analyzing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md transition-all"
          >
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            <span>Scan Database Models Now</span>
          </button>
        </div>
      ) : (
        <>
          {/* TAB 1: MERMAID ER DIAGRAM */}
          {activeTab === 'diagram' && (
            <div className="space-y-4">
              {diagram && diagram.mermaid_code ? (
                <MermaidViewer
                  code={diagram.mermaid_code}
                  title={`${projectName || 'Project'} Entity Relationship (ER) Diagram`}
                />
              ) : (
                <div className="p-8 bg-slate-900/50 rounded-2xl border border-slate-800 text-center text-slate-400 text-xs">
                  No diagram code generated yet. Click "Analyze Database" to produce the Mermaid ER diagram.
                </div>
              )}
            </div>
          )}

          {/* TAB 2: MODELS & FIELDS EXPLORER */}
          {activeTab === 'models' && (
            <div className="space-y-4">
              {/* ORM filter pills */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Filter className="w-3 h-3" />
                  <span>ORM Filter:</span>
                </span>
                {['ALL', 'SQLAlchemy', 'Django', 'SQL'].map((orm) => (
                  <button
                    key={orm}
                    onClick={() => setSelectedOrm(orm)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all ${
                      selectedOrm === orm
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {orm}
                  </button>
                ))}
              </div>

              {/* Models List */}
              <div className="grid grid-cols-1 gap-4">
                {filteredModels.map((model) => {
                  const isExpanded = expandedModelId === model.id;
                  const pkCount = model.fields.filter((f) => f.is_primary_key).length;
                  const fkCount = model.fields.filter((f) => f.is_foreign_key).length;

                  return (
                    <div
                      key={model.id}
                      className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden transition-all hover:border-slate-700 shadow-md"
                    >
                      {/* Model Card Header */}
                      <div
                        onClick={() => setExpandedModelId(isExpanded ? null : model.id)}
                        className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none bg-slate-900/80 hover:bg-slate-800/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <button className="text-slate-400 hover:text-white transition-colors">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                            <Table className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-bold text-white font-mono">{model.name}</span>
                              <span className="text-xs text-slate-400 font-mono">
                                (table: <strong className="text-slate-300">{model.table_name}</strong>)
                              </span>
                              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20 uppercase">
                                {model.orm_type}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 font-mono">
                              <FileCode className="w-3 h-3 text-slate-600" />
                              <span>{model.file_path}:L{model.start_line}</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                            {model.fields.length} columns
                          </span>
                          {pkCount > 0 && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              {pkCount} PK
                            </span>
                          )}
                          {fkCount > 0 && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                              {fkCount} FK
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Expanded Model Fields Table */}
                      {isExpanded && (
                        <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs">
                              <thead>
                                <tr className="border-b border-slate-800 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                                  <th className="pb-2.5 pl-2 font-medium">Field / Column</th>
                                  <th className="pb-2.5 font-medium">Data Type</th>
                                  <th className="pb-2.5 font-medium">Keys</th>
                                  <th className="pb-2.5 font-medium">Nullable</th>
                                  <th className="pb-2.5 font-medium">Default</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                                {model.fields.map((field) => (
                                  <tr key={field.id} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="py-2.5 pl-2 font-bold text-white flex items-center gap-1.5">
                                      {field.is_primary_key && <Key className="w-3 h-3 text-amber-400 shrink-0" />}
                                      <span>{field.name}</span>
                                    </td>
                                    <td className="py-2.5 text-cyan-300">{field.data_type}</td>
                                    <td className="py-2.5">
                                      <div className="flex items-center gap-1.5">
                                        {field.is_primary_key && (
                                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                            PRIMARY KEY
                                          </span>
                                        )}
                                        {field.is_foreign_key && (
                                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1">
                                            <span>FK</span>
                                            {field.foreign_key_target && (
                                              <span className="text-[9px] text-cyan-200">
                                                -&gt; {field.foreign_key_target}
                                              </span>
                                            )}
                                          </span>
                                        )}
                                        {!field.is_primary_key && !field.is_foreign_key && (
                                          <span className="text-slate-600">-</span>
                                        )}
                                      </div>
                                    </td>
                                    <td className="py-2.5">
                                      {field.is_nullable ? (
                                        <span className="text-slate-400">NULL</span>
                                      ) : (
                                        <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                                          NOT NULL
                                        </span>
                                      )}
                                    </td>
                                    <td className="py-2.5 text-slate-400">
                                      {field.default_value ? (
                                        <span className="text-emerald-400">{field.default_value}</span>
                                      ) : (
                                        <span className="text-slate-600">-</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: RELATIONSHIPS */}
          {activeTab === 'relationships' && (
            <div className="space-y-4">
              {/* Filter by relationship type */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Filter className="w-3 h-3" />
                  <span>Relationship Type:</span>
                </span>
                {['ALL', 'ONE_TO_ONE', 'ONE_TO_MANY', 'MANY_TO_MANY', 'FOREIGN_KEY'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setSelectedRelType(type)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-all ${
                      selectedRelType === type
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>

              {filteredRelationships.length === 0 ? (
                <div className="p-8 bg-slate-900/40 rounded-2xl border border-slate-800 text-center text-xs text-slate-500">
                  No relationships match the selected filter.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {filteredRelationships.map((rel) => {
                    const badgeClass = getRelBadgeStyle(rel.relationship_type);
                    return (
                      <div
                        key={rel.id}
                        className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all space-y-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-mono font-bold border uppercase ${badgeClass}`}>
                            {rel.relationship_type}
                          </span>
                          {rel.description && (
                            <span className="text-[11px] text-slate-400 italic">
                              "{rel.description}"
                            </span>
                          )}
                        </div>

                        {/* Visual Source -> Target */}
                        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800 font-mono text-xs">
                          <div className="flex items-center gap-2">
                            <Table className="w-3.5 h-3.5 text-amber-400" />
                            <strong className="text-white">{rel.source_model}</strong>
                          </div>
                          <div className="flex items-center gap-1 text-slate-500">
                            <span className="text-[10px] uppercase font-sans font-semibold text-slate-400">
                              {rel.relationship_type === 'ONE_TO_ONE'
                                ? '1:1'
                                : rel.relationship_type === 'ONE_TO_MANY'
                                ? '1:N'
                                : rel.relationship_type === 'MANY_TO_MANY'
                                ? 'M:N'
                                : 'FK'}
                            </span>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                          </div>
                          <div className="flex items-center gap-2">
                            <Table className="w-3.5 h-3.5 text-cyan-400" />
                            <strong className="text-white">{rel.target_model}</strong>
                          </div>
                        </div>

                        {/* Additional Metadata */}
                        <div className="space-y-1 text-[11px] text-slate-400 font-mono">
                          {rel.foreign_key_field && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">FK Field:</span>
                              <span className="text-cyan-300">{rel.foreign_key_field}</span>
                            </div>
                          )}
                          {rel.back_populates && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Back Populates:</span>
                              <span className="text-emerald-300">{rel.back_populates}</span>
                            </div>
                          )}
                          {rel.secondary_table && (
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Join Table:</span>
                              <span className="text-purple-300">{rel.secondary_table}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
