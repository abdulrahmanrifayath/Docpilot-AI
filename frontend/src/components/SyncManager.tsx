import React, { useState, useEffect } from 'react';
import {
  GitCommit,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  FilePlus,
  FileEdit,
  FileX,
  History,
  Layers,
  Sparkles,
  Server,
  Database,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  Clock,
  Workflow,
  BookOpen,
  GitBranch,
  ExternalLink,
  FolderGit2,
  Globe,
  Loader2,
  Check,
} from 'lucide-react';
import {
  Project,
  ChangeCheckResponse,
  ChangeReportResponse,
  GitHubStatusResponse,
  GitHubRefreshResponse,
} from '../types';
import {
  checkProjectChanges,
  updateProjectDocumentation,
  fetchProjectChanges,
  fetchGitHubStatus,
  refreshGitHubRepo,
} from '../api/client';

interface SyncManagerProps {
  project: Project;
  onSyncComplete?: () => void;
}

export const SyncManager: React.FC<SyncManagerProps> = ({ project, onSyncComplete }) => {
  const [checking, setChecking] = useState<boolean>(false);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [checkResult, setCheckResult] = useState<ChangeCheckResponse | null>(null);
  const [latestReport, setLatestReport] = useState<ChangeReportResponse | null>(null);
  const [history, setHistory] = useState<ChangeReportResponse[]>([]);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [showFilesList, setShowFilesList] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Phase 15: GitHub Integration State
  const isGitProject = project.source_type === 'git' || (project.source_url && project.source_url.includes('github.com'));
  const [githubStatus, setGithubStatus] = useState<GitHubStatusResponse | null>(null);
  const [loadingGithub, setLoadingGithub] = useState<boolean>(false);
  const [refreshingGithub, setRefreshingGithub] = useState<boolean>(false);
  const [selectedBranch, setSelectedBranch] = useState<string>(project.branch || 'main');
  const [forceSyncRemote, setForceSyncRemote] = useState<boolean>(false);
  const [githubSuccessMsg, setGithubSuccessMsg] = useState<string | null>(null);
  const [githubErrorMsg, setGithubErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (project?.id) {
      loadHistory(project.id);
      if (isGitProject) {
        loadGithubStatus(project.id);
      }
    }
  }, [project?.id, isGitProject]);

  const loadGithubStatus = async (projectId: string) => {
    setLoadingGithub(true);
    setGithubErrorMsg(null);
    try {
      const status = await fetchGitHubStatus(projectId);
      setGithubStatus(status);
      if (status.current_branch) {
        setSelectedBranch(status.current_branch);
      }
    } catch (err: any) {
      setGithubErrorMsg(err.message || 'Failed to check GitHub status');
    } finally {
      setLoadingGithub(false);
    }
  };

  const handleRefreshGitHub = async () => {
    setRefreshingGithub(true);
    setGithubErrorMsg(null);
    setGithubSuccessMsg(null);
    try {
      const res = await refreshGitHubRepo(project.id, {
        branch: selectedBranch,
        force_sync: forceSyncRemote,
      });
      setGithubSuccessMsg(res.message);
      await loadGithubStatus(project.id);
      await loadHistory(project.id);
      if (onSyncComplete) {
        onSyncComplete();
      }
    } catch (err: any) {
      setGithubErrorMsg(err.message || 'Failed to refresh repository from GitHub');
    } finally {
      setRefreshingGithub(false);
    }
  };

  const loadHistory = async (projectId: string) => {
    try {
      const records = await fetchProjectChanges(projectId, 5);
      setHistory(records);
      if (records.length > 0 && !latestReport) {
        setLatestReport(records[0]);
      }
    } catch (err: any) {
      console.warn('Failed to load change history:', err);
    }
  };

  const handleCheckChanges = async () => {
    setChecking(true);
    setErrorMsg(null);
    try {
      const res = await checkProjectChanges(project.id);
      setCheckResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to detect changes');
    } finally {
      setChecking(false);
    }
  };

  const handleSyncDocumentation = async (forceAll: boolean = false) => {
    setSyncing(true);
    setErrorMsg(null);
    try {
      const report = await updateProjectDocumentation(project.id, {
        force_all: forceAll,
        regenerate_diagrams: true,
      });
      setLatestReport(report);
      setCheckResult(null); // Clear preview once synced
      await loadHistory(project.id);
      if (onSyncComplete) {
        onSyncComplete();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to synchronize documentation');
    } finally {
      setSyncing(false);
    }
  };

  const commitShaDisplay = project.last_commit_sha
    ? project.last_commit_sha.slice(0, 8)
    : 'Not Recorded';

  const isOutOfSync = checkResult?.has_changes;
  const isSyncing = syncing || project.sync_status === 'SYNCING';

  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 space-y-6">
      {/* Top Header & Commit Tracking Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <RefreshCw className={`w-4 h-4 text-brand-400 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>Change Detection & Documentation Synchronization</span>
            </h2>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                project.sync_status === 'SYNCED' && !isOutOfSync
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : isOutOfSync || project.sync_status === 'OUT_OF_SYNC'
                  ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  : isSyncing
                  ? 'bg-brand-500/10 text-brand-400 border-brand-500/30 animate-pulse'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}
            >
              {project.sync_status === 'SYNCED' && !isOutOfSync && <CheckCircle2 className="w-3 h-3" />}
              {isOutOfSync && <AlertTriangle className="w-3 h-3" />}
              {isSyncing && <RefreshCw className="w-3 h-3 animate-spin" />}
              <span>
                {isSyncing
                  ? 'Synchronizing...'
                  : isOutOfSync
                  ? 'Changes Detected'
                  : project.sync_status || 'In Sync'}
              </span>
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Tracks repository commit diffs, reanalyzes affected files incrementally, and archives previous document versions.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleCheckChanges}
            disabled={checking || isSyncing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all disabled:opacity-50"
            title="Inspect latest commit or working tree for modifications"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
            <span>{checking ? 'Checking Git...' : 'Check for Changes'}</span>
          </button>

          <button
            onClick={() => handleSyncDocumentation(false)}
            disabled={syncing || checking}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-md shadow-brand-600/25 transition-all disabled:opacity-50"
            title="Incrementally reanalyze affected components and update documentation versions"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{syncing ? 'Synchronizing...' : 'Sync Documentation'}</span>
          </button>
        </div>
      </div>

      {/* Commit & Snapshot Metadata Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <GitCommit className="w-4 h-4 text-brand-400" />
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Analyzed Commit</span>
              <p className="text-xs font-mono font-bold text-slate-200">{commitShaDisplay}</p>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20 text-[10px] font-mono">
            HEAD
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Clock className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Last Sync Snapshot</span>
              <p className="text-xs font-medium text-slate-200">
                {project.last_analyzed_at
                  ? new Date(project.last_analyzed_at).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Never'}
              </p>
            </div>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Incremental</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <History className="w-4 h-4 text-indigo-400" />
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Version Strategy</span>
              <p className="text-xs font-medium text-slate-200">Archive Previous Copies</p>
            </div>
          </div>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-[11px] text-brand-400 hover:text-brand-300 font-semibold inline-flex items-center gap-1"
          >
            <span>{showHistory ? 'Hide Audits' : 'View Audits'}</span>
            <ChevronDown className={`w-3 h-3 transition-transform ${showHistory ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* PHASE 15: GITHUB INTEGRATION & REMOTE COMMIT TRACKING CARD */}
      {isGitProject && (
        <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 border border-brand-500/30 shadow-lg space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
                <FolderGit2 className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-1.5">
                    <span>GitHub Remote Integration</span>
                  </h3>
                  {githubStatus?.is_github_repo ? (
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        githubStatus.status === 'BEHIND'
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/40 animate-pulse'
                          : githubStatus.status === 'UP_TO_DATE'
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {githubStatus.status === 'BEHIND' && <AlertTriangle className="w-3 h-3 text-amber-400" />}
                      {githubStatus.status === 'UP_TO_DATE' && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                      <span>
                        {githubStatus.status === 'BEHIND'
                          ? `${githubStatus.commits_behind} Commit(s) Behind Remote`
                          : githubStatus.status === 'UP_TO_DATE'
                          ? 'Synchronized with Origin'
                          : githubStatus.status}
                      </span>
                    </span>
                  ) : null}
                </div>
                {githubStatus?.repository_url && (
                  <div className="flex items-center gap-2 mt-0.5">
                    <a
                      href={githubStatus.repository_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                    >
                      <span>
                        {githubStatus.owner}/{githubStatus.repo_name}
                      </span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => loadGithubStatus(project.id)}
                disabled={loadingGithub || refreshingGithub}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all disabled:opacity-50"
                title="Query GitHub API / remote origin for new commits"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingGithub ? 'animate-spin' : ''}`} />
                <span>{loadingGithub ? 'Checking...' : 'Check Remote'}</span>
              </button>

              <button
                type="button"
                onClick={handleRefreshGitHub}
                disabled={refreshingGithub || loadingGithub}
                className="flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-600/25 transition-all disabled:opacity-50"
                title="Pull latest remote commits and automatically synchronize documentation"
              >
                {refreshingGithub ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <GitBranch className="w-3.5 h-3.5" />
                )}
                <span>{refreshingGithub ? 'Pulling & Syncing...' : 'Pull & Refresh'}</span>
              </button>
            </div>
          </div>

          {/* GitHub Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            {/* Branch selector / active branch */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider flex items-center gap-1">
                <GitBranch className="w-3 h-3 text-brand-400" />
                <span>Tracking Branch</span>
              </span>
              {githubStatus?.available_branches && githubStatus.available_branches.length > 1 ? (
                <select
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                  disabled={refreshingGithub}
                  className="w-full mt-0.5 px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
                >
                  {githubStatus.available_branches.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="font-mono font-bold text-slate-200">
                  {selectedBranch || project.branch || 'main'}
                </p>
              )}
            </div>

            {/* Local Commit SHA */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Local Commit</span>
              <p className="font-mono font-bold text-slate-200">
                {githubStatus?.local_commit_sha ? githubStatus.local_commit_sha.slice(0, 8) : commitShaDisplay}
              </p>
            </div>

            {/* Remote Commit SHA */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Remote Origin Commit</span>
              <div className="flex items-center justify-between">
                <p className="font-mono font-bold text-brand-300">
                  {githubStatus?.remote_commit_sha ? githubStatus.remote_commit_sha.slice(0, 8) : 'Pending Check'}
                </p>
                {githubStatus?.local_commit_sha && githubStatus?.remote_commit_sha && (
                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-semibold font-mono ${
                      githubStatus.local_commit_sha === githubStatus.remote_commit_sha
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-amber-500/10 text-amber-400'
                    }`}
                  >
                    {githubStatus.local_commit_sha === githubStatus.remote_commit_sha ? 'MATCH' : 'DIFF'}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Force Sync Option */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="force-sync-checkbox"
              checked={forceSyncRemote}
              onChange={(e) => setForceSyncRemote(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-brand-500 focus:ring-0"
            />
            <label htmlFor="force-sync-checkbox" className="text-[11px] text-slate-400 cursor-pointer">
              Force regeneration of all documentation and diagrams even if commit hash has not changed
            </label>
          </div>

          {/* GitHub Success Notification */}
          {githubSuccessMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-white mb-0.5">Refresh Complete</p>
                <p className="text-emerald-200/90">{githubSuccessMsg}</p>
              </div>
            </div>
          )}

          {/* GitHub Error Notification */}
          {githubErrorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-white mb-0.5">GitHub Integration Notice</p>
                <p className="text-rose-200/90">{githubErrorMsg}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Message Banner */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-3">
          <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold text-white mb-0.5">Change Detection / Synchronization Notice</h4>
            <p className="text-rose-200/90">{errorMsg}</p>
            <span className="text-[10px] text-rose-300/80 block mt-1">
              Documentation was not claimed synchronized due to incomplete analysis.
            </span>
          </div>
        </div>
      )}

      {/* Active Change Check Preview */}
      {checkResult && (
        <div
          className={`p-4 rounded-2xl border transition-all ${
            checkResult.has_changes
              ? 'bg-amber-500/5 border-amber-500/30'
              : 'bg-emerald-500/5 border-emerald-500/30'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              {checkResult.has_changes ? (
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              )}
              <span className="text-xs font-bold text-white">
                {checkResult.has_changes
                  ? `Repository Diff Detected (${checkResult.total_files_changed} files changed)`
                  : 'Repository is Up to Date'}
              </span>
            </div>
            {checkResult.has_changes && (
              <button
                onClick={() => setShowFilesList(!showFilesList)}
                className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1"
              >
                <span>{showFilesList ? 'Collapse files' : 'Expand files'}</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${showFilesList ? 'rotate-180' : ''}`} />
              </button>
            )}
          </div>

          <p className="text-xs text-slate-300 mb-3">{checkResult.summary}</p>

          {/* Files Changed Pills */}
          {checkResult.has_changes && showFilesList && (
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="flex flex-wrap gap-2 text-xs">
                {checkResult.files_added.map((f) => (
                  <span
                    key={f}
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-mono"
                  >
                    <FilePlus className="w-3 h-3" />
                    <span>+{f}</span>
                  </span>
                ))}
                {checkResult.files_modified.map((f) => (
                  <span
                    key={f}
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-mono"
                  >
                    <FileEdit className="w-3 h-3" />
                    <span>~{f}</span>
                  </span>
                ))}
                {checkResult.files_deleted.map((f) => (
                  <span
                    key={f}
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[11px] font-mono"
                  >
                    <FileX className="w-3 h-3" />
                    <span>-{f}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Impact Breakdown Cards */}
          {checkResult.has_changes && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-4 pt-3 border-t border-slate-800/80 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Entities Affected</span>
                <p className="text-base font-extrabold text-white mt-0.5">{checkResult.affected_entities.length}</p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">APIs Affected</span>
                <p className="text-base font-extrabold text-white mt-0.5">{checkResult.affected_apis.length}</p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">DB Models Affected</span>
                <p className="text-base font-extrabold text-white mt-0.5">{checkResult.affected_db_models.length}</p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Docs to Update</span>
                <p className="text-base font-extrabold text-brand-300 mt-0.5">{checkResult.affected_documents.length}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Latest Change Report Display */}
      {latestReport && (
        <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Latest Synchronization Report
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  latestReport.status === 'SYNCED'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : latestReport.status === 'NO_CHANGES'
                    ? 'bg-slate-800 text-slate-400'
                    : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                }`}
              >
                {latestReport.status}
              </span>
            </div>

            <div className="text-[11px] text-slate-400 font-mono">
              {latestReport.previous_commit_sha ? latestReport.previous_commit_sha.slice(0, 7) : 'init'} →{' '}
              {latestReport.current_commit_sha ? latestReport.current_commit_sha.slice(0, 7) : 'HEAD'}
            </div>
          </div>

          <p className="text-xs text-slate-300">{latestReport.message}</p>

          {/* Report Breakdown Grids */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {/* Documentation Updated List */}
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-brand-400" />
                  <span>Documentation Updated</span>
                </span>
                <span className="text-[11px] text-brand-400 font-bold">
                  {latestReport.documentation_updated.length}
                </span>
              </div>
              {latestReport.documentation_updated.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">No document updates were required.</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {latestReport.documentation_updated.map((doc) => (
                    <div
                      key={doc.document_id}
                      className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/60 flex items-center justify-between text-xs"
                    >
                      <div className="truncate mr-2">
                        <span className="font-semibold text-slate-200">{doc.title}</span>
                        <span className="text-[10px] text-slate-500 block truncate">{doc.document_type}</span>
                      </div>
                      <span className="shrink-0 px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30 text-[10px] font-mono">
                        v{doc.previous_version || 1} → v{doc.version}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Diagrams Updated List */}
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Workflow className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Diagrams Updated</span>
                </span>
                <span className="text-[11px] text-indigo-400 font-bold">
                  {latestReport.diagrams_updated.length}
                </span>
              </div>
              {latestReport.diagrams_updated.length === 0 ? (
                <p className="text-[11px] text-slate-500 italic">No architecture diagram changes needed.</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {latestReport.diagrams_updated.map((diag) => (
                    <div
                      key={diag.diagram_id}
                      className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/60 flex items-center justify-between text-xs"
                    >
                      <div className="truncate mr-2">
                        <span className="font-semibold text-slate-200">{diag.title}</span>
                        <span className="text-[10px] text-slate-500 block truncate">{diag.diagram_type}</span>
                      </div>
                      <span className="shrink-0 px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono">
                        v{diag.version}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Historical Audit Trail Modal / Section */}
      {showHistory && (
        <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-800">
            <span className="font-bold text-white flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-brand-400" />
              <span>Synchronization Audit History</span>
            </span>
            <span className="text-slate-400">{history.length} records</span>
          </div>

          {history.length === 0 ? (
            <p className="text-xs text-slate-500 py-3 text-center">No past synchronization records recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {history.map((rec) => (
                <div
                  key={rec.id}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        rec.status === 'SYNCED'
                          ? 'bg-emerald-400'
                          : rec.status === 'NO_CHANGES'
                          ? 'bg-slate-400'
                          : 'bg-rose-400'
                      }`}
                    />
                    <span className="font-semibold text-slate-200">{rec.message}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400">
                    <span className="font-mono">
                      {rec.total_files_changed} files · {rec.documentation_updated.length} docs
                    </span>
                    <span>
                      {rec.created_at ? new Date(rec.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
