import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  Plus,
  Trash2,
  ExternalLink,
  Archive,
  GitBranch,
  HardDrive,
  RefreshCw,
  Search,
  AlertCircle,
  CheckCircle2,
  Upload,
  X,
  Loader2,
  Clock,
  ArrowRight,
  Star,
  GitFork,
  Shield,
  Check,
} from 'lucide-react';
import { useProjects } from '../context/ProjectContext';
import {
  createProject,
  uploadProjectZip,
  cloneProjectGit,
  deleteProject,
  validateGitHubRepo,
} from '../api/client';
import { Project, GitHubValidateResponse } from '../types';

export const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const { projects, refreshProjects, loading, setActiveProject } = useProjects();

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [sourceType, setSourceType] = useState<'zip' | 'git'>('zip');
  const [projectName, setProjectName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [gitUrl, setGitUrl] = useState<string>('');
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [gitToken, setGitToken] = useState<string>('');
  const [showTokenField, setShowTokenField] = useState<boolean>(false);
  const [validatingGit, setValidatingGit] = useState<boolean>(false);
  const [validatedRepo, setValidatedRepo] = useState<GitHubValidateResponse | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [modalStatusMsg, setModalStatusMsg] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  // Filter / Search State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (p.source_url && p.source_url.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleValidateGitHub = async () => {
    if (!gitUrl.trim()) {
      setModalError('Please enter a GitHub repository URL or owner/repo shorthand');
      return;
    }
    setValidatingGit(true);
    setModalError(null);
    try {
      const res = await validateGitHubRepo({
        url: gitUrl.trim(),
        token: gitToken.trim() || undefined,
      });
      setValidatedRepo(res);
      const initialBranch = res.default_branch || res.selected_branch || 'main';
      setSelectedBranch(initialBranch);
      if (!projectName.trim()) {
        setProjectName(res.repo);
      }
      if (!description.trim() && res.description) {
        setDescription(res.description);
      }
    } catch (err: any) {
      setValidatedRepo(null);
      setModalError(err.message || 'GitHub repository validation failed');
    } finally {
      setValidatingGit(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) {
      setModalError('Project name is required');
      return;
    }

    if (sourceType === 'zip' && !zipFile) {
      setModalError('Please select a ZIP file to upload');
      return;
    }

    if (sourceType === 'git' && !gitUrl.trim()) {
      setModalError('Please enter a GitHub repository URL');
      return;
    }

    setSubmitting(true);
    setModalError(null);
    setModalStatusMsg('Creating project record...');

    try {
      // 1. Create the Project
      const branchToUse = sourceType === 'git' ? (selectedBranch.trim() || 'main') : undefined;
      const newProj = await createProject({
        name: projectName.trim(),
        description: description.trim() || undefined,
        source_type: sourceType,
        source_url: sourceType === 'git' ? (validatedRepo?.clone_url || gitUrl.trim()) : undefined,
        branch: branchToUse,
      });

      // 2. Perform Upload or Clone
      if (sourceType === 'zip' && zipFile) {
        setModalStatusMsg('Uploading and extracting ZIP archive...');
        await uploadProjectZip(newProj.id, zipFile);
      } else if (sourceType === 'git' && gitUrl) {
        setModalStatusMsg(`Cloning branch '${branchToUse}' from GitHub...`);
        await cloneProjectGit(newProj.id, gitUrl.trim(), branchToUse);
      }

      setModalStatusMsg('Project setup complete!');
      await refreshProjects();
      setActiveProject(newProj);

      // Close modal and navigate to details
      setTimeout(() => {
        setIsModalOpen(false);
        resetForm();
        navigate(`/projects/${newProj.id}`);
      }, 700);
    } catch (err: any) {
      console.error(err);
      setModalError(err.message || 'Failed to complete project setup');
      setSubmitting(false);
      refreshProjects();
    }
  };

  const resetForm = () => {
    setProjectName('');
    setDescription('');
    setZipFile(null);
    setGitUrl('');
    setSelectedBranch('main');
    setGitToken('');
    setShowTokenField(false);
    setValidatingGit(false);
    setValidatedRepo(null);
    setModalError(null);
    setModalStatusMsg(null);
    setSubmitting(false);
  };

  const handleDelete = async (e: React.MouseEvent, id: string, name: string) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete project "${name}"? All isolated files will be removed.`)) {
      return;
    }
    try {
      await deleteProject(id);
      await refreshProjects();
    } catch (err: any) {
      alert(`Delete failed: ${err.message || err}`);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Project Management</h1>
          <p className="text-xs text-slate-400 mt-1">
            Ingest and manage source code projects for deep architectural analysis and automated documentation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshProjects()}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => {
              resetForm();
              setIsModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search projects by name or URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-[11px] font-semibold text-slate-400">Filter Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 cursor-pointer"
          >
            <option value="ALL">All Statuses</option>
            <option value="READY">Ready</option>
            <option value="UPLOADING">Uploading</option>
            <option value="CLONING">Cloning</option>
            <option value="ANALYZED">Analyzed</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* Projects Table */}
      {filteredProjects.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center">
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-3">
            <FolderKanban className="w-7 h-7" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">
            {searchQuery || statusFilter !== 'ALL' ? 'No matching projects found' : 'No projects created yet'}
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mb-5">
            {searchQuery || statusFilter !== 'ALL'
              ? 'Try modifying your search or status filter'
              : 'Create your first project by uploading a ZIP archive or connecting a public GitHub repository.'}
          </p>
          {!searchQuery && statusFilter === 'ALL' && (
            <button
              onClick={() => {
                resetForm();
                setIsModalOpen(true);
              }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-4">Project Name</th>
                <th className="px-5 py-4">Source Type</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Created Date</th>
                <th className="px-5 py-4">Last Analysis Date</th>
                <th className="px-5 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredProjects.map((p) => {
                const isReady = p.status === 'READY' || p.status === 'ANALYZED';
                const isPending = p.status === 'UPLOADING' || p.status === 'CLONING' || p.status === 'ANALYZING';
                const isFailed = p.status === 'FAILED';

                return (
                  <tr
                    key={p.id}
                    onClick={() => {
                      setActiveProject(p);
                      navigate(`/projects/${p.id}`);
                    }}
                    className="hover:bg-slate-800/50 transition-colors cursor-pointer group"
                  >
                    <td className="px-5 py-4">
                      <div className="font-bold text-white text-sm group-hover:text-brand-400 transition-colors">
                        {p.name}
                      </div>
                      {p.description && (
                        <p className="text-[11px] text-slate-400 truncate max-w-sm mt-0.5">{p.description}</p>
                      )}
                      {p.source_url && (
                        <p className="text-[10px] text-slate-500 font-mono truncate max-w-xs mt-0.5">
                          {p.source_url}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] font-semibold text-slate-300 capitalize">
                        {p.source_type === 'zip' ? (
                          <Archive className="w-3.5 h-3.5 text-brand-400" />
                        ) : p.source_type === 'git' ? (
                          <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
                        ) : (
                          <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
                        )}
                        <span>{p.source_type}</span>
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
                          isReady
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : isPending
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
                            : isFailed
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                        {isReady && <CheckCircle2 className="w-3 h-3" />}
                        {isFailed && <AlertCircle className="w-3 h-3" />}
                        <span>{p.status}</span>
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-400">
                      {new Date(p.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="px-5 py-4 text-slate-400">
                      {p.last_analyzed_at ? (
                        new Date(p.last_analyzed_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      ) : (
                        <span className="text-slate-600 italic">Not yet analyzed</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <Link
                          to={`/projects/${p.id}`}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                          title="View Details & Files"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={(e) => handleDelete(e, p.id, p.name)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="Delete Project"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* New Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-[#0f172a] border border-slate-800 shadow-2xl p-6 relative">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center">
                  <FolderKanban className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Create New Project</h3>
                  <p className="text-[11px] text-slate-400">Ingest source code from ZIP or GitHub</p>
                </div>
              </div>
              <button
                disabled={submitting}
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error & Status Alerts */}
            {modalError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{modalError}</span>
              </div>
            )}
            {modalStatusMsg && (
              <div className="mt-4 p-3 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-300 text-xs flex items-center gap-2">
                <Loader2 className="w-4 h-4 shrink-0 text-brand-400 animate-spin" />
                <span>{modalStatusMsg}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleCreateProject} className="mt-4 space-y-4">
              {/* Project Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Project Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. My Fastapi Backend"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description <span className="text-slate-500 text-[10px]">(Optional)</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="Brief summary of this codebase..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors resize-none"
                />
              </div>

              {/* Source Type Selector Tabs */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Source Type <span className="text-rose-400">*</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSourceType('zip')}
                    className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      sourceType === 'zip'
                        ? 'bg-brand-600/20 border-brand-500/50 text-brand-300 shadow-sm'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Archive className="w-4 h-4" />
                    <span>ZIP Upload</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceType('git')}
                    className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      sourceType === 'git'
                        ? 'bg-brand-600/20 border-brand-500/50 text-brand-300 shadow-sm'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    <GitBranch className="w-4 h-4" />
                    <span>Public GitHub</span>
                  </button>
                </div>
              </div>

              {/* Source-specific input */}
              {sourceType === 'zip' ? (
                <div className="p-4 rounded-xl border border-dashed border-slate-700 bg-slate-900/60 text-center">
                  <Upload className="w-7 h-7 text-slate-400 mx-auto mb-2" />
                  <input
                    type="file"
                    id="zip-upload"
                    accept=".zip,application/zip"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        const file = e.target.files[0];
                        setZipFile(file);
                        if (!projectName) {
                          setProjectName(file.name.replace(/\.zip$/i, ''));
                        }
                      }
                    }}
                    className="hidden"
                  />
                  <label
                    htmlFor="zip-upload"
                    className="cursor-pointer text-xs font-semibold text-brand-400 hover:text-brand-300 block mb-1"
                  >
                    {zipFile ? `Selected: ${zipFile.name}` : 'Click to select ZIP archive'}
                  </label>
                  <p className="text-[10px] text-slate-500">
                    Maximum 100MB • Auto-extracts & sanitizes node_modules, .venv, etc.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      GitHub Repository URL or Shorthand
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="https://github.com/owner/repo or owner/repo"
                        value={gitUrl}
                        onChange={(e) => {
                          setGitUrl(e.target.value);
                          setValidatedRepo(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleValidateGitHub();
                          }
                        }}
                        className="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors"
                      />
                      <button
                        type="button"
                        onClick={handleValidateGitHub}
                        disabled={validatingGit || !gitUrl.trim()}
                        className="px-3.5 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-brand-300 border border-slate-700 transition-all flex items-center gap-1.5 disabled:opacity-50 shrink-0"
                      >
                        {validatingGit ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5 text-brand-400" />
                        )}
                        <span>{validatingGit ? 'Validating...' : 'Validate Repo'}</span>
                      </button>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[10px] text-slate-500">
                      <span>Public repositories clone without authentication</span>
                      <button
                        type="button"
                        onClick={() => setShowTokenField(!showTokenField)}
                        className="text-brand-400 hover:text-brand-300 font-medium"
                      >
                        {showTokenField ? 'Hide Token' : 'Private Repo Token (Optional)'}
                      </button>
                    </div>
                  </div>

                  {/* Optional GitHub Token */}
                  {showTokenField && (
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
                        <Shield className="w-3.5 h-3.5 text-brand-400" />
                        <span>GitHub Personal Access Token (Ephemeral)</span>
                      </div>
                      <input
                        type="password"
                        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx (Never stored in plain text)"
                        value={gitToken}
                        onChange={(e) => setGitToken(e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors font-mono"
                      />
                      <p className="text-[10px] text-slate-500">
                        DocPilot executes in-memory verification only and never persists plain-text tokens.
                      </p>
                    </div>
                  )}

                  {/* Validated Repository Metadata Card */}
                  {validatedRepo && (
                    <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/30 space-y-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-white flex items-center gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                              <span>{validatedRepo.full_name}</span>
                            </span>
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {validatedRepo.is_private ? 'Private' : 'Public'}
                            </span>
                            {validatedRepo.language && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                                {validatedRepo.language}
                              </span>
                            )}
                          </div>
                          {validatedRepo.description && (
                            <p className="text-[11px] text-slate-300 mt-1 line-clamp-2">
                              {validatedRepo.description}
                            </p>
                          )}
                        </div>
                        <a
                          href={validatedRepo.clone_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
                          title="Open on GitHub"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>

                      {/* Stats row */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                        <span className="flex items-center gap-1">
                          <Star className="w-3 h-3 text-amber-400" />
                          <span>{validatedRepo.stars_count.toLocaleString()} stars</span>
                        </span>
                        <span className="flex items-center gap-1">
                          <GitFork className="w-3 h-3 text-slate-400" />
                          <span>{validatedRepo.forks_count.toLocaleString()} forks</span>
                        </span>
                        {validatedRepo.latest_commit_sha && (
                          <span className="font-mono text-[10px] text-slate-500">
                            Commit: {validatedRepo.latest_commit_sha.slice(0, 7)}
                          </span>
                        )}
                        {validatedRepo.rate_limit_remaining !== null && validatedRepo.rate_limit_remaining !== undefined && (
                          <span className="text-[10px] text-slate-500 ml-auto">
                            Rate Limit: {validatedRepo.rate_limit_remaining} left
                          </span>
                        )}
                      </div>

                      {/* Branch Selection Dropdown */}
                      <div className="pt-2 border-t border-slate-800/80">
                        <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                          <GitBranch className="w-3.5 h-3.5 text-brand-400" />
                          <span>Target Branch to Clone & Track</span>
                        </label>
                        <select
                          value={selectedBranch}
                          onChange={(e) => setSelectedBranch(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500 transition-colors"
                        >
                          {validatedRepo.branches.map((b) => (
                            <option key={b} value={b}>
                              {b} {b === validatedRepo.default_branch ? '(default branch)' : ''}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 transition-all disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{submitting ? 'Creating Project...' : 'Create Project'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
