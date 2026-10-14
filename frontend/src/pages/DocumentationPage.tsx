import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  BookOpen,
  Code2,
  Workflow,
  Sparkles,
  Layers,
  FolderKanban,
  Search,
  ExternalLink,
  Info,
  Clock,
  Database,
  Globe,
  Boxes,
  Cpu,
  RefreshCw,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Download,
  Settings,
  Folder,
  Tag,
  Shield,
  FileCode,
  FileDown,
  ChevronRight,
  Send,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import {
  fetchProjectDocuments,
  generateDocumentation,
  regenerateProjectDocument,
  fetchSettings,
} from '../api/client';
import { DocumentItem, DocumentationType, ProviderSettings } from '../types';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

// 8 Sections matching Phase 9 requirements
type DocSection =
  | 'overview'
  | 'readme'
  | 'architecture'
  | 'apis'
  | 'database'
  | 'modules'
  | 'classes'
  | 'functions';

const SECTION_CONFIG: Record<
  DocSection,
  {
    type: DocumentationType;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    desc: string;
  }
> = {
  overview: {
    type: 'PROJECT_OVERVIEW',
    label: 'Overview',
    icon: BookOpen,
    desc: 'High-level project summary and tech breakdown',
  },
  readme: {
    type: 'README',
    label: 'README',
    icon: FileText,
    desc: 'Production-ready README.md with setup guide',
  },
  architecture: {
    type: 'ARCHITECTURE_OVERVIEW',
    label: 'Architecture',
    icon: Workflow,
    desc: 'System layout & cross-tier flow specification',
  },
  apis: {
    type: 'API_DOCS',
    label: 'APIs',
    icon: Globe,
    desc: 'REST endpoints, request/response models & auth',
  },
  database: {
    type: 'DATABASE_DOCS',
    label: 'Database',
    icon: Database,
    desc: 'ORM models, tables, columns & ER relationships',
  },
  modules: {
    type: 'FOLDER_DOCS',
    label: 'Modules',
    icon: Folder,
    desc: 'Folder hierarchies and component modules',
  },
  classes: {
    type: 'CLASS_DOCS',
    label: 'Classes',
    icon: Boxes,
    desc: 'Object-oriented classes, methods & inheritance',
  },
  functions: {
    type: 'FUNCTION_DOCS',
    label: 'Functions',
    icon: Code2,
    desc: 'Top-level functions, signatures & callers',
  },
};

export const DocumentationPage: React.FC = () => {
  const { activeProject } = useProjects();
  const navigate = useNavigate();

  const [activeSection, setActiveSection] = useState<DocSection>('overview');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [providerSettings, setProviderSettings] = useState<ProviderSettings | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [isConfigRequired, setIsConfigRequired] = useState<boolean>(false);

  // Sub-selected document index if multiple docs exist for a section
  const [selectedDocIndex, setSelectedDocIndex] = useState<number>(0);

  useEffect(() => {
    loadSettingsState();
  }, []);

  useEffect(() => {
    if (activeProject?.id) {
      loadDocuments(activeProject.id);
    }
  }, [activeProject?.id]);

  // Reset selected document index when section changes
  useEffect(() => {
    setSelectedDocIndex(0);
  }, [activeSection]);

  const loadSettingsState = async () => {
    try {
      const s = await fetchSettings();
      setProviderSettings(s);
      setIsConfigRequired(!s.is_configured);
    } catch (err) {
      console.warn('Could not fetch settings state:', err);
    }
  };

  const loadDocuments = async (projectId: string) => {
    setLoading(true);
    setErrorBanner(null);
    try {
      const docs = await fetchProjectDocuments(projectId);
      setDocuments(docs);
    } catch (err: any) {
      console.warn('Error loading documents:', err);
    } finally {
      setLoading(false);
    }
  };

  // Documents matching current active section
  const currentSectionType = SECTION_CONFIG[activeSection].type;
  const sectionDocs = useMemo(() => {
    return documents.filter((d) => d.document_type.toUpperCase() === currentSectionType);
  }, [documents, currentSectionType]);

  const activeDoc = sectionDocs[selectedDocIndex] || sectionDocs[0] || null;

  // Generate for current section or full suite
  const handleGenerate = async (targetType?: DocumentationType) => {
    if (!activeProject) return;
    setGenerating(true);
    setErrorBanner(null);
    try {
      const typeToGen = targetType || currentSectionType;
      await generateDocumentation(activeProject.id, {
        document_types: [typeToGen],
      });
      await loadDocuments(activeProject.id);
      setIsConfigRequired(false);
    } catch (err: any) {
      if (err.status === 400 && (err.data?.status === 'CONFIGURATION_REQUIRED' || !providerSettings?.is_configured)) {
        setIsConfigRequired(true);
        setErrorBanner(
          err.data?.message ||
            'LLM Provider is not configured. Please supply an API key in Settings to generate AI documentation.'
        );
      } else {
        alert(`Generation failed: ${err.message || err}`);
      }
    } finally {
      setGenerating(false);
    }
  };

  // Generate all 5 core documentation chapters at once
  const handleGenerateAll = async () => {
    if (!activeProject) return;
    setGenerating(true);
    setErrorBanner(null);
    try {
      await generateDocumentation(activeProject.id, {
        document_types: [
          'PROJECT_OVERVIEW',
          'README',
          'ARCHITECTURE_OVERVIEW',
          'API_DOCS',
          'DATABASE_DOCS',
        ],
      });
      await loadDocuments(activeProject.id);
      setIsConfigRequired(false);
    } catch (err: any) {
      if (err.status === 400 && (err.data?.status === 'CONFIGURATION_REQUIRED' || !providerSettings?.is_configured)) {
        setIsConfigRequired(true);
        setErrorBanner(
          err.data?.message ||
            'LLM Provider is not configured. Please supply an API key in Settings.'
        );
      } else {
        alert(`Generation failed: ${err.message || err}`);
      }
    } finally {
      setGenerating(false);
    }
  };

  // Regenerate current document
  const handleRegenerate = async (docId: string) => {
    if (!activeProject) return;
    setRegeneratingId(docId);
    setErrorBanner(null);
    try {
      await regenerateProjectDocument(activeProject.id, docId);
      await loadDocuments(activeProject.id);
      setIsConfigRequired(false);
    } catch (err: any) {
      if (err.status === 400 && (err.data?.status === 'CONFIGURATION_REQUIRED' || !providerSettings?.is_configured)) {
        setIsConfigRequired(true);
        setErrorBanner(
          err.data?.message ||
            'LLM Provider is not configured. Please supply an API key in Settings.'
        );
      } else {
        alert(`Regeneration failed: ${err.message || err}`);
      }
    } finally {
      setRegeneratingId(null);
    }
  };

  // Export all documentation as single bundled Markdown file
  const handleExportAll = () => {
    if (!documents.length || !activeProject) return;
    const bundle = documents
      .map(
        (d) =>
          `# ${d.title}\n*Type: ${d.document_type} | Version: v${d.version} | Model: ${d.model || 'N/A'}*\n\n${d.content}\n\n---\n`
      )
      .join('\n\n');

    const blob = new Blob([bundle], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${activeProject.name.toLowerCase().replace(/\s+/g, '-')}-documentation-suite.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Please select an existing project from the top selector or upload a codebase to view and generate technical documentation.
        </p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
        >
          <FolderKanban className="w-4 h-4" />
          <span>Go to Projects</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Documentation Center</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {activeProject.name}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Grounded technical documentation synthesized from parsed AST entities, API endpoints, and database models.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {documents.length > 0 && (
            <button
              onClick={handleExportAll}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-all"
              title="Download all generated documentation chapters as a single Markdown file"
            >
              <FileDown className="w-3.5 h-3.5 text-brand-400" />
              <span>Export All (.md)</span>
            </button>
          )}

          <Link
            to={`/projects/${activeProject.id}#reports-export-section`}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold border border-indigo-500/30 transition-all"
            title="Open Technical Reports & Multi-Format Export Center (PDF, HTML, MD)"
          >
            <FileDown className="w-3.5 h-3.5 text-indigo-400" />
            <span>Reports & PDF Export</span>
          </Link>

          <button
            onClick={handleGenerateAll}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>{generating ? 'Synthesizing...' : 'Generate Full Suite'}</span>
          </button>
        </div>
      </div>

      {/* Configuration Required Banner if LLM is not configured */}
      {isConfigRequired && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-white mb-0.5">AI Provider Configuration Required</h4>
              <p className="text-amber-200/90 leading-relaxed">
                DocPilot AI requires an LLM API key (OpenAI, Gemini, Anthropic, or local Ollama) to synthesize technical
                documentation. No fake or hallucinated documents will be created.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/settings')}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shrink-0 transition-all shadow-md shadow-amber-600/30"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Configure LLM Settings</span>
          </button>
        </div>
      )}

      {/* Error alert if any other error occurred */}
      {errorBanner && !isConfigRequired && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-rose-400 hover:text-white text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Documentation Center Layout: Sidebar Sections + Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Sidebar Navigation: 8 Required Sections */}
        <div className="lg:col-span-1 space-y-3">
          <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-md">
            <div className="flex items-center justify-between px-2 pb-2 mb-1 border-b border-slate-800">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Documentation Chapters
              </span>
              <span className="text-[10px] font-mono text-brand-400 font-bold">
                {documents.length} Generated
              </span>
            </div>

            <div className="space-y-1 mt-2">
              {(Object.keys(SECTION_CONFIG) as DocSection[]).map((secKey) => {
                const sec = SECTION_CONFIG[secKey];
                const Icon = sec.icon;
                const isSelected = activeSection === secKey;
                const hasDoc = documents.some((d) => d.document_type.toUpperCase() === sec.type);

                return (
                  <button
                    key={secKey}
                    onClick={() => setActiveSection(secKey)}
                    className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left transition-all ${
                      isSelected
                        ? 'bg-brand-600/20 border border-brand-500/60 text-white shadow-md shadow-brand-500/10'
                        : 'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div
                        className={`p-1.5 rounded-lg ${
                          isSelected
                            ? 'bg-brand-500 text-white'
                            : hasDoc
                            ? 'bg-slate-800 text-slate-300'
                            : 'bg-slate-800/40 text-slate-500'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div className="truncate">
                        <p className={`text-xs font-bold leading-tight ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                          {sec.label}
                        </p>
                        <p className="text-[10px] text-slate-500 truncate mt-0.5">{sec.desc}</p>
                      </div>
                    </div>

                    {hasDoc && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 ml-2" title="Generated" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Info Box */}
          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 text-[11px] text-slate-400 space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-300">
              <Shield className="w-3.5 h-3.5 text-brand-400" />
              <span>Context Grounding Guarantee</span>
            </div>
            <p className="text-slate-500 leading-relaxed text-[10px]">
              Every explanation is synthesized strictly from parsed AST entities, API route definitions, and database ORM schemas. Never invents nonexistent components.
            </p>
          </div>
        </div>

        {/* Main Document Viewer Canvas */}
        <div className="lg:col-span-3 space-y-4">
          {/* If docs exist in this section */}
          {activeDoc ? (
            <div className="space-y-4">
              {/* Document Header & Metadata Badge Bar */}
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur-md">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-brand-500/20 text-brand-300 border border-brand-500/40 text-[10px] font-mono font-bold uppercase">
                        {activeDoc.document_type}
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 text-[10px] font-mono font-bold">
                        v{activeDoc.version}
                      </span>
                      {activeDoc.model && (
                        <span className="px-2 py-0.5 rounded-md bg-indigo-950/80 text-indigo-300 border border-indigo-500/40 text-[10px] font-mono">
                          {activeDoc.model}
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-bold text-white mt-1.5">{activeDoc.title}</h2>
                    {activeDoc.generated_at && (
                      <p className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                        <Clock className="w-3 h-3" />
                        <span>Generated on {new Date(activeDoc.generated_at).toLocaleString()}</span>
                      </p>
                    )}
                  </div>

                  {/* Document Actions (Regenerate button) */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRegenerate(activeDoc.id)}
                      disabled={regeneratingId === activeDoc.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold border border-slate-700 transition-all disabled:opacity-50"
                      title="Re-run AI prompt with updated repository context, incrementing version"
                    >
                      <RefreshCw
                        className={`w-3.5 h-3.5 ${regeneratingId === activeDoc.id ? 'animate-spin text-brand-400' : ''}`}
                      />
                      <span>{regeneratingId === activeDoc.id ? 'Regenerating...' : 'Regenerate'}</span>
                    </button>
                  </div>
                </div>

                {/* Sub-selector tabs if multiple documents exist in this section (e.g. multiple classes or functions) */}
                {sectionDocs.length > 1 && (
                  <div className="mt-3 pt-3 border-t border-slate-800 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] uppercase font-bold text-slate-500 mr-1">Chapters:</span>
                    {sectionDocs.map((doc, idx) => (
                      <button
                        key={doc.id}
                        onClick={() => setSelectedDocIndex(idx)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                          selectedDocIndex === idx
                            ? 'bg-brand-600 text-white shadow-sm'
                            : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {doc.title.replace(activeProject.name + ' - ', '')}
                      </button>
                    ))}
                  </div>
                )}

                {/* Source Entities Reference Pills (Clickable references) */}
                {activeDoc.source_entities && activeDoc.source_entities.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                      <Tag className="w-3 h-3 text-brand-400" />
                      <span>Verified Source Entities ({activeDoc.source_entities.length})</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5 max-h-24 overflow-y-auto">
                      {activeDoc.source_entities.map((ent, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded-md bg-slate-950/80 border border-slate-800 text-[10px] font-mono text-cyan-300/90 hover:border-slate-700 cursor-default"
                          title={`Analyzed entity: ${ent}`}
                        >
                          {ent}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Rendered Markdown Document */}
              <MarkdownRenderer
                content={activeDoc.content}
                title={activeDoc.title}
                downloadFilename={`${activeDoc.document_type.toLowerCase()}-${activeProject.name.toLowerCase().replace(/\s+/g, '-')}.md`}
              />
            </div>
          ) : (
            /* Empty State for this Section */
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-12 text-center min-h-[460px] flex flex-col items-center justify-center">
              <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mb-4 shadow-xl">
                {(() => {
                  const Icon = SECTION_CONFIG[activeSection].icon;
                  return <Icon className="w-8 h-8" />;
                })()}
              </div>

              <h3 className="text-base font-bold text-white mb-1.5">
                No {SECTION_CONFIG[activeSection].label} Documentation Generated Yet
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mb-6 leading-relaxed">
                Generate high-quality {SECTION_CONFIG[activeSection].label.toLowerCase()} documentation using parsed
                entities, dependencies, APIs, and database schemas from <strong className="text-slate-300">{activeProject.name}</strong>.
              </p>

              {isConfigRequired ? (
                <div className="space-y-3">
                  <p className="text-xs text-amber-400 font-semibold">
                    LLM Provider is not configured. Configure your API key to generate this document.
                  </p>
                  <button
                    onClick={() => navigate('/settings')}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all shadow-md shadow-amber-600/25"
                  >
                    <Settings className="w-4 h-4" />
                    <span>Configure AI Provider in Settings</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => handleGenerate(currentSectionType)}
                  disabled={generating}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold transition-all shadow-lg shadow-brand-600/30 disabled:opacity-50"
                >
                  {generating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  <span>{generating ? 'Synthesizing...' : `Generate ${SECTION_CONFIG[activeSection].label} Document`}</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
