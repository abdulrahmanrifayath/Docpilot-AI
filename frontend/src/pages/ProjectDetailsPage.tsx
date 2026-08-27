import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import {
  Project,
  ProjectStructureResponse,
  TechnologyDetectionResponse,
  ProjectStatisticsResponse,
  ProjectStatus,
} from '../types';
import { useProject } from '../context/ProjectContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { FileTreeExplorer } from '../components/projects/FileTreeExplorer';
import { TechStackCard } from '../components/projects/TechStackCard';
import { LanguageDistribution } from '../components/projects/LanguageDistribution';
import { CodeEntityInspector } from '../components/code/CodeEntityInspector';
import {
  BookOpen,
  GitBranch,
  Bot,
  ExternalLink,
  Calendar,
  ArrowLeft,
  Upload,
  RefreshCw,
  Trash2,
  AlertTriangle,
  FolderTree,
  Code2,
  Cpu,
  Clock,
  Server,
  Layers,
} from 'lucide-react';

const getStatusBadge = (status: ProjectStatus) => {
  switch (status) {
    case 'READY':
      return <Badge variant="success" dot>READY (UNSCANNED)</Badge>;
    case 'ANALYZED':
      return <Badge variant="success" dot>ANALYZED</Badge>;
    case 'UPLOADING':
      return <Badge variant="warning" dot>UPLOADING</Badge>;
    case 'CLONING':
      return <Badge variant="warning" dot>CLONING</Badge>;
    case 'ANALYZING':
      return <Badge variant="primary" dot>ANALYZING</Badge>;
    case 'FAILED':
      return <Badge variant="danger" dot>FAILED</Badge>;
    case 'CREATED':
    default:
      return <Badge variant="neutral" dot>CREATED</Badge>;
  }
};

export const ProjectDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setActiveProject, refreshProjects } = useProject();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [structure, setStructure] = useState<ProjectStructureResponse | null>(null);
  const [technologies, setTechnologies] = useState<TechnologyDetectionResponse | null>(null);
  const [statistics, setStatistics] = useState<ProjectStatisticsResponse | null>(null);

  const [activeTab, setActiveTab] = useState<'overview' | 'entities'>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAllData = async () => {
    if (!id) return;
    try {
      setIsLoading(true);
      setError(null);
      const projData = await projectsApi.getById(id);
      setProject(projData);
      setActiveProject(projData);

      if (projData.status === 'READY' || projData.status === 'ANALYZED') {
        try {
          const [structData, techData, statsData] = await Promise.all([
            projectsApi.getStructure(id),
            projectsApi.getTechnologies(id),
            projectsApi.getStatistics(id),
          ]);
          setStructure(structData);
          setTechnologies(techData);
          setStatistics(statsData);
        } catch (scanErr) {
          console.warn('Repository not scanned yet or error loading scan data:', scanErr);
        }
      } else {
        setStructure(null);
        setTechnologies(null);
        setStatistics(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load project details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, [id]);

  const handleRunScan = async () => {
    if (!project) return;
    try {
      setIsScanning(true);
      setError(null);
      const scanRes = await projectsApi.scan(project.id);
      setStatistics(scanRes.summary);
      setTechnologies(scanRes.technologies);
      const structRes = await projectsApi.getStructure(project.id);
      setStructure(structRes);
      await refreshProjects();
      const updated = await projectsApi.getById(project.id);
      setProject(updated);
    } catch (err: any) {
      setError(err.message || 'Repository scan failed.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleZipUpload = async (file: File) => {
    if (!project) return;
    try {
      setIsActionLoading(true);
      setError(null);
      await projectsApi.uploadZip(project.id, file, (progress) => {
        setUploadProgress(progress);
      });
      await fetchAllData();
      await refreshProjects();
    } catch (err: any) {
      setError(err.message || 'ZIP upload failed.');
    } finally {
      setIsActionLoading(false);
      setUploadProgress(null);
    }
  };

  const handleReClone = async () => {
    if (!project || !project.source_url) return;
    try {
      setIsActionLoading(true);
      setError(null);
      await projectsApi.cloneRepo(project.id, project.source_url);
      await fetchAllData();
      await refreshProjects();
    } catch (err: any) {
      setError(err.message || 'Cloning failed.');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    if (!window.confirm(`Delete ${project.name} and remove all repository data?`)) return;
    try {
      await projectsApi.delete(project.id);
      await refreshProjects();
      navigate('/projects');
    } catch (err: any) {
      setError(err.message || 'Failed to delete project.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error && !project) {
    return (
      <Card className="p-8 text-center border-dashed">
        <div className="text-rose-400 font-semibold text-sm mb-2">Project Not Found</div>
        <p className="text-xs text-slate-500 mb-4">{error || 'Could not find the requested repository.'}</p>
        <Link to="/projects">
          <Button variant="outline" size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />}>
            Back to Repositories
          </Button>
        </Link>
      </Card>
    );
  }

  if (!project) return null;

  return (
    <div className="space-y-6">
      {/* Back button & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/projects')}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-bold text-white tracking-tight">{project.name}</h1>
              {getStatusBadge(project.status)}
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span className="font-mono uppercase text-slate-300">{project.source_type}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3 text-slate-500" />
                Created {new Date(project.created_at).toLocaleDateString()}
              </span>
              {project.last_analyzed_at && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1 text-emerald-400">
                    <Clock className="w-3 h-3" />
                    Last Scan: {new Date(project.last_analyzed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action navigation & Scan trigger */}
        <div className="flex items-center gap-2">
          {(project.status === 'READY' || project.status === 'ANALYZED') && (
            <Button
              variant="primary"
              size="sm"
              isLoading={isScanning}
              onClick={handleRunScan}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : ''}`} />}
            >
              {project.status === 'ANALYZED' ? 'Re-Scan Repository' : 'Scan Repository'}
            </Button>
          )}

          <Link to="/documentation">
            <Button variant="secondary" size="sm" leftIcon={<BookOpen className="w-4 h-4 text-indigo-400" />}>
              Docs
            </Button>
          </Link>
          <Link to="/diagrams">
            <Button variant="secondary" size="sm" leftIcon={<GitBranch className="w-4 h-4 text-cyan-400" />}>
              Diagrams
            </Button>
          </Link>
          <Link to="/chat">
            <Button variant="outline" size="sm" leftIcon={<Bot className="w-4 h-4" />}>
              AI Chat
            </Button>
          </Link>
        </div>
      </div>

      {/* Error or Warning Banner if FAILED */}
      {project.status === 'FAILED' && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-rose-200">Repository Ingestion or Scan Failed</div>
              <div className="mt-0.5 text-[11px] text-rose-300/90">{project.status_message}</div>
            </div>
          </div>
          {project.source_type === 'github' && project.source_url && (
            <Button
              variant="outline"
              size="sm"
              isLoading={isActionLoading}
              onClick={handleReClone}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry Clone
            </Button>
          )}
        </div>
      )}

      {/* Ingestion In-Progress Banner */}
      {(project.status === 'UPLOADING' || project.status === 'CLONING' || project.status === 'ANALYZING') && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 flex items-center justify-between gap-3 animate-pulse">
          <div className="flex items-center gap-2.5">
            <RefreshCw className="w-4 h-4 text-amber-400 animate-spin" />
            <span>{project.status_message || 'Processing repository files...'}</span>
          </div>
          <Button variant="outline" size="sm" onClick={fetchAllData}>
            Check Status
          </Button>
        </div>
      )}

      {/* Upload prompt if status is CREATED */}
      {project.status === 'CREATED' && (
        <Card className="p-8 text-center border-dashed border-indigo-500/40 bg-indigo-950/10">
          <FolderTree className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-white">Repository Files Not Uploaded Yet</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            This project was created without files. Upload a .ZIP archive or clone from a public GitHub repository.
          </p>

          <input
            type="file"
            ref={fileInputRef}
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleZipUpload(e.target.files[0]);
              }
            }}
          />

          <div className="flex items-center justify-center gap-3 mt-5">
            <Button
              variant="primary"
              size="md"
              isLoading={isActionLoading}
              onClick={() => fileInputRef.current?.click()}
              leftIcon={<Upload className="w-4 h-4" />}
            >
              {uploadProgress !== null ? `Uploading ${uploadProgress}%` : 'Upload Project ZIP'}
            </Button>
          </div>
        </Card>
      )}

      {/* Top Metrics Row if Scanned */}
      {statistics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card className="flex items-center gap-3.5 p-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Code2 className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-mono">Lines of Code</div>
              <div className="text-xl font-bold text-white font-mono mt-0.5">
                {statistics.total_lines.toLocaleString()}
              </div>
            </div>
          </Card>

          <Card className="flex items-center gap-3.5 p-4">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <FolderTree className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-mono">Total Files</div>
              <div className="text-xl font-bold text-white font-mono mt-0.5">
                {statistics.total_files}
              </div>
            </div>
          </Card>

          <Card className="flex items-center gap-3.5 p-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-mono">Primary Language</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5 truncate max-w-[130px]">
                {technologies?.primary_language || 'Detected'}
              </div>
            </div>
          </Card>

          <Card className="flex items-center gap-3.5 p-4">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] text-slate-400 uppercase font-mono">Frameworks</div>
              <div className="text-sm font-bold text-white font-mono mt-0.5 truncate max-w-[130px]">
                {technologies && technologies.frameworks.length > 0
                  ? technologies.frameworks.map((f) => f.name).join(', ')
                  : 'Custom / Standard'}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Description & Remote URL Bar */}
      <Card className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Repository Overview
            </h3>
            <p className="text-sm text-slate-200 leading-relaxed">
              {project.description || 'No description provided for this repository.'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {project.source_type === 'github' && project.source_url && (
              <Button
                variant="outline"
                size="sm"
                isLoading={isActionLoading}
                onClick={handleReClone}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Re-clone
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
              leftIcon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Delete
            </Button>
          </div>
        </div>

        {project.source_url && (
          <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center gap-2 text-xs">
            <span className="text-slate-400">Remote GitHub Repository:</span>
            <a
              href={project.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
            >
              {project.source_url}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}
      </Card>

      {/* Tabs for Navigation */}
      {(project.status === 'READY' || project.status === 'ANALYZED') && (
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'overview'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Layers className="w-4 h-4" />
            Overview & Tech Stack
          </button>

          <button
            onClick={() => setActiveTab('entities')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'entities'
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Code2 className="w-4 h-4" />
            Code Entities (AST Parser)
          </button>
        </div>
      )}

      {/* Tab 1: Overview & Stack */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {technologies && statistics && (
            <>
              <LanguageDistribution
                languages={statistics.languages}
                categories={statistics.categories}
                totalLines={statistics.total_lines}
              />

              <TechStackCard
                frameworks={technologies.frameworks}
                infrastructure={technologies.infrastructure}
              />
            </>
          )}

          {structure && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                  <FolderTree className="w-4 h-4 text-indigo-400" />
                  Repository File Hierarchy & Code Density
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchAllData}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Refresh View
                </Button>
              </div>

              <FileTreeExplorer data={structure} />
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Code Entities */}
      {activeTab === 'entities' && (
        <CodeEntityInspector projectId={project.id} />
      )}
    </div>
  );
};
