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
  Boxes,
  Braces,
  Hash,
  Sparkles,
  Workflow,
  Network,
  Database,
} from 'lucide-react';
import {
  Project,
  ProjectStructureNode,
  ProjectStructureResponse,
  ProjectTechnologiesResponse,
  ProjectStatisticsResponse,
  CodeEntity,
  CodeEntityType,
  ProjectParseResponse,
  DependencyGraphResponse,
  APIEndpoint,
} from '../types';
import {
  fetchProject,
  fetchProjectStructure,
  fetchProjectTechnologies,
  fetchProjectStatistics,
  scanProject,
  parseProjectCode,
  fetchFileEntities,
  fetchProjectEntities,
  fetchDependencyGraph,
  analyzeDependencies,
  fetchProjectApis,
  analyzeProjectApis,
  fetchDatabaseModels,
  analyzeProjectDatabase,
  buildKnowledgeGraph,
  fetchKnowledgeGraph,
  uploadProjectZip,
  cloneProjectGit,
  deleteProject,
} from '../api/client';
import { DependencyGraphViewer } from '../components/DependencyGraphViewer';
import { APIExplorer } from '../components/APIExplorer';
import { DatabaseSchemaExplorer } from '../components/DatabaseSchemaExplorer';
import { ArchitectureExplorer } from '../components/ArchitectureExplorer';
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
  const [parsing, setParsing] = useState<boolean>(false);
  const [parseSuccess, setParseSuccess] = useState<boolean>(false);
  const [parseSummary, setParseSummary] = useState<ProjectParseResponse | null>(null);
  const [depGraphData, setDepGraphData] = useState<DependencyGraphResponse | null>(null);
  const [analyzingDeps, setAnalyzingDeps] = useState<boolean>(false);
  const [analyzeDepsSuccess, setAnalyzeDepsSuccess] = useState<boolean>(false);
  const [apis, setApis] = useState<APIEndpoint[]>([]);
  const [analyzingApis, setAnalyzingApis] = useState<boolean>(false);
  const [analyzeApisSuccess, setAnalyzeApisSuccess] = useState<boolean>(false);
  const [dbModelsCount, setDbModelsCount] = useState<number>(0);
  const [analyzingDb, setAnalyzingDb] = useState<boolean>(false);
  const [analyzeDbSuccess, setAnalyzeDbSuccess] = useState<boolean>(false);
  const [knowledgeStats, setKnowledgeStats] = useState<{ nodes: number; edges: number } | null>(null);
  const [buildingKnowledge, setBuildingKnowledge] = useState<boolean>(false);
  const [buildKnowledgeSuccess, setBuildKnowledgeSuccess] = useState<boolean>(false);
  const [fileEntities, setFileEntities] = useState<CodeEntity[]>([]);
  const [loadingEntities, setLoadingEntities] = useState<boolean>(false);
  const [entityFilter, setEntityFilter] = useState<string>('ALL');
  const [totalEntitiesCount, setTotalEntitiesCount] = useState<number>(0);
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
      const [proj, struct, tech, stats, allEntities, graph, discoveredApis, dbModels, kGraph] = await Promise.all([
        fetchProject(projId),
        fetchProjectStructure(projId).catch(() => null),
        fetchProjectTechnologies(projId).catch(() => null),
        fetchProjectStatistics(projId).catch(() => null),
        fetchProjectEntities(projId).catch(() => []),
        fetchDependencyGraph(projId).catch(() => null),
        fetchProjectApis(projId).catch(() => []),
        fetchDatabaseModels(projId).catch(() => []),
        fetchKnowledgeGraph(projId, { limit: 1 }).catch(() => null),
      ]);

      setProject(proj);
      setActiveProject(proj);
      setStructureData(struct);
      setTechData(tech);
      setStatsData(stats);
      setTotalEntitiesCount(allEntities.length);
      setDepGraphData(graph);
      setApis(discoveredApis || []);
      setDbModelsCount(dbModels?.length || 0);
      if (kGraph?.stats) {
        setKnowledgeStats({
          nodes: kGraph.stats.total_nodes,
          edges: kGraph.stats.total_edges,
        });
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectNode = async (node: ProjectStructureNode) => {
    setSelectedFileNode(node);
    if (node.type === 'file' && project) {
      setLoadingEntities(true);
      try {
        const ents = await fetchFileEntities(project.id, node.path);
        setFileEntities(ents);
      } catch (err) {
        console.warn('Failed to load file entities:', err);
        setFileEntities([]);
      } finally {
        setLoadingEntities(false);
      }
    } else {
      setFileEntities([]);
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

  const handleParseCode = async () => {
    if (!project) return;
    setParsing(true);
    setParseSuccess(false);
    try {
      const res = await parseProjectCode(project.id);
      setParseSummary(res);
      setParseSuccess(true);
      setTotalEntitiesCount(res.total_entities_extracted);
      await loadAllData(project.id);
      await refreshProjects();
      if (selectedFileNode && selectedFileNode.type === 'file') {
        const ents = await fetchFileEntities(project.id, selectedFileNode.path);
        setFileEntities(ents);
      }
      setTimeout(() => setParseSuccess(false), 4000);
    } catch (err: any) {
      alert(`Code parsing failed: ${err.message || err}`);
    } finally {
      setParsing(false);
    }
  };

  const handleAnalyzeDependencies = async () => {
    if (!project) return;
    setAnalyzingDeps(true);
    setAnalyzeDepsSuccess(false);
    try {
      await analyzeDependencies(project.id);
      const graph = await fetchDependencyGraph(project.id);
      setDepGraphData(graph);
      setAnalyzeDepsSuccess(true);
      await loadAllData(project.id);
      await refreshProjects();
      setTimeout(() => setAnalyzeDepsSuccess(false), 4000);
    } catch (err: any) {
      alert(`Dependency analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzingDeps(false);
    }
  };

  const handleAnalyzeApis = async () => {
    if (!project) return;
    setAnalyzingApis(true);
    setAnalyzeApisSuccess(false);
    try {
      const res = await analyzeProjectApis(project.id);
      setApis(res.endpoints || []);
      setAnalyzeApisSuccess(true);
      await loadAllData(project.id);
      await refreshProjects();
      setTimeout(() => setAnalyzeApisSuccess(false), 4000);
    } catch (err: any) {
      alert(`API Analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzingApis(false);
    }
  };

  const handleAnalyzeDatabase = async () => {
    if (!project) return;
    setAnalyzingDb(true);
    setAnalyzeDbSuccess(false);
    try {
      const res = await analyzeProjectDatabase(project.id);
      setDbModelsCount(res.total_models || 0);
      setAnalyzeDbSuccess(true);
      await loadAllData(project.id);
      await refreshProjects();
      setTimeout(() => setAnalyzeDbSuccess(false), 4000);
    } catch (err: any) {
      alert(`Database Analysis failed: ${err.message || err}`);
    } finally {
      setAnalyzingDb(false);
    }
  };

  const handleBuildKnowledge = async () => {
    if (!project) return;
    setBuildingKnowledge(true);
    setBuildKnowledgeSuccess(false);
    try {
      const res = await buildKnowledgeGraph(project.id);
      setKnowledgeStats({ nodes: res.total_nodes, edges: res.total_edges });
      setBuildKnowledgeSuccess(true);
      await loadAllData(project.id);
      await refreshProjects();
      setTimeout(() => setBuildKnowledgeSuccess(false), 4000);
    } catch (err: any) {
      alert(`Knowledge Graph build failed: ${err.message || err}`);
    } finally {
      setBuildingKnowledge(false);
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

          {/* Parse Code Button */}
          <button
            onClick={handleParseCode}
            disabled={parsing || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              parseSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/25'
            } disabled:opacity-50`}
            title="Parse Python AST and JS/TS Tree-sitter entities without AI"
          >
            {parsing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : parseSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Code2 className="w-3.5 h-3.5" />
            )}
            <span>{parsing ? 'Parsing AST...' : parseSuccess ? 'Code Parsed' : 'Parse Code'}</span>
          </button>

          {/* Analyze Dependencies Button */}
          <button
            onClick={handleAnalyzeDependencies}
            disabled={analyzingDeps || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              analyzeDepsSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-teal-600 hover:bg-teal-500 text-white shadow-teal-600/25'
            } disabled:opacity-50`}
            title="Detect file imports, module calls, inheritance, and dependency topology"
          >
            {analyzingDeps ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : analyzeDepsSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Workflow className="w-3.5 h-3.5" />
            )}
            <span>{analyzingDeps ? 'Analyzing Graph...' : analyzeDepsSuccess ? 'Graph Analyzed' : 'Analyze Dependencies'}</span>
          </button>

          {/* Discover APIs Button */}
          <button
            onClick={handleAnalyzeApis}
            disabled={analyzingApis || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              analyzeApisSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-violet-600 hover:bg-violet-500 text-white shadow-violet-600/25'
            } disabled:opacity-50`}
            title="Automatically detect backend API routes (FastAPI, Flask, Express)"
          >
            {analyzingApis ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : analyzeApisSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Server className="w-3.5 h-3.5" />
            )}
            <span>{analyzingApis ? 'Scanning Routes...' : analyzeApisSuccess ? 'APIs Discovered' : 'Discover APIs'}</span>
          </button>

          {/* Analyze Database Button */}
          <button
            onClick={handleAnalyzeDatabase}
            disabled={analyzingDb || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              analyzeDbSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/25'
            } disabled:opacity-50`}
            title="Automatically inspect database models, relationships, and generate Mermaid ER diagrams"
          >
            {analyzingDb ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : analyzeDbSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Database className="w-3.5 h-3.5" />
            )}
            <span>{analyzingDb ? 'Analyzing DB...' : analyzeDbSuccess ? 'Database Analyzed' : 'Analyze Database'}</span>
          </button>

          {/* Build Knowledge Graph Button */}
          <button
            onClick={handleBuildKnowledge}
            disabled={buildingKnowledge || isPending}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all ${
              buildKnowledgeSuccess
                ? 'bg-emerald-600 text-white'
                : 'bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white shadow-brand-600/25'
            } disabled:opacity-50`}
            title="Combine scanner, AST entities, dependencies, APIs, and database models into a unified project knowledge graph"
          >
            {buildingKnowledge ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : buildKnowledgeSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>{buildingKnowledge ? 'Building Graph...' : buildKnowledgeSuccess ? 'Knowledge Graph Built' : 'Build Knowledge Graph'}</span>
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

      {/* Parse Summary Banner if freshly parsed */}
      {parseSummary && (
        <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-200 text-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0" />
            <div>
              <span className="font-bold text-white">Static Code Parsing Engine Complete:</span>{' '}
              Parsed {parseSummary.total_files_parsed} files, extracted {parseSummary.total_entities_extracted} entities.
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {Object.entries(parseSummary.entity_breakdown).map(([type, count]) => (
              <span key={type} className="px-2 py-0.5 rounded-lg bg-indigo-950/80 border border-indigo-500/30 text-[11px] font-mono text-indigo-300">
                {type}: <strong className="text-white">{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

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
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-4">
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
            <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
              Parsed Code Entities
            </span>
            <p className="text-2xl font-extrabold text-indigo-300 mt-1">{totalEntitiesCount.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">AST classes, methods, functions</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
              Dependency Graph
            </span>
            <p className="text-2xl font-extrabold text-emerald-300 mt-1">
              {(depGraphData?.edges?.length || 0).toLocaleString()}
            </p>
            <span className="text-[10px] text-slate-500 block mt-1">
              {depGraphData?.nodes?.length || 0} nodes · Edges detected
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-400">
              Discovered APIs
            </span>
            <p className="text-2xl font-extrabold text-violet-300 mt-1">{apis.length.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">
              {apis.filter(a => a.authentication_required).length} auth · {apis.filter(a => !a.authentication_required).length} public
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
              Database Models
            </span>
            <p className="text-2xl font-extrabold text-amber-300 mt-1">{dbModelsCount.toLocaleString()}</p>
            <span className="text-[10px] text-slate-500 block mt-1">
              SQLAlchemy & Django models
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-gradient-to-br from-brand-950/40 to-slate-900/60 border border-brand-500/30">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-300">
              Knowledge Graph
            </span>
            <p className="text-2xl font-extrabold text-white mt-1">
              {(knowledgeStats?.nodes || 0).toLocaleString()}
            </p>
            <span className="text-[10px] text-brand-300/80 block mt-1">
              {knowledgeStats?.edges || 0} cross-tier edges
            </span>
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
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Tree Navigation Column */}
            <div className="lg:col-span-5 max-h-[640px] overflow-y-auto pr-2 border-r border-slate-800/80">
              <div className="space-y-0.5">
                {structureData.tree.children &&
                  structureData.tree.children.map((child) => (
                    <FileTreeNode
                      key={child.path}
                      node={child}
                      level={0}
                      selectedPath={selectedFileNode?.path || null}
                      onSelect={(n) => handleSelectNode(n)}
                      searchFilter={searchFilter}
                    />
                  ))}
              </div>
            </div>

            {/* Selected Node Details & Code Entity Inspector Column */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-brand-400" />
                  <span>File & AST Code Inspector</span>
                </h3>
                {selectedFileNode && (
                  <span className="text-[11px] font-mono text-slate-400">
                    {fileEntities.length} entities detected
                  </span>
                )}
              </div>

              {selectedFileNode ? (
                <div className="space-y-4">
                  {/* File Metadata Overview */}
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                          Selected File
                        </span>
                        <p className="text-xs font-bold text-white break-all mt-0.5">
                          {selectedFileNode.name}
                        </p>
                      </div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {selectedFileNode.language && (
                          <span className="px-2 py-0.5 rounded-lg bg-brand-500/10 border border-brand-500/30 text-brand-300 text-[10px] font-semibold">
                            {selectedFileNode.language}
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-semibold capitalize">
                          {selectedFileNode.file_category || selectedFileNode.type}
                        </span>
                        {selectedFileNode.estimated_line_count !== undefined && (
                          <span className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-mono">
                            {selectedFileNode.estimated_line_count.toLocaleString()} lines
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="text-[11px] font-mono text-slate-400 break-all bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                        {selectedFileNode.path}
                      </p>
                    </div>
                  </div>

                  {/* STATIC CODE ENTITIES SECTION */}
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3.5">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <Boxes className="w-4 h-4 text-indigo-400" />
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                          Extracted Static Code Entities
                        </h4>
                      </div>

                      {/* Filter Pills */}
                      {fileEntities.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap">
                          {[
                            { key: 'ALL', label: `All (${fileEntities.length})` },
                            { key: 'CLASS', label: `Classes (${fileEntities.filter((e) => e.entity_type === 'CLASS').length})` },
                            { key: 'FUNCTION', label: `Functions (${fileEntities.filter((e) => e.entity_type === 'FUNCTION').length})` },
                            { key: 'METHOD', label: `Methods (${fileEntities.filter((e) => e.entity_type === 'METHOD').length})` },
                            { key: 'COMPONENT', label: `Components (${fileEntities.filter((e) => e.entity_type === 'COMPONENT').length})` },
                            { key: 'INTERFACE', label: `Interfaces (${fileEntities.filter((e) => e.entity_type === 'INTERFACE').length})` },
                          ]
                            .filter((f) => f.key === 'ALL' || !f.label.includes('(0)'))
                            .map((f) => (
                              <button
                                key={f.key}
                                onClick={() => setEntityFilter(f.key)}
                                className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold transition-colors ${
                                  entityFilter === f.key
                                    ? 'bg-brand-600 text-white shadow-sm'
                                    : 'bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-800'
                                }`}
                              >
                                {f.label}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>

                    {/* Entities Content */}
                    {loadingEntities ? (
                      <div className="py-8 text-center text-slate-400 flex flex-col items-center justify-center">
                        <Loader2 className="w-5 h-5 animate-spin text-brand-400 mb-2" />
                        <span className="text-xs">Extracting AST entities for this file...</span>
                      </div>
                    ) : fileEntities.length === 0 ? (
                      <div className="py-8 text-center text-slate-500 space-y-2">
                        <Braces className="w-7 h-7 text-slate-600 mx-auto" />
                        <p className="text-xs font-semibold text-slate-400">
                          No code entities detected for this file
                        </p>
                        <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                          Python AST and Tree-sitter extract modules, classes, methods, functions, interfaces, and components.
                        </p>
                        <button
                          onClick={handleParseCode}
                          disabled={parsing}
                          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold transition-all"
                        >
                          {parsing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Code2 className="w-3.5 h-3.5" />}
                          <span>{parsing ? 'Parsing...' : 'Parse Repository Code'}</span>
                        </button>
                      </div>
                    ) : (
                      <div className="max-h-[460px] overflow-y-auto space-y-3 pr-1">
                        {fileEntities
                          .filter((e) => entityFilter === 'ALL' || e.entity_type === entityFilter)
                          .map((entity) => {
                            const badgeColor =
                              entity.entity_type === 'CLASS'
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : entity.entity_type === 'FUNCTION'
                                ? 'bg-sky-500/15 text-sky-400 border-sky-500/30'
                                : entity.entity_type === 'METHOD'
                                ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                                : entity.entity_type === 'COMPONENT'
                                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                                : entity.entity_type === 'INTERFACE'
                                ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                                : 'bg-slate-700/50 text-slate-300 border-slate-600';

                            const bases = entity.metadata?.bases || entity.metadata?.inheritance || [];
                            const decorators = entity.metadata?.decorators || [];
                            const docstring = entity.metadata?.docstring;
                            const isAsync = entity.metadata?.is_async;
                            const returnType = entity.metadata?.return_annotation || entity.metadata?.return_type;

                            return (
                              <div
                                key={entity.id}
                                className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2.5"
                              >
                                {/* Entity Top Header */}
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                      className={`px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wider border uppercase ${badgeColor}`}
                                    >
                                      {entity.entity_type}
                                    </span>
                                    <span className="text-xs font-bold text-white font-mono">
                                      {entity.name}
                                    </span>
                                    {isAsync && (
                                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                        async
                                      </span>
                                    )}
                                    {entity.parent_entity && (
                                      <span className="text-[10px] text-slate-400 font-mono">
                                        in <strong className="text-slate-300">{entity.parent_entity}</strong>
                                      </span>
                                    )}
                                  </div>

                                  {/* Line Range */}
                                  <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                                    <Hash className="w-3 h-3 text-slate-500" />
                                    <span>
                                      L{entity.start_line}
                                      {entity.end_line && entity.end_line !== entity.start_line
                                        ? ` - L${entity.end_line}`
                                        : ''}
                                    </span>
                                  </div>
                                </div>

                                {/* Code Signature */}
                                {entity.signature && (
                                  <div className="bg-slate-900 p-2 rounded-lg border border-slate-800/90 font-mono text-[11px] text-brand-300 overflow-x-auto whitespace-pre">
                                    <code>{entity.signature}</code>
                                  </div>
                                )}

                                {/* Metadata Details: Bases, Decorators, Return Type, Docstring */}
                                <div className="space-y-1.5 text-[11px]">
                                  {bases.length > 0 && (
                                    <div className="flex items-center gap-1.5 text-slate-400">
                                      <span className="font-semibold text-slate-300">Inheritance:</span>
                                      <span className="text-emerald-300 font-mono">
                                        {bases.join(', ')}
                                      </span>
                                    </div>
                                  )}

                                  {decorators.length > 0 && (
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-semibold text-slate-400">Decorators:</span>
                                      {decorators.map((dec: string, idx: number) => (
                                        <span
                                          key={idx}
                                          className="px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 font-mono text-[10px]"
                                        >
                                          @{dec}
                                        </span>
                                      ))}
                                    </div>
                                  )}

                                  {returnType && (
                                    <div className="flex items-center gap-1.5 text-slate-400">
                                      <span className="font-semibold text-slate-300">Return:</span>
                                      <span className="text-cyan-300 font-mono">{returnType}</span>
                                    </div>
                                  )}

                                  {docstring && (
                                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800/60 text-slate-400 italic text-[11px] leading-relaxed">
                                      &ldquo;{docstring}&rdquo;
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center text-slate-500">
                  <FileCode className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-xs font-semibold text-slate-400">No File Selected</p>
                  <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                    Select any file in the tree to inspect its detected classes, functions, methods, components, signatures, and line ranges.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SECTION 4: COMPONENT DEPENDENCIES & RELATIONSHIP TOPOLOGY GRAPH (PHASE 5) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Workflow className="w-4 h-4 text-emerald-400" />
              <span>Component Dependencies & Architecture Topology</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Interactive React Flow graph with static analysis detected relationships (Imports, Calls, Extends, Implements, Depends On).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/diagrams"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all border border-slate-700"
            >
              <span>View in Diagrams</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <DependencyGraphViewer
          graphData={depGraphData}
          onRefresh={() => id && loadAllData(id)}
          isLoading={analyzingDeps}
        />
      </div>

      {/* SECTION 5: AUTOMATIC API DISCOVERY & SPECIFICATIONS (PHASE 6) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Server className="w-4 h-4 text-violet-400" />
              <span>Backend API Explorer & Specifications</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Discovered backend API routes with request/response schemas, parameters, auth requirements, and component links.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/documentation"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all border border-slate-700"
            >
              <span>API Reference Hub</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <APIExplorer
          projectId={project.id}
          projectName={project.name}
          onRefreshProject={() => loadAllData(project.id)}
        />
      </div>

      {/* SECTION 6: DATABASE STRUCTURE ANALYSIS & ER ARCHITECTURE (PHASE 7) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Database className="w-4 h-4 text-amber-400" />
              <span>Database Structure & Entity-Relationship Schema</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Static ORM inspection (SQLAlchemy, Django ORM, SQL files) with Mermaid ER diagrams, columns, types, and relationship cardinalities.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/diagrams"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all border border-slate-700"
            >
              <span>Full ER Canvas</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <DatabaseSchemaExplorer
          projectId={project.id}
          projectName={project.name}
          onRefreshProject={() => loadAllData(project.id)}
          defaultView="diagram"
        />
      </div>

      {/* SECTION 7: UNIFIED PROJECT KNOWLEDGE GRAPH (PHASE 8) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Network className="w-4 h-4 text-brand-400" />
              <span>Unified Project Architecture & Knowledge Graph</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Cross-tier project knowledge model connecting Folders → Files → Modules → Classes → Functions → APIs → Database Models.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/diagrams"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-all border border-slate-700"
            >
              <span>Dedicated Diagram Canvas</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <ArchitectureExplorer
          projectId={project.id}
          projectName={project.name}
        />
      </div>
    </div>
  );
};


