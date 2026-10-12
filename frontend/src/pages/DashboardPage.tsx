import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  GitBranch,
  FolderGit2,
  Plus,
  Trash2,
  ArrowRight,
  Code2,
  FileCode,
  Layers,
  Database,
  Globe,
  Loader2,
  Sparkles,
  BookOpen,
  CheckCircle2,
} from 'lucide-react';
import { Repository } from '../types';
import { fetchRepositories, uploadZip, cloneGit, deleteRepository } from '../api/client';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [modalTab, setModalTab] = useState<'zip' | 'git'>('zip');

  // Form states
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [gitUrl, setGitUrl] = useState<string>('');
  const [repoName, setRepoName] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadRepos();
    // Poll repositories every 3 seconds to update running progress
    const timer = setInterval(loadRepos, 3000);
    return () => clearInterval(timer);
  }, []);

  const loadRepos = async () => {
    try {
      const data = await fetchRepositories();
      setRepositories(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadZip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await uploadZip(selectedFile, repoName || undefined);
      setIsModalOpen(false);
      setSelectedFile(null);
      setRepoName('');
      loadRepos();
      navigate(`/repository/${created.id}`);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloneGit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim()) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const created = await cloneGit(gitUrl, repoName || undefined);
      setIsModalOpen(false);
      setGitUrl('');
      setRepoName('');
      loadRepos();
      navigate(`/repository/${created.id}`);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Git clone failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this repository?')) return;
    try {
      await deleteRepository(id);
      loadRepos();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Hero Header */}
      <div className="relative rounded-3xl p-8 sm:p-12 mb-10 overflow-hidden bg-gradient-to-br from-brand-950/70 via-slate-900 to-[#0b0f19] border border-brand-500/20 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-300 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Autonomous Repository Intelligence</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-4">
            Transform Any Codebase Into <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 via-indigo-300 to-cyan-400">Developer Knowledge</span>
          </h1>
          <p className="text-slate-300 text-sm sm:text-base leading-relaxed mb-8">
            DocPilot AI automatically parses your software project, maps its architecture, extracts APIs & database models, synthesizes comprehensive documentation, and grounds an interactive AI assistant.
          </p>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-brand-500/25 transition-all flex items-center gap-2 group"
            >
              <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform" />
              <span>Analyze New Repository</span>
            </button>
          </div>
        </div>
      </div>

      {/* Repositories Section */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Analyzed Repositories</h2>
          <p className="text-xs text-slate-400 mt-0.5">Explore documentation, diagrams, and knowledge graphs</p>
        </div>
        <span className="text-xs font-mono text-slate-400 bg-slate-800 px-3 py-1 rounded-full">
          {repositories.length} {repositories.length === 1 ? 'Repository' : 'Repositories'}
        </span>
      </div>

      {loading ? (
        <div className="py-20 text-center">
          <Loader2 className="w-8 h-8 text-brand-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-400">Loading repositories...</p>
        </div>
      ) : repositories.length === 0 ? (
        <div className="py-16 text-center border-2 border-dashed border-slate-800 rounded-3xl bg-slate-900/20 p-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-4">
            <FolderGit2 className="w-7 h-7 text-brand-400" />
          </div>
          <h3 className="text-base font-bold text-white mb-2">No Repositories Analyzed Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Upload a local project ZIP or paste a GitHub repository link to begin automatic documentation synthesis.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-md shadow-brand-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Analyze First Repository</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {repositories.map((repo) => {
            const isAnalyzing = repo.status === 'analyzing' || repo.status === 'pending';
            const topLangs = Object.entries(repo.languages || {}).slice(0, 3);

            return (
              <div
                key={repo.id}
                onClick={() => navigate(`/repository/${repo.id}`)}
                className="group relative bg-[#111827]/80 hover:bg-slate-800/60 border border-slate-800 hover:border-brand-500/40 rounded-2xl p-6 transition-all duration-200 cursor-pointer shadow-lg hover:shadow-brand-500/10 flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 group-hover:border-brand-500/40 transition-colors">
                        {repo.source_type === 'git' ? (
                          <GitBranch className="w-4 h-4 text-cyan-400" />
                        ) : (
                          <Upload className="w-4 h-4 text-brand-400" />
                        )}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-white group-hover:text-brand-300 transition-colors truncate max-w-[180px]">
                          {repo.name}
                        </h3>
                        <p className="text-[11px] text-slate-400 font-mono capitalize">
                          {repo.source_type} source
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={(e) => handleDelete(e, repo.id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Delete Repository"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Languages Tags */}
                  {topLangs.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-5">
                      {topLangs.map(([lang, stat]) => (
                        <span
                          key={lang}
                          className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700/60 text-[10px] font-semibold text-slate-300"
                        >
                          {lang} ({stat.percent}%)
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-3 gap-2 py-3 px-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 mb-5 text-center">
                    <div>
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">Lines</p>
                      <p className="text-xs font-bold text-white mt-0.5">
                        {repo.stats?.lines?.toLocaleString() || 0}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">Files</p>
                      <p className="text-xs font-bold text-white mt-0.5">{repo.stats?.files || 0}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">APIs</p>
                      <p className="text-xs font-bold text-cyan-400 mt-0.5">{repo.stats?.apis || 0}</p>
                    </div>
                  </div>
                </div>

                {/* Progress / Status Bottom */}
                <div>
                  {isAnalyzing ? (
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1.5 font-medium">
                        <span className="text-brand-300 animate-pulse truncate max-w-[200px]">
                          {repo.current_step}
                        </span>
                        <span className="text-slate-400 font-mono">{repo.progress_percent}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 rounded-full transition-all duration-300"
                          style={{ width: `${repo.progress_percent}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between text-xs pt-3 border-t border-slate-800 text-slate-400 group-hover:text-brand-300 transition-colors">
                      <span className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Documentation Ready</span>
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload / Clone Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-[#0f172a] border border-slate-800 rounded-3xl p-6 shadow-2xl relative">
            <h3 className="text-lg font-bold text-white tracking-tight mb-2">Analyze New Repository</h3>
            <p className="text-xs text-slate-400 mb-6">
              Select an ingest method to execute the 11-stage static intelligence pipeline.
            </p>

            {/* Modal Tabs */}
            <div className="grid grid-cols-2 p-1 bg-slate-900 rounded-xl mb-6 border border-slate-800">
              <button
                type="button"
                onClick={() => setModalTab('zip')}
                className={`py-2 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-2 ${
                  modalTab === 'zip' ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload ZIP File</span>
              </button>
              <button
                type="button"
                onClick={() => setModalTab('git')}
                className={`py-2 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-2 ${
                  modalTab === 'git' ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Clone Git Repo</span>
              </button>
            </div>

            {errorMsg && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {errorMsg}
              </div>
            )}

            {modalTab === 'zip' ? (
              <form onSubmit={handleUploadZip} className="space-y-4">
                <div className="border-2 border-dashed border-slate-700 hover:border-brand-500 rounded-2xl p-6 text-center transition-colors">
                  <input
                    type="file"
                    id="zipFileInput"
                    accept=".zip"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                  <label htmlFor="zipFileInput" className="cursor-pointer block">
                    <Upload className="w-8 h-8 text-brand-400 mx-auto mb-2" />
                    <span className="text-xs font-semibold text-white block">
                      {selectedFile ? selectedFile.name : 'Click to select project .ZIP archive'}
                    </span>
                    <span className="text-[10px] text-slate-500 block mt-1">
                      Max file size: 100MB · Supported formats: .zip
                    </span>
                  </label>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Project Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    placeholder="e.g. MyAwesomeService"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!selectedFile || submitting}
                    className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-500/20 flex items-center gap-2"
                  >
                    {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>{submitting ? 'Uploading...' : 'Start Pipeline'}</span>
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleCloneGit} className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Git Repository URL
                  </label>
                  <input
                    type="url"
                    required
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    placeholder="https://github.com/fastapi/fastapi"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">
                    Project Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    placeholder="e.g. FastAPI Core"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!gitUrl || submitting}
                    className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-500/20 flex items-center gap-2"
                  >
                    {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>{submitting ? 'Cloning...' : 'Start Pipeline'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
