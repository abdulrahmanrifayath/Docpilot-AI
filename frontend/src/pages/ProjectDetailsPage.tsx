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
} from 'lucide-react';
import { Project, ProjectFileNode, ProjectFilesResponse } from '../types';
import { fetchProject, fetchProjectFiles, uploadProjectZip, cloneProjectGit, deleteProject } from '../api/client';
import { useProjects } from '../context/ProjectContext';

// Recursive File Tree Node component
interface FileTreeNodeProps {
  node: ProjectFileNode;
  level: number;
  selectedPath: string | null;
  onSelect: (node: ProjectFileNode) => void;
}

const FileTreeNode: React.FC<FileTreeNodeProps> = ({ node, level, selectedPath, onSelect }) => {
  const [isOpen, setIsOpen] = useState<boolean>(level === 0 || level === 1);
  const isDirectory = node.type === 'directory';
  const isSelected = selectedPath === node.path;

  const getFileIcon = (name: string) => {
    const ext = name.split('.').pop()?.toLowerCase();
    if (ext === 'md' || ext === 'txt') return <FileText className="w-3.5 h-3.5 text-slate-400" />;
    if (ext === 'json' || ext === 'yaml' || ext === 'yml' || ext === 'toml')
      return <FileSpreadsheet className="w-3.5 h-3.5 text-amber-400" />;
    if (['ts', 'tsx', 'js', 'jsx', 'py', 'go', 'rs', 'java', 'c', 'cpp'].includes(ext || ''))
      return <FileCode className="w-3.5 h-3.5 text-brand-400" />;
    return <File className="w-3.5 h-3.5 text-slate-500" />;
  };

  const formatBytes = (bytes?: number) => {
    if (bytes === undefined || bytes === null) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
            ? 'bg-brand-600/20 text-white font-medium'
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
              {getFileIcon(node.name)}
            </>
          )}
          <span className="truncate">{node.name}</span>
        </div>

        {!isDirectory && node.size !== undefined && (
          <span className="text-[10px] text-slate-500 font-mono shrink-0 pl-2">
            {formatBytes(node.size)}
          </span>
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
  const [filesData, setFilesData] = useState<ProjectFilesResponse | null>(null);
  const [selectedFileNode, setSelectedFileNode] = useState<ProjectFileNode | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingFiles, setLoadingFiles] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Quick Action States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  useEffect(() => {
    if (id) {
      loadProject(id);
      loadFiles(id);
    }
  }, [id]);

  const loadProject = async (projId: string) => {
    try {
      setLoading(true);
      const proj = await fetchProject(projId);
      setProject(proj);
      setActiveProject(proj);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load project');
    } finally {
      setLoading(false);
    }
  };

  const loadFiles = async (projId: string) => {
    try {
      setLoadingFiles(true);
      const files = await fetchProjectFiles(projId);
      setFilesData(files);
    } catch (err: any) {
      console.warn('Could not load files:', err.message);
    } finally {
      setLoadingFiles(false);
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
      const updated = await uploadProjectZip(project.id, uploadFile);
      setProject(updated);
      setUploadFile(null);
      await loadFiles(project.id);
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
      const updated = await cloneProjectGit(project.id, project.source_url);
      setProject(updated);
      await loadFiles(project.id);
      await refreshProjects();
    } catch (err: any) {
      alert(`Git Clone failed: ${err.message || err}`);
    } finally {
      setIsUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500 mb-3" />
        <span className="text-xs">Loading project details...</span>
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
  const isPending = project.status === 'UPLOADING' || project.status === 'CLONING';
  const isFailed = project.status === 'FAILED';

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
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

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (id) {
                loadProject(id);
                loadFiles(id);
              }
            }}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold border border-rose-500/30 transition-all"
            title="Delete Project"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete</span>
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

      {/* Metadata Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Source Type */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Source Type</span>
          <div className="flex items-center gap-2 mt-2">
            {project.source_type === 'zip' ? (
              <Archive className="w-4 h-4 text-brand-400" />
            ) : project.source_type === 'git' ? (
              <GitBranch className="w-4 h-4 text-indigo-400" />
            ) : (
              <HardDrive className="w-4 h-4 text-cyan-400" />
            )}
            <span className="text-sm font-bold text-white uppercase">{project.source_type}</span>
          </div>
          {project.source_url && (
            <a
              href={project.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-brand-400 hover:text-brand-300 truncate block mt-1"
            >
              {project.source_url}
            </a>
          )}
        </div>

        {/* Isolated Storage Path */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Sandbox Path</span>
          <p className="text-xs font-mono text-slate-300 truncate mt-2" title={project.repository_path}>
            {project.repository_path || 'Not allocated yet'}
          </p>
          <span className="text-[10px] text-slate-500 block mt-1">Safe isolated sandbox directory</span>
        </div>

        {/* Created Timestamp */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Created At</span>
          <p className="text-xs font-semibold text-white mt-2">
            {new Date(project.created_at).toLocaleString()}
          </p>
          <span className="text-[10px] text-slate-500 block mt-1">Initial registration</span>
        </div>

        {/* Total Extracted Files */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Extracted Files</span>
          <p className="text-xl font-bold text-white mt-1">
            {filesData ? filesData.total_files : '...'}
          </p>
          <span className="text-[10px] text-slate-500 block mt-1">Sanitized source files</span>
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

      {/* Project File Tree Explorer Section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm p-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <Folder className="w-5 h-5 text-brand-400" />
            <h2 className="text-sm font-bold text-white tracking-tight">Repository File Explorer</h2>
            {filesData && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {filesData.total_files} files
              </span>
            )}
          </div>
          <button
            onClick={() => id && loadFiles(id)}
            disabled={loadingFiles}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingFiles ? 'animate-spin text-brand-400' : ''}`} />
            <span>Refresh Tree</span>
          </button>
        </div>

        {loadingFiles ? (
          <div className="py-16 text-center text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-brand-500 mx-auto mb-2" />
            <p className="text-xs">Reading isolated project directory...</p>
          </div>
        ) : !filesData || filesData.files.length === 0 ? (
          <div className="py-12 text-center text-slate-500">
            <Folder className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-400">No extracted files found</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Ensure the project has finished uploading or cloning successfully.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tree Navigation Column */}
            <div className="lg:col-span-2 max-h-[500px] overflow-y-auto pr-2 border-r border-slate-800/80">
              <div className="space-y-0.5">
                {filesData.files.map((child) => (
                  <FileTreeNode
                    key={child.path}
                    node={child}
                    level={0}
                    selectedPath={selectedFileNode?.path || null}
                    onSelect={(n) => setSelectedFileNode(n)}
                  />
                ))}
              </div>
            </div>

            {/* Selected Node Details Column */}
            <div className="lg:col-span-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                File Details
              </h3>
              {selectedFileNode ? (
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
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

                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                      Type
                    </span>
                    <p className="text-xs font-semibold text-slate-300 capitalize mt-0.5">
                      {selectedFileNode.type}
                    </p>
                  </div>

                  {selectedFileNode.size !== undefined && (
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                        Size
                      </span>
                      <p className="text-xs font-semibold text-white mt-0.5">
                        {selectedFileNode.size.toLocaleString()} bytes
                      </p>
                    </div>
                  )}

                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                    <p>
                      Files are stored in sandbox isolation. Source code parsing and documentation generation are enabled in Phase 3.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center text-slate-500">
                  <p className="text-xs">Select any file from the explorer tree to view its path and size.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
