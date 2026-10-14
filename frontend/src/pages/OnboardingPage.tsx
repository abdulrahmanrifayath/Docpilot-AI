import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  FolderKanban,
  ExternalLink,
  RefreshCw,
  Download,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  FileText,
  Boxes,
  Compass,
  Layers,
  Database,
  Terminal,
  ShieldCheck,
  ChevronRight,
  ChevronDown,
  ArrowRight,
  BookOpen,
  Cpu,
  Server,
  Play,
  RotateCcw,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import { fetchOnboardingGuide, generateOnboardingGuide } from '../api/client';
import { OnboardingGuideResponse, OnboardingSection, DetectedCommandItem } from '../types';

export const OnboardingPage: React.FC = () => {
  const { activeProject, projects, setActiveProject } = useProjects();
  const [guide, setGuide] = useState<OnboardingGuideResponse | null>(null);
  const [activeSectionKey, setActiveSectionKey] = useState<string>('overview');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [completedSections, setCompletedSections] = useState<Record<string, boolean>>({});

  // Load completed sections from localStorage when project changes
  useEffect(() => {
    if (activeProject?.id) {
      const saved = localStorage.getItem(`onboarding_completed_${activeProject.id}`);
      if (saved) {
        try {
          setCompletedSections(JSON.parse(saved));
        } catch {
          setCompletedSections({});
        }
      } else {
        setCompletedSections({});
      }
    }
  }, [activeProject?.id]);

  // Load guide for active project
  useEffect(() => {
    let isCancelled = false;

    if (!activeProject?.id) {
      setGuide(null);
      return;
    }

    const loadGuide = async () => {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const data = await fetchOnboardingGuide(activeProject.id);
        if (!isCancelled) {
          setGuide(data);
          if (data.sections && data.sections.length > 0) {
            setActiveSectionKey(data.sections[0].key);
          }
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error('Failed to load onboarding guide:', err);
          setErrorMsg('Failed to fetch existing guide. Click "Generate Guide" to create one.');
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    loadGuide();

    return () => {
      isCancelled = true;
    };
  }, [activeProject?.id]);

  const handleGenerate = async (force: boolean = true) => {
    if (!activeProject?.id) return;
    setIsGenerating(true);
    setErrorMsg(null);
    try {
      const data = await generateOnboardingGuide(activeProject.id, force);
      setGuide(data);
      if (data.sections && data.sections.length > 0) {
        setActiveSectionKey(data.sections[0].key);
      }
    } catch (err: any) {
      console.error('Error generating onboarding guide:', err);
      setErrorMsg(err.message || 'Failed to generate onboarding guide.');
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleSectionCompleted = (key: string) => {
    if (!activeProject?.id) return;
    const updated = {
      ...completedSections,
      [key]: !completedSections[key],
    };
    setCompletedSections(updated);
    localStorage.setItem(`onboarding_completed_${activeProject.id}`, JSON.stringify(updated));
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleExportMarkdown = () => {
    if (!guide?.markdown_content) return;
    const filename = `${(activeProject?.name || 'project').toLowerCase().replace(/\s+/g, '_')}_onboarding.md`;
    const blob = new Blob([guide.markdown_content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const completedCount = Object.values(completedSections).filter(Boolean).length;
  const totalSections = guide?.sections?.length || 15;
  const progressPercent = Math.min(100, Math.round((completedCount / totalSections) * 100));

  const activeSection = guide?.sections?.find((s) => s.key === activeSectionKey) || guide?.sections?.[0];

  const getSectionIcon = (key: string) => {
    switch (key) {
      case 'overview':
        return BookOpen;
      case 'tech_stack':
        return Cpu;
      case 'repo_structure':
        return FolderKanban;
      case 'prerequisites':
        return CheckCircle2;
      case 'env_setup':
        return FileCode;
      case 'installation':
        return Download;
      case 'database_setup':
        return Database;
      case 'backend_startup':
        return Server;
      case 'frontend_startup':
        return Play;
      case 'important_modules':
        return Boxes;
      case 'auth_flow':
        return ShieldCheck;
      case 'important_apis':
        return Layers;
      case 'dev_workflow':
        return Compass;
      case 'testing':
        return Terminal;
      case 'deployment':
        return Server;
      default:
        return FileText;
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-4">
          <BookOpen className="w-7 h-7" />
        </div>
        <h2 className="text-lg font-bold text-white mb-2">No Active Project Selected</h2>
        <p className="text-xs text-slate-400 mb-6">
          Please select an analyzed repository to generate or view its developer onboarding guide.
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
    <div className="space-y-4 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 p-0.5 shadow-lg shadow-brand-600/20">
            <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center text-brand-400">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">Developer Onboarding Guide</h1>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Phase 13 Live
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Automated, 15-section walkthrough grounded in verified configuration files and repository evidence
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Project Switcher */}
          <select
            value={activeProject.id}
            onChange={(e) => {
              const target = projects.find((p) => p.id === e.target.value);
              if (target) setActiveProject(target);
            }}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium text-slate-200 focus:outline-none focus:border-brand-500 cursor-pointer"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                📁 {p.name}
              </option>
            ))}
          </select>

          {/* Regenerate Button */}
          <button
            onClick={() => handleGenerate(true)}
            disabled={isGenerating || isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin text-brand-400' : ''}`} />
            <span>{isGenerating ? 'Generating...' : 'Regenerate'}</span>
          </button>

          {/* Export Markdown Button */}
          {guide && (
            <button
              onClick={handleExportMarkdown}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-md shadow-brand-600/25 transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Guide (.md)</span>
            </button>
          )}

          {/* Codebase Link */}
          <Link
            to={`/projects/${activeProject.id}`}
            className="inline-flex items-center gap-1.5 p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Inspect Project Codebase"
          >
            <ExternalLink className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Progress Tracking Banner */}
      {guide && (
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md space-y-3">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 font-medium text-slate-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>
                Onboarding Progress: <strong>{completedCount}</strong> of <strong>{totalSections}</strong> sections completed ({progressPercent}%)
              </span>
            </div>
            {guide.version && (
              <span className="text-[11px] text-slate-400 font-mono">
                Guide Version v{guide.version}
              </span>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-emerald-400 transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Detected Tools Pills */}
          {guide.detected_tools && guide.detected_tools.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
                Verified Tooling:
              </span>
              {guide.detected_tools.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300 text-[10px] font-medium"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => handleGenerate(true)}
            className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-[11px]"
          >
            Retry Generate
          </button>
        </div>
      )}

      {/* Main Content Layout: Sidebar Navigation + Active Section Viewer */}
      {isLoading ? (
        <div className="py-24 text-center space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin text-brand-400 mx-auto" />
          <p className="text-sm text-slate-400">Analyzing repository configuration & building guide...</p>
        </div>
      ) : !guide ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900/50 border border-slate-800 space-y-4 max-w-xl mx-auto my-8">
          <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto">
            <Sparkles className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-bold text-white">Generate Developer Onboarding Guide</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            DocPilot AI will inspect your repository's configuration files (package.json, requirements.txt, Docker, docker-compose, Makefile, scripts, etc.) and generate a practical, 15-section guide for new developers.
          </p>
          <button
            onClick={() => handleGenerate(true)}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-brand-600/25 transition-all"
          >
            {isGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>{isGenerating ? 'Analyzing Repository...' : 'Generate Onboarding Guide'}</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column: Interactive Section Navigation */}
          <div className="lg:col-span-4 space-y-2 sticky top-20">
            <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2 pb-1">
                Onboarding Walkthrough (15 Sections)
              </div>

              <div className="space-y-1 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
                {guide.sections.map((s, idx) => {
                  const Icon = getSectionIcon(s.key);
                  const isSelected = s.key === activeSectionKey;
                  const isDone = !!completedSections[s.key];
                  const isMissing = s.is_missing || s.status === 'NOT_DETECTED';

                  return (
                    <div
                      key={s.key}
                      className={`group flex items-center justify-between p-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-brand-600/15 border border-brand-500/40 text-brand-300 font-semibold shadow-sm'
                          : 'bg-slate-900/40 hover:bg-slate-800/80 text-slate-300 border border-transparent'
                      }`}
                      onClick={() => setActiveSectionKey(s.key)}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        {/* Checkbox for progress tracking */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSectionCompleted(s.key);
                          }}
                          className={`w-4 h-4 rounded flex items-center justify-center border transition-colors shrink-0 ${
                            isDone
                              ? 'bg-emerald-500 border-emerald-400 text-slate-950'
                              : 'bg-slate-800 border-slate-700 hover:border-slate-500 text-transparent'
                          }`}
                          title={isDone ? 'Mark uncompleted' : 'Mark completed'}
                        >
                          <Check className="w-3 h-3 stroke-[3]" />
                        </button>

                        <Icon className={`w-4 h-4 shrink-0 ${isSelected ? 'text-brand-400' : 'text-slate-400'}`} />

                        <span className={`truncate text-[11px] ${isDone ? 'line-through text-slate-500' : ''}`}>
                          {s.title}
                        </span>
                      </div>

                      {/* Status indicator */}
                      <div className="flex items-center gap-1.5 shrink-0 ml-1">
                        {isMissing ? (
                          <span
                            className="w-2 h-2 rounded-full bg-slate-600"
                            title="Manual configuration required"
                          />
                        ) : s.status === 'PARTIAL' ? (
                          <span
                            className="w-2 h-2 rounded-full bg-amber-400"
                            title="Partially detected"
                          />
                        ) : (
                          <span
                            className="w-2 h-2 rounded-full bg-emerald-400"
                            title="Verified from repository evidence"
                          />
                        )}
                        <ChevronRight className={`w-3.5 h-3.5 ${isSelected ? 'text-brand-400' : 'text-slate-600'}`} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Active Section Interactive Card */}
          <div className="lg:col-span-8 space-y-4">
            {activeSection && (
              <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-5">
                {/* Section Header */}
                <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-white tracking-tight">{activeSection.title}</h2>
                      {activeSection.status === 'DETECTED' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Detected & Verified</span>
                        </span>
                      ) : activeSection.status === 'PARTIAL' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          <AlertTriangle className="w-3 h-3" />
                          <span>Partial Evidence</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                          <span>Manual Configuration</span>
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Grounded guidance derived strictly from analyzed repository configuration files.
                    </p>
                  </div>

                  {/* Mark as Completed Button */}
                  <button
                    onClick={() => toggleSectionCompleted(activeSection.key)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                      completedSections[activeSection.key]
                        ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>{completedSections[activeSection.key] ? 'Completed ✓' : 'Mark Completed'}</span>
                  </button>
                </div>

                {/* Verified Commands Cards */}
                {activeSection.detected_commands && activeSection.detected_commands.length > 0 && (
                  <div className="space-y-3">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-brand-400" />
                      <span>Verified Setup & Execution Commands ({activeSection.detected_commands.length})</span>
                    </div>

                    <div className="space-y-2.5">
                      {activeSection.detected_commands.map((cmd, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-xl border border-slate-800 bg-slate-950/80 p-3.5 space-y-2 transition-all hover:border-slate-700"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[11px] text-slate-300 font-medium">{cmd.description}</span>
                            <div className="flex items-center gap-2">
                              {cmd.source_file && (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                                  <FileCode className="w-3 h-3 text-brand-400" />
                                  <span>{cmd.source_file}</span>
                                </span>
                              )}
                              {cmd.verified && (
                                <span className="inline-flex items-center gap-0.5 text-[10px] text-emerald-400 font-semibold">
                                  <CheckCircle2 className="w-3 h-3" />
                                  <span>Verified</span>
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Command Line with Copy */}
                          <div className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 font-mono text-xs text-brand-300">
                            <span className="truncate">{cmd.command}</span>
                            <button
                              onClick={() => handleCopy(cmd.command, `${activeSection.key}_${cIdx}`)}
                              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors shrink-0"
                              title="Copy command"
                            >
                              {copiedText === `${activeSection.key}_${cIdx}` ? (
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Section Markdown Body */}
                <div className="p-4 rounded-2xl bg-slate-950/40 border border-slate-800/80 text-xs leading-relaxed text-slate-300 whitespace-pre-wrap font-sans space-y-2">
                  {activeSection.content}
                </div>

                {/* Bottom Navigation Buttons between sections */}
                <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
                  {(() => {
                    const currentIndex = guide.sections.findIndex((s) => s.key === activeSection.key);
                    const prevSection = currentIndex > 0 ? guide.sections[currentIndex - 1] : null;
                    const nextSection = currentIndex < guide.sections.length - 1 ? guide.sections[currentIndex + 1] : null;

                    return (
                      <>
                        {prevSection ? (
                          <button
                            onClick={() => setActiveSectionKey(prevSection.key)}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
                          >
                            <span>← {prevSection.title}</span>
                          </button>
                        ) : (
                          <div />
                        )}

                        {nextSection ? (
                          <button
                            onClick={() => setActiveSectionKey(nextSection.key)}
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white shadow-md shadow-brand-600/20 transition-all"
                          >
                            <span>Next: {nextSection.title} →</span>
                          </button>
                        ) : (
                          <button
                            onClick={handleExportMarkdown}
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-md shadow-emerald-600/20 transition-all"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>Export Completed Guide</span>
                          </button>
                        )}
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
