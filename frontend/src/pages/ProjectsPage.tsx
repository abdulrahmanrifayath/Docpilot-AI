import React, { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { CreateProjectModal } from '../components/projects/CreateProjectModal';
import { projectsApi } from '../api/projects';
import { ProjectStatus } from '../types';
import {
  FolderGit2,
  Plus,
  Search,
  Trash2,
  Calendar,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const getStatusBadge = (status: ProjectStatus) => {
  switch (status) {
    case 'READY':
      return <Badge variant="success" dot>READY</Badge>;
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

export const ProjectsPage: React.FC = () => {
  const { projects, refreshProjects, setActiveProject } = useProject();
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(search.toLowerCase()));
    const matchesType = filterType === 'all' || p.source_type === filterType;
    return matchesSearch && matchesType;
  });

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this repository from DocPilot? All extracted files and models will be deleted.')) return;

    try {
      setDeletingId(id);
      await projectsApi.delete(id);
      await refreshProjects();
    } catch (err) {
      console.error('Failed to delete project:', err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Repositories & Projects</h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your ingested software repositories, monitor ingestion status, and view code trees.
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={() => setIsCreateOpen(true)}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          Add Repository
        </Button>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search repositories by name or description..."
            className="w-full pl-10 pr-4 py-2 text-xs bg-slate-900/80 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2">
          {['all', 'github', 'zip'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                filterType === type
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-slate-200'
              }`}
            >
              {type === 'all' ? 'All Sources' : type}
            </button>
          ))}
        </div>
      </div>

      {/* Projects Grid */}
      {filteredProjects.length === 0 ? (
        <Card className="p-12 text-center border-dashed">
          <FolderGit2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Projects Found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {search || filterType !== 'all'
              ? 'No projects matched your search criteria.'
              : 'Add your first GitHub repository or upload a ZIP file to start analyzing.'}
          </p>
          <Button
            variant="primary"
            size="sm"
            className="mt-4"
            onClick={() => setIsCreateOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Add Repository
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <Card
              key={project.id}
              hoverable
              onClick={() => {
                setActiveProject(project);
                navigate(`/projects/${project.id}`);
              }}
              className="flex flex-col justify-between group relative overflow-hidden"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                      <FolderGit2 className="w-4 h-4" />
                    </div>
                    <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors truncate max-w-[170px]">
                      {project.name}
                    </h3>
                  </div>
                  {getStatusBadge(project.status)}
                </div>

                <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                  {project.description || 'No description provided for this repository.'}
                </p>

                {project.status === 'FAILED' && project.status_message && (
                  <div className="mt-2.5 p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300 truncate">
                    {project.status_message}
                  </div>
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                <div className="flex flex-col gap-1 text-[11px]">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 capitalize">
                      {project.source_type}
                    </span>
                    <span className="flex items-center gap-1 text-slate-500">
                      <Calendar className="w-3 h-3" />
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {project.last_analyzed_at && (
                    <div className="flex items-center gap-1 text-slate-400">
                      <Clock className="w-3 h-3" />
                      <span>Analyzed {new Date(project.last_analyzed_at).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => handleDelete(e, project.id)}
                    disabled={deletingId === project.id}
                    title="Delete project"
                    className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateProjectModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </div>
  );
};
