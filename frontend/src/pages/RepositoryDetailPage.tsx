import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FileText,
  Workflow,
  Globe,
  Database,
  RefreshCw,
  Sparkles,
  Layers,
  ArrowLeft,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Code2,
  Lock,
  Unlock,
  ChevronRight,
  Folder,
  FileCode,
  Download,
} from 'lucide-react';
import {
  Repository,
  DocumentItem,
  DiagramItem,
  PipelineProgress,
} from '../types';
import {
  fetchRepository,
  fetchProgress,
  fetchDocuments,
  fetchDiagrams,
  syncRepository,
  triggerAnalysis,
} from '../api/client';
import { PipelineStepper } from '../components/PipelineStepper';
import { MermaidViewer } from '../components/MermaidViewer';
import { ReactFlowGraph } from '../components/ReactFlowGraph';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface RepositoryDetailPageProps {
  onOpenChat: (repoId: string, repoName: string) => void;
}

export const RepositoryDetailPage: React.FC<RepositoryDetailPageProps> = ({ onOpenChat }) => {
  const { id } = useParams<{ id: string }>();
  const [repository, setRepository] = useState<Repository | null>(null);
  const [progress, setProgress] = useState<PipelineProgress | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [diagrams, setDiagrams] = useState<DiagramItem[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'docs' | 'diagrams' | 'apis' | 'models' | 'sync'>('overview');
  const [activeDocType, setActiveDocType] = useState<string>('readme');
  const [activeDiagramType, setActiveDiagramType] = useState<string>('react_flow');
  const [syncing, setSyncing] = useState<boolean>(false);
  const [apiSearch, setApiSearch] = useState<string>('');
  const [selectedApiTag, setSelectedApiTag] = useState<string>('All');

  useEffect(() => {
    if (id) {
      loadData(id);
      const pollTimer = setInterval(() => {
        checkProgress(id);
      }, 2500);
      return () => clearInterval(pollTimer);
    }
  }, [id]);

  const loadData = async (repoId: string) => {
    try {
      const repo = await fetchRepository(repoId);
      setRepository(repo);
      setProgress({
        repository_id: repo.id,
        status: repo.status,
        current_step: repo.current_step,
        progress_percent: repo.progress_percent,
        error_message: repo.error_message,
      });

      if (repo.status === 'completed') {
        const [docs, diags] = await Promise.all([
          fetchDocuments(repoId),
          fetchDiagrams(repoId),
        ]);
        setDocuments(docs);
        setDiagrams(diags);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const checkProgress = async (repoId: string) => {
    try {
      const p = await fetchProgress(repoId);
      setProgress(p);
      if (p.status === 'completed' && documents.length === 0) {
        loadData(repoId);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSync = async () => {
    if (!id) return;
    setSyncing(true);
    try {
      await syncRepository(id);
      loadData(id);
    } catch (err) {
      console.error(err);
    } finally {
      setSyncing(false);
    }
  };

  const handleReanalyze = async () => {
    if (!id) return;
    try {
      await triggerAnalysis(id);
      loadData(id);
    } catch (err) {
      console.error(err);
    }
  };

  if (!repository) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading repository knowledge base...</p>
      </div>
    );
  }

  const isAnalyzing = repository.status === 'analyzing' || repository.status === 'pending';
  const selectedDoc = documents.find((d) => d.doc_type === activeDocType) || documents[0];
  const selectedDiagram = diagrams.find((d) => d.diagram_type === activeDiagramType) || diagrams[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <Link to="/" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white mb-2 transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Repositories</span>
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">{repository.name}</h1>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                repository.status === 'completed'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-brand-500/10 text-brand-400 border-brand-500/30'
              }`}
            >
              {repository.status}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpenChat(repository.id, repository.name)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 flex items-center gap-2 transition-all"
          >
            <Sparkles className="w-4 h-4 text-cyan-300" />
            <span>Ask AI Assistant</span>
          </button>

          <button
            onClick={handleSync}
            disabled={syncing || isAnalyzing}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-1.5"
            title="Incremental Git / Filesystem Sync"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>

          <button
            onClick={handleReanalyze}
            disabled={isAnalyzing}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            Re-Analyze
          </button>
        </div>
      </div>

      {/* Stepper if running */}
      {progress && (isAnalyzing || progress.status !== 'completed') && (
        <div className="mb-8">
          <PipelineStepper progress={progress} />
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex overflow-x-auto gap-2 border-b border-slate-800 pb-3 mb-8">
        {[
          { key: 'overview', label: 'Overview & Metrics', icon: Layers },
          { key: 'docs', label: 'Documentation Hub', icon: FileText, count: documents.length },
          { key: 'diagrams', label: 'Architecture & Diagrams', icon: Workflow, count: diagrams.length },
          { key: 'apis', label: 'API Explorer', icon: Globe, count: repository.stats?.apis || 0 },
          { key: 'models', label: 'Database Models', icon: Database, count: repository.stats?.models || 0 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 shrink-0 ${
                isActive
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${isActive ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-8">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { label: 'Total Lines', value: repository.stats?.lines?.toLocaleString() || 0, color: 'text-white' },
              { label: 'Source Files', value: repository.stats?.files || 0, color: 'text-brand-300' },
              { label: 'Classes', value: repository.stats?.classes || 0, color: 'text-indigo-300' },
              { label: 'Functions', value: repository.stats?.functions || 0, color: 'text-emerald-300' },
              { label: 'REST APIs', value: repository.stats?.apis || 0, color: 'text-cyan-300' },
              { label: 'Database Models', value: repository.stats?.models || 0, color: 'text-amber-300' },
            ].map((stat, i) => (
              <div key={i} className="p-4 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{stat.label}</p>
                <p className={`text-2xl font-black mt-1 ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Languages & Frameworks */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Languages Breakdown */}
            <div className="p-6 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md">
              <h3 className="text-sm font-bold text-white mb-4">Language Composition</h3>
              {Object.keys(repository.languages || {}).length === 0 ? (
                <p className="text-xs text-slate-400">No language data detected.</p>
              ) : (
                <div className="space-y-3">
                  {/* Multi-color Progress bar */}
                  <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-800">
                    {Object.entries(repository.languages).map(([lang, data], idx) => {
                      const colors = ['bg-brand-500', 'bg-cyan-500', 'bg-emerald-500', 'bg-amber-500', 'bg-rose-500', 'bg-indigo-500'];
                      return (
                        <div
                          key={lang}
                          style={{ width: `${data.percent}%` }}
                          className={`${colors[idx % colors.length]} h-full transition-all`}
                          title={`${lang}: ${data.percent}%`}
                        />
                      );
                    })}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                    {Object.entries(repository.languages).map(([lang, data]) => (
                      <div key={lang} className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                        <p className="text-xs font-bold text-white">{lang}</p>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                          {data.lines.toLocaleString()} lines ({data.percent}%)
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Frameworks & Infrastructure */}
            <div className="p-6 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md">
              <h3 className="text-sm font-bold text-white mb-4">Detected Frameworks & Infrastructure</h3>
              {repository.frameworks?.length === 0 ? (
                <p className="text-xs text-slate-400">No external frameworks detected in manifests.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {repository.frameworks.map((fw) => (
                    <span
                      key={fw}
                      className="px-3 py-1.5 rounded-xl bg-brand-500/10 border border-brand-500/30 text-xs font-semibold text-brand-300 flex items-center gap-1.5 shadow-sm"
                    >
                      <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{fw}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Directory Hierarchy & Inferred Purposes */}
          <div className="p-6 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md">
            <h3 className="text-sm font-bold text-white mb-4">Project Structure & Folder Purposes</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(repository.structure?.folder_purposes || {}).map(([folder, purpose]) => (
                <div key={folder} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-2.5">
                  <Folder className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-mono font-bold text-cyan-300">{folder}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{purpose}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DOCUMENTATION HUB */}
      {activeTab === 'docs' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Docs Sidebar */}
          <div className="space-y-1.5">
            {[
              { id: 'readme', label: 'README.md', desc: 'Project overview & quickstart' },
              { id: 'architecture', label: 'Architecture Guide', desc: 'System design & layers' },
              { id: 'api', label: 'REST API Reference', desc: 'Endpoint specifications' },
              { id: 'onboarding', label: 'Onboarding Guide', desc: 'Day 1 developer setup' },
              { id: 'report', label: 'Technical Health Report', desc: 'Metrics & quality grade' },
            ].map((docItem) => {
              const isSelected = activeDocType === docItem.id;
              return (
                <button
                  key={docItem.id}
                  onClick={() => setActiveDocType(docItem.id)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                    isSelected
                      ? 'bg-brand-600 text-white border-brand-500 shadow-md shadow-brand-500/20'
                      : 'bg-[#111827]/60 text-slate-300 border-slate-800 hover:bg-slate-800/60'
                  }`}
                >
                  <p className="text-xs font-bold">{docItem.label}</p>
                  <p className={`text-[10px] mt-0.5 truncate ${isSelected ? 'text-brand-100' : 'text-slate-500'}`}>
                    {docItem.desc}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Docs Viewer */}
          <div className="lg:col-span-3">
            {selectedDoc ? (
              <MarkdownRenderer
                title={selectedDoc.title}
                content={selectedDoc.content}
                downloadFilename={`${repository.name}_${selectedDoc.doc_type}.md`}
              />
            ) : (
              <div className="py-20 text-center text-slate-500 text-xs">
                Documentation generating or not available yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: ARCHITECTURE & DIAGRAMS */}
      {activeTab === 'diagrams' && (
        <div className="space-y-6">
          {/* Subtabs */}
          <div className="flex flex-wrap gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800">
            {[
              { id: 'react_flow', label: 'Interactive React Flow Graph' },
              { id: 'architecture', label: 'Runtime Architecture (Mermaid)' },
              { id: 'sequence', label: 'Sequence Diagram (Mermaid)' },
              { id: 'er', label: 'Entity-Relationship ER Diagram' },
              { id: 'dependency', label: 'Module Dependency Graph' },
            ].map((diagTab) => (
              <button
                key={diagTab.id}
                onClick={() => setActiveDiagramType(diagTab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  activeDiagramType === diagTab.id
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {diagTab.label}
              </button>
            ))}
          </div>

          {activeDiagramType === 'react_flow' ? (
            <div>
              {diagrams.find((d) => d.diagram_type === 'react_flow')?.flow_data ? (
                <ReactFlowGraph
                  flowData={diagrams.find((d) => d.diagram_type === 'react_flow')!.flow_data!}
                />
              ) : (
                <div className="py-20 text-center text-slate-500 text-xs">React Flow data not available.</div>
              )}
            </div>
          ) : (
            <div>
              {selectedDiagram?.mermaid_code ? (
                <MermaidViewer
                  code={selectedDiagram.mermaid_code}
                  title={selectedDiagram.title}
                />
              ) : (
                <div className="py-20 text-center text-slate-500 text-xs">Mermaid diagram not available.</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: API EXPLORER */}
      {activeTab === 'apis' && (
        <div className="space-y-6">
          {/* Search bar */}
          <div className="flex gap-4">
            <input
              type="text"
              value={apiSearch}
              onChange={(e) => setApiSearch(e.target.value)}
              placeholder="Filter by endpoint path, method, or handler name..."
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Endpoints List */}
          {documents.find((d) => d.doc_type === 'api') ? (
            <div className="space-y-4">
              <MarkdownRenderer
                title="API Endpoints Specification"
                content={documents.find((d) => d.doc_type === 'api')!.content}
                downloadFilename={`${repository.name}_api_spec.md`}
              />
            </div>
          ) : (
            <div className="py-20 text-center text-slate-500 text-xs">No REST API routes discovered.</div>
          )}
        </div>
      )}

      {/* TAB 5: DATABASE MODELS */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          {diagrams.find((d) => d.diagram_type === 'er')?.mermaid_code && (
            <MermaidViewer
              title="Database Entity-Relationship (ER) Diagram"
              code={diagrams.find((d) => d.diagram_type === 'er')!.mermaid_code!}
            />
          )}
        </div>
      )}
    </div>
  );
};
