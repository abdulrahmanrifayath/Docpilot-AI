import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  Archive,
  GitBranch,
  HardDrive,
  RefreshCw,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  FileSpreadsheet,
  File,
  ChevronRight,
  ChevronDown,
  Layers,
  Upload,
  Calendar,
  ExternalLink,
  Code2,
  Cpu,
  Server,
  Terminal,
  Activity,
  Scan,
  Check,
  Search,
} from 'lucide-react';
import {
  Project,
  ProjectStructureNode,
  ProjectStructureResponse,
  ProjectTechnologiesResponse,
  ProjectStatisticsResponse,
} from '../types';
import {
  fetchProject,
  fetchProjectStructure,
  fetchProjectTechnologies,
  fetchProjectStatistics,
  scanProject,
  uploadProjectZip,
  cloneProjectGit,
  deleteProject,
} from '../api/client';
import { useProjects } from '../context/ProjectContext';

// Recursive File Tree Node component
interface FileTreeNodeProps {
  node: ProjectStructureNode;
  level: number;
  selectedPath: string | null;
  onSelect: (node: ProjectStructureNode) => void;
  searchFilter: string;
}

const FileTreeNode: React.FC<FileTreeNodeProps> = ({
  node,
  level,
  selectedPath,
  onSelect,
  searchFilter,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(level === 0 || level === 1);
  const isDirectory = node.type === 'directory';
  const isSelected = selectedPath === node.path;

  // Filter matching
  const hasMatchingChildren = (n: ProjectStructureNode): boolean => {
    if (!searchFilter) return true;
    if (n.name.toLowerCase().includes(searchFilter.toLowerCase())) return true;
    if (n.children) {
      return n.children.some(hasMatchingChildren);
    }
    return false;
  };

  if (searchFilter && !hasMatchingChildren(node)) {
    return null;
  }

  const getFileIcon = (name: string, ext?: string) => {
    const extension = (ext || name.split('.').pop() || '').toLowerCase();
    if (extension === '.md' || extension === 'md' || extension === 'txt')
      return <FileText className="w-3.5 h-3.5 text-slate-400" />;
    if (['.json', '.yaml', '.yml', '.toml', 'json', 'yaml', 'yml'].includes(extension))
      return <FileSpreadsheet className="w-3.5 h-3.5 text-amber-400" />;
    if (['.ts', '.tsx', '.js', '.jsx', '.py', '.sql', '.html', '.css', 'ts', 'tsx', 'js', 'jsx', 'py'].includes(extension))
      return <FileCode className="w-3.5 h-3.5 text-brand-400" />;
    return <File className="w-3.5 h-3.5 text-slate-500" />;
  };

  const formatBytes = (bytes?: number) => {
    if (bytes === undefined || bytes === null) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getCategoryColor = (cat?: string) => {
    switch (cat) {
      case 'code':
        return 'text-brand-400 bg-brand-500/10 border-brand-500/20';
      case 'infrastructure':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'config':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'documentation':
        return 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
      case 'asset':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div>
      <div
        onClick={() => {
          if (isDirectory) {
            setIsOpen(!isOpen);
          }
          onSelect(node);
        }}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        className={`flex items-center justify-between py-1.5 pr-3 rounded-lg text-xs cursor-pointer select-none transition-colors ${
          isSelected
            ? 'bg-brand-600/25 text-white font-medium shadow-sm'
            : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
        }`}
      >
        <div className="flex items-center gap-2 truncate">
          {isDirectory ? (
            <>
              {isOpen ? (
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              )}
              {isOpen ? (
                <FolderOpen className="w-4 h-4 text-amber-400 shrink-0" />
              ) : (
                <Folder className="w-4 h-4 text-amber-400 shrink-0" />
              )}
            </>
          ) : (
            <>
              <span className="w-3.5 shrink-0" />
              {getFileIcon(node.name, node.extension)}
            </>
          )}
          <span className="truncate">{node.name}</span>
        </div>

        {!isDirectory && (
          <div className="flex items-center gap-2 shrink-0 pl-2">
            {node.language && (
              <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-slate-800 text-slate-300 border border-slate-700 hidden sm:inline">
                {node.language}
              </span>
            )}
            {node.file_category && (
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-semibold uppercase tracking-wider border hidden md:inline ${getCategoryColor(
                  node.file_category
                )}`}
              >
                {node.file_category}
              </span>
            )}
            {node.estimated_line_count !== undefined && node.estimated_line_count > 0 && (
              <span className="text-[10px] text-slate-400 font-mono hidden lg:inline">
                {node.estimated_line_count}L
              </span>
            )}
            {node.file_size !== undefined && (
              <span className="text-[10px] text-slate-500 font-mono">
                {formatBytes(node.file_size)}
              </span>
            )}
          </div>
        )}
      </div>

      {isDirectory && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              searchFilter={searchFilter}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const ProjectDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setActiveProject, refreshProjects } = useProjects();

  const [project, setProject] = useState<Project | null>(null);
  const [structureData, setStructureData] = useState<ProjectStructureResponse | null>(null);
  const [techData, setTechData] = useState<ProjectTechnologiesResponse | null>(null);
  const [statsData, setStatsData] = useState<ProjectStatisticsResponse | null>(null);
  const [selectedFileNode, setSelectedFileNode] = useState<ProjectStructureNode | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);
  const [scanSuccess, setScanSuccess] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  // Quick Action States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  useEffect(() => {
    if (id) {
      loadAllData(id);
    }
  }, [id]);

  const loadAllData = async (projId: string) => {
    try {
      setLoading(true);
      const [proj, struct, tech, stats] = await Promise.all([
        fetchProject(projId),
        fetchProjectStructure(projId).catch(() => null),
        fetchProjectTechnologies(projId).catch(() => null),
        fetchProjectStatistics(projId).catch(() => null),
      ]);

      setProject(proj);
      setActiveProject(proj);
      setStructureData(struct);
      setTechData(tech);
      setStatsData(stats);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    if (!project) return;
    setScanning(true);
    setScanSuccess(false);
    try {
      await scanProject(project.id);
      setScanSuccess(true);
      await loadAllData(project.id);
      await refreshProjects();
      setTimeout(() => setScanSuccess(false), 3000);
    } catch (err: any) {
      alert(`Scan failed: ${err.message || err}`);
    } finally {
      setScanning(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    if (!window.confirm(`Delete project "${project.name}" and remove all isolated files?`)) return;
    try {
      await deleteProject(project.id);
      await refreshProjects();
      navigate('/projects');
    } catch (err: any) {
      alert(`Delete failed: ${err.message || err}`);
    }
  };

  const handleUploadZip = async () => {
    if (!project || !uploadFile) return;
    setIsUploading(true);
    try {
      await uploadProjectZip(project.id, uploadFile);
      setUploadFile(null);
      await loadAllData(project.id);
      await refreshProjects();
    } catch (err: any) {
      alert(`Upload failed: ${err.message || err}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleCloneGit = async () => {
    if (!project) return;
    setIsUploading(true);
    try {
      await cloneProjectGit(project.id, project.source_url);
      await loadAllData(project.id);
      await refreshProjects();
    } catch (err: any) {
      alert(`Git Clone failed: ${err.message || err}`);
    } finally {
      setIsUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500 mb-3" />
        <span className="text-xs">Analyzing and loading repository intelligence...</span>
      </div>
    );
  }

  if (errorMsg || !project) {
    return (
      <div className="p-8 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm max-w-lg mx-auto text-center">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
        <h3 className="font-bold text-white mb-1">Project Not Found</h3>
        <p className="text-xs text-rose-200/80 mb-4">{errorMsg || 'Unable to retrieve project.'}</p>
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Projects</span>
        </Link>
      </div>
    );
  }

  const isReady = project.status === 'READY' || project.status === 'ANALYZED';
  const isPending = project.status === 'UPLOADING' || project.status === 'CLONING' || project.status === 'ANALYZING';
  const isFailed = project.status === 'FAILED';

  const totalFiles = statsData?.total_files ?? structureData?.total_files ?? 0;
  const totalDirs = statsData?.total_directories ?? structureData?.total_directories ?? 0;
  const totalLines = statsData?.total_lines ?? 0;
  const languages = techData?.languages || statsData?.languages || project.languages || {};
  const frameworks = techData?.frameworks || statsData?.frameworks || project.frameworks || [];
  const infrastructure = techData?.infrastructure || statsData?.infrastructure || project.infrastructure || [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/projects"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Back to Projects"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">{project.name}</h1>
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
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
                <span>{project.status}</span>
              </span>
            </div>
            {project.description && (
              <p className="text-xs text-slate-400 mt-0.5">{project.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Scan Button */}
          <button
            onClick={handleScan}
            disabled={scanning || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              scanSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-brand-600 hover:bg-brand-500 text-white shadow-brand-600/25'
            } disabled:opacity-50`}
            title="Scan repository files, languages, and frameworks"
          >
            {scanning ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : scanSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Scan className="w-3.5 h-3.5" />
            )}
            <span>{scanning ? 'Scanning...' : scanSuccess ? 'Scan Complete' : 'Scan Repository'}</span>
          </button>

          <button
            onClick={() => id && loadAllData(id)}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Refresh Data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleDelete}
            className="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-all"
            title="Delete Project"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Error Alert if Failed */}
      {isFailed && project.error_message && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
          <div>
            <h4 className="font-bold text-white mb-0.5">Project Ingestion Error</h4>
            <p className="text-rose-200/90">{project.error_message}</p>
          </div>
        </div>
      )}

      {/* SECTION 1: PROJECT OVERVIEW METRICS */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-brand-400" />
          <span>Project Overview & Discovery Metrics</span>
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Files</span>
            <p className="text-2xl font-extrabold text-white mt-1">{totalFiles.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">Sanitized source assets</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Directories</span>
            <p className="text-2xl font-extrabold text-white mt-1">{totalDirs.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">Folder hierarchy nodes</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-400">
              Estimated Lines of Code
            </span>
            <p className="text-2xl font-extrabold text-brand-300 mt-1">{totalLines.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">Non-binary text lines</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Last Analysis</span>
            <p className="text-xs font-semibold text-white mt-2 truncate">
              {project.last_analyzed_at
                ? new Date(project.last_analyzed_at).toLocaleString()
                : 'Scanned upon ingestion'}
            </p>
            <span className="text-[10px] text-slate-500 block mt-1">Static AST discovery</span>
          </div>
        </div>
      </div>

      {/* SECTION 2: TECHNOLOGY INTELLIGENCE (Languages, Frameworks, Infrastructure) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Languages Card */}
        <div className="lg:col-span-1 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-brand-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">Detected Languages</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">{Object.keys(languages).length} found</span>
          </div>

          {Object.keys(languages).length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No supported languages identified yet.</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(languages).map(([lang, stat]) => {
                const percent = totalLines > 0 ? Math.round((stat.lines / totalLines) * 100) : 0;
                return (
                  <div key={lang} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-white">{lang}</span>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {stat.files} files • {stat.lines.toLocaleString()} lines ({percent}%)
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-brand-500 to-indigo-500 rounded-full"
                        style={{ width: `${Math.min(100, Math.max(4, percent))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Frameworks Card */}
        <div className="lg:col-span-1 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">Detected Frameworks</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">{frameworks.length} detected</span>
          </div>

          {frameworks.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No major frameworks detected in project.</p>
          ) : (
            <div className="flex flex-wrap gap-2 pt-1">
              {frameworks.map((fw) => (
                <span
                  key={fw}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold"
                >
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  <span>{fw}</span>
                </span>
              ))}
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500">
            Detected via heuristic imports, pyproject.toml, requirements.txt, and package.json descriptors.
          </div>
        </div>

        {/* Infrastructure Card */}
        <div className="lg:col-span-1 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-white">Infrastructure & DevOps</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">{infrastructure.length} detected</span>
          </div>

          {infrastructure.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No container or cloud configurations found.</p>
          ) : (
            <div className="flex flex-wrap gap-2 pt-1">
              {infrastructure.map((inf) => (
                <span
                  key={inf}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold"
                >
                  <Server className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{inf}</span>
                </span>
              ))}
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500">
            Identifies Dockerfiles, Compose specs, GitHub Workflows, Kubernetes manifests, and Terraform files.
          </div>
        </div>
      </div>

      {/* If Project is in CREATED status without files, offer ingestion action */}
      {project.status === 'CREATED' && (
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-brand-500/30 text-center">
          <h3 className="text-base font-bold text-white mb-2">Ingestion Required</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
            This project has been registered but code has not been uploaded or cloned yet.
          </p>

          {project.source_type === 'zip' ? (
            <div className="max-w-xs mx-auto flex flex-col items-center gap-3">
              <input
                type="file"
                accept=".zip,application/zip"
                id="details-zip-upload"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setUploadFile(e.target.files[0]);
                  }
                }}
                className="hidden"
              />
              <label
                htmlFor="details-zip-upload"
                className="cursor-pointer px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700"
              >
                {uploadFile ? uploadFile.name : 'Choose ZIP Archive'}
              </label>
              {uploadFile && (
                <button
                  disabled={isUploading}
                  onClick={handleUploadZip}
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 disabled:opacity-50"
                >
                  {isUploading ? 'Extracting...' : 'Upload & Extract Now'}
                </button>
              )}
            </div>
          ) : (
            <div className="max-w-xs mx-auto">
              <button
                disabled={isUploading}
                onClick={handleCloneGit}
                className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/25 disabled:opacity-50"
              >
                {isUploading ? 'Cloning...' : 'Start Git Clone Now'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* SECTION 3: EXPANDABLE REPOSITORY TREE */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6 space-y-4">
        {/* Tree Explorer Header & Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Folder className="w-5 h-5 text-brand-400" />
            <h2 className="text-sm font-bold text-white tracking-tight">Expandable Repository Tree</h2>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {totalFiles} files
            </span>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search repository files..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>
        </div>

        {/* Tree Content Area */}
        {!structureData || !structureData.tree || (structureData.tree.children && structureData.tree.children.length === 0) ? (
          <div className="py-12 text-center text-slate-500">
            <Folder className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-400">No repository files scanned</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Click &quot;Scan Repository&quot; to inspect files, extensions, lines, and categories.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tree Navigation Column */}
            <div className="lg:col-span-2 max-h-[520px] overflow-y-auto pr-2 border-r border-slate-800/80">
              <div className="space-y-0.5">
                {structureData.tree.children &&
                  structureData.tree.children.map((child) => (
                    <FileTreeNode
                      key={child.path}
                      node={child}
                      level={0}
                      selectedPath={selectedFileNode?.path || null}
                      onSelect={(n) => setSelectedFileNode(n)}
                      searchFilter={searchFilter}
                    />
                  ))}
              </div>
            </div>

            {/* Selected Node Details Column */}
            <div className="lg:col-span-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                File & Component Inspector
              </h3>
              {selectedFileNode ? (
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3.5">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                      Name
                    </span>
                    <p className="text-xs font-bold text-white break-all mt-0.5">
                      {selectedFileNode.name}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                      Relative Path
                    </span>
                    <p className="text-xs font-mono text-slate-300 break-all mt-0.5 bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                      {selectedFileNode.path}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
                        Category
                      </span>
                      <span className="font-semibold text-white capitalize mt-0.5 inline-block">
                        {selectedFileNode.file_category || selectedFileNode.type}
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
                        Language
                      </span>
                      <span className="font-semibold text-brand-300 mt-0.5 inline-block">
                        {selectedFileNode.language || 'Plain Text / Other'}
                      </span>
                    </div>
                  </div>

                  {selectedFileNode.estimated_line_count !== undefined && (
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                        Lines of Code
                      </span>
                      <p className="text-xs font-mono font-semibold text-white mt-0.5">
                        {selectedFileNode.estimated_line_count.toLocaleString()} lines
                      </p>
                    </div>
                  )}

                  {selectedFileNode.file_size !== undefined && (
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                        File Size
                      </span>
                      <p className="text-xs font-semibold text-white mt-0.5">
                        {selectedFileNode.file_size.toLocaleString()} bytes
                      </p>
                    </div>
                  )}

                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                    <p>
                      Files are parsed statically. Phase 4 will generate interactive Mermaid architecture diagrams and dependency graphs.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center text-slate-500">
                  <p className="text-xs">Select any file in the tree to inspect its path, language, category, and lines of code.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
