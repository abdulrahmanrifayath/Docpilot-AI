import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Sparkles,
  FileCode,
  BookOpen,
  Database,
  Layers,
  Rocket,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  Eye,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Search,
  Filter,
  X,
  FileCheck,
  FileType,
  Printer,
  Copy,
  Check,
} from 'lucide-react';
import {
  Project,
  TechnicalReportResponse,
  ReportType,
  ReportSectionItem,
} from '../types';
import {
  generateProjectReport,
  fetchProjectReports,
  downloadProjectReport,
  getReportExportUrl,
} from '../api/client';
import { MarkdownRenderer } from './MarkdownRenderer';

interface ReportsExportCenterProps {
  project: Project;
}

export const ReportsExportCenter: React.FC<ReportsExportCenterProps> = ({ project }) => {
  const [reports, setReports] = useState<TechnicalReportResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [activeType, setActiveType] = useState<ReportType>('FULL_TECHNICAL_REPORT');
  const [customTitle, setCustomTitle] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Preview Modal State
  const [selectedReport, setSelectedReport] = useState<TechnicalReportResponse | null>(null);
  const [previewTab, setPreviewTab] = useState<'formatted' | 'raw_markdown'>('formatted');
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (project?.id) {
      loadReports(project.id);
    }
  }, [project?.id]);

  const loadReports = async (projectId: string) => {
    setLoading(true);
    try {
      const data = await fetchProjectReports(projectId);
      setReports(data);
    } catch (err: any) {
      console.warn('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (typeToGen?: ReportType) => {
    const reportType = typeToGen || activeType;
    setGenerating(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const newReport = await generateProjectReport(project.id, {
        report_type: reportType,
        title: customTitle.trim() || undefined,
      });
      setSuccessMsg(`Generated "${newReport.title}" successfully!`);
      setCustomTitle('');
      await loadReports(project.id);
      setSelectedReport(newReport);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async (
    report: TechnicalReportResponse,
    format: 'markdown' | 'html' | 'pdf'
  ) => {
    setDownloadingFormat(`${report.id}_${format}`);
    try {
      await downloadProjectReport(project.id, report.id, format);
    } catch (err: any) {
      alert(`Export failed: ${err.message || err}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleCopyMarkdown = (content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const reportTypeCards: Array<{
    type: ReportType;
    label: string;
    icon: React.ReactNode;
    desc: string;
    badge: string;
    sectionsCount: string;
    color: string;
  }> = [
    {
      type: 'FULL_TECHNICAL_REPORT',
      label: 'Full Technical Report',
      icon: <FileText className="w-5 h-5 text-brand-400" />,
      desc: 'All 12 architecture sections, executive summary, APIs, database, flows, and risk analysis.',
      badge: 'Comprehensive Audit',
      sectionsCount: '12 Sections',
      color: 'border-brand-500/40 bg-brand-500/10 hover:border-brand-500',
    },
    {
      type: 'README',
      label: 'Project README',
      icon: <FileCode className="w-5 h-5 text-emerald-400" />,
      desc: 'High-impact GitHub-ready README.md with badges, architecture highlights, and quick start.',
      badge: 'GitHub Standard',
      sectionsCount: '3 Sections',
      color: 'border-emerald-500/40 bg-emerald-500/10 hover:border-emerald-500',
    },
    {
      type: 'API_DOCUMENTATION',
      label: 'API Documentation',
      icon: <Rocket className="w-5 h-5 text-violet-400" />,
      desc: 'Complete HTTP route specifications, parameters, authentication requirements, and handlers.',
      badge: 'API Reference',
      sectionsCount: '2 Sections',
      color: 'border-violet-500/40 bg-violet-500/10 hover:border-violet-500',
    },
    {
      type: 'ARCHITECTURE',
      label: 'Architecture Documentation',
      icon: <Layers className="w-5 h-5 text-indigo-400" />,
      desc: 'System topology, modular component breakdown, and embedded Mermaid architecture diagrams.',
      badge: 'System Design',
      sectionsCount: 'Multi-Diagram',
      color: 'border-indigo-500/40 bg-indigo-500/10 hover:border-indigo-500',
    },
    {
      type: 'DATABASE',
      label: 'Database Documentation',
      icon: <Database className="w-5 h-5 text-amber-400" />,
      desc: 'Data dictionary, ORM entities, column constraints, primary/foreign keys, and ER diagrams.',
      badge: 'Data Layer',
      sectionsCount: 'Schema & ERD',
      color: 'border-amber-500/40 bg-amber-500/10 hover:border-amber-500',
    },
    {
      type: 'ONBOARDING',
      label: 'Developer Onboarding Guide',
      icon: <BookOpen className="w-5 h-5 text-teal-400" />,
      desc: 'Developer onboarding guide grounded in detected package manifests, Docker, and scripts.',
      badge: 'Team Ramp-Up',
      sectionsCount: 'Setup Guide',
      color: 'border-teal-500/40 bg-teal-500/10 hover:border-teal-500',
    },
  ];

  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-brand-400" />
              <span>Technical Reports & Documentation Export</span>
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20">
              Phase 16
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Generate, inspect, and export publication-ready technical reports grounded in verified repository evidence.
          </p>
        </div>

        {/* Classification Legend */}
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
            🔍 Detected Evidence
          </span>
          <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-medium">
            🤖 AI Synthesis
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
            🔗 Inferred Graph
          </span>
        </div>
      </div>

      {/* Report Generator Selector Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Select Report Type to Generate
          </h3>
          <span className="text-[11px] text-slate-500">
            Exports support Markdown, HTML, and PDF
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {reportTypeCards.map((c) => {
            const isSelected = activeType === c.type;
            return (
              <div
                key={c.type}
                onClick={() => setActiveType(c.type)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? `${c.color} shadow-lg ring-1 ring-brand-500/50`
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    {c.icon}
                    <h4 className="text-xs font-bold text-white">{c.label}</h4>
                  </div>
                  <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    {c.sectionsCount}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">
                  {c.desc}
                </p>
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[10px]">
                  <span className="text-slate-500 font-medium">{c.badge}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleGenerate(c.type);
                    }}
                    disabled={generating}
                    className="flex items-center gap-1 font-semibold text-brand-400 hover:text-brand-300"
                  >
                    <span>Generate Now</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Custom Title & Primary Action */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <input
            type="text"
            placeholder="Custom Report Title (Optional - e.g. Executive Architecture Audit v1.0)"
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
            className="flex-1 w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors"
          />
          <button
            onClick={() => handleGenerate()}
            disabled={generating}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all disabled:opacity-50 shrink-0"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>{generating ? 'Compiling Report...' : 'Generate Selected Report'}</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-slate-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-slate-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Generated Reports Table */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Generated Reports & Export Catalog ({reports.length})
          </h3>
          <button
            onClick={() => loadReports(project.id)}
            className="text-[11px] text-slate-400 hover:text-white transition-colors"
          >
            Refresh List
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-brand-400" />
            <span>Loading technical reports catalog...</span>
          </div>
        ) : reports.length === 0 ? (
          <div className="p-8 rounded-xl bg-slate-950/40 border border-slate-800/80 text-center space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-300">No technical reports generated yet</p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              Select one of the report templates above to compile a comprehensive, verified technical document.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/50">
            {reports.map((r) => {
              const createdDate = new Date(r.created_at).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });
              const isPdfDownloading = downloadingFormat === `${r.id}_pdf`;
              const isHtmlDownloading = downloadingFormat === `${r.id}_html`;
              const isMdDownloading = downloadingFormat === `${r.id}_markdown`;

              return (
                <div
                  key={r.id}
                  className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-900/40 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-bold text-white">{r.title}</h4>
                      <span className="px-2 py-0.2 rounded text-[10px] font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20 font-mono">
                        {r.report_type.replace(/_/g, ' ')}
                      </span>
                      {r.commit_sha && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800">
                          {r.commit_sha.slice(0, 7)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{createdDate}</span>
                      </span>
                      <span>•</span>
                      <span>{r.sections?.length || 0} Sections Compiled</span>
                      {r.description && (
                        <>
                          <span>•</span>
                          <span className="truncate max-w-sm text-slate-500">{r.description}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Preview Button */}
                    <button
                      onClick={() => setSelectedReport(r)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
                    >
                      <Eye className="w-3.5 h-3.5 text-brand-400" />
                      <span>Preview</span>
                    </button>

                    {/* Markdown Export */}
                    <button
                      onClick={() => handleExport(r, 'markdown')}
                      disabled={isMdDownloading}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
                      title="Download as GitHub-Flavored Markdown (.md)"
                    >
                      {isMdDownloading ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <FileCode className="w-3 h-3 text-emerald-400" />
                      )}
                      <span>MD</span>
                    </button>

                    {/* HTML Export */}
                    <button
                      onClick={() => handleExport(r, 'html')}
                      disabled={isHtmlDownloading}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition-all disabled:opacity-50"
                      title="Download as standalone HTML with Mermaid diagrams (.html)"
                    >
                      {isHtmlDownloading ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <FileType className="w-3 h-3 text-amber-400" />
                      )}
                      <span>HTML</span>
                    </button>

                    {/* PDF Export */}
                    <button
                      onClick={() => handleExport(r, 'pdf')}
                      disabled={isPdfDownloading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white shadow-sm shadow-rose-600/25 transition-all disabled:opacity-50"
                      title="Download as publication-ready PDF with ReportLab formatting (.pdf)"
                    >
                      {isPdfDownloading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5" />
                      )}
                      <span>PDF</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Interactive Report Preview Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-5xl h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60 shrink-0">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">{selectedReport.title}</h3>
                  <span className="px-2 py-0.2 rounded text-[10px] font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20 font-mono">
                    {selectedReport.report_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>Project: <strong>{project.name}</strong></span>
                  <span>•</span>
                  <span>Branch: <code>{project.branch || 'main'}</code></span>
                  <span>•</span>
                  <span>{selectedReport.sections.length} Sections</span>
                </div>
              </div>

              {/* Top Controls */}
              <div className="flex items-center gap-2">
                {/* View switcher */}
                <div className="flex items-center bg-slate-900 p-0.5 rounded-lg border border-slate-800 text-xs">
                  <button
                    onClick={() => setPreviewTab('formatted')}
                    className={`px-3 py-1 rounded-md font-medium transition-all ${
                      previewTab === 'formatted'
                        ? 'bg-brand-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Rendered Report
                  </button>
                  <button
                    onClick={() => setPreviewTab('raw_markdown')}
                    className={`px-3 py-1 rounded-md font-medium transition-all ${
                      previewTab === 'raw_markdown'
                        ? 'bg-brand-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Raw Markdown
                  </button>
                </div>

                {/* Copy Markdown */}
                <button
                  onClick={() => handleCopyMarkdown(selectedReport.markdown_content)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
                  title="Copy complete markdown source to clipboard"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  <span>{copied ? 'Copied' : 'Copy MD'}</span>
                </button>

                {/* Export Dropdown / Buttons */}
                <button
                  onClick={() => handleExport(selectedReport, 'markdown')}
                  className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
                  title="Export Markdown file"
                >
                  .MD
                </button>
                <button
                  onClick={() => handleExport(selectedReport, 'html')}
                  className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
                  title="Export Standalone HTML file"
                >
                  .HTML
                </button>
                <button
                  onClick={() => handleExport(selectedReport, 'pdf')}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white shadow-md shadow-rose-600/25 transition-all"
                  title="Download Publication-Ready PDF"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>PDF</span>
                </button>

                <button
                  onClick={() => setSelectedReport(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-2"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {previewTab === 'raw_markdown' ? (
                <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {selectedReport.markdown_content}
                </pre>
              ) : (
                <div className="space-y-6 max-w-4xl mx-auto">
                  {selectedReport.sections.map((s, idx) => {
                    const isDetected = s.category === 'detected';
                    const isInferred = s.category === 'inferred';
                    const isAi = s.category === 'ai_generated';

                    return (
                      <div
                        key={s.id || idx}
                        className="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800/80">
                          <h4 className="text-sm font-bold text-white">{s.title}</h4>
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                              isDetected
                                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                : isInferred
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                                : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                            }`}
                          >
                            <span>
                              {isDetected
                                ? '🔍 Detected Evidence'
                                : isInferred
                                ? '🔗 Inferred Graph'
                                : '🤖 AI Synthesis'}
                            </span>
                          </span>
                        </div>
                        <div className="prose prose-invert prose-xs max-w-none">
                          <MarkdownRenderer content={s.content} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
