import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { projectsApi } from '../api/projects';
import { Project } from '../types';
import { useProject } from '../context/ProjectContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import {
  BookOpen,
  GitBranch,
  Bot,
  ExternalLink,
  Calendar,
  Layers,
  ArrowLeft,
} from 'lucide-react';

export const ProjectDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setActiveProject } = useProject();
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchProject = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await projectsApi.getById(id);
        setProject(data);
        setActiveProject(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load project details.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchProject();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !project) {
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
              <Badge variant={project.status === 'ready' ? 'success' : 'neutral'} dot>
                {project.status}
              </Badge>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span className="font-mono uppercase text-slate-300">{project.source_type}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3 text-slate-500" />
                Created {new Date(project.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        {/* Action navigation pills */}
        <div className="flex items-center gap-2">
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
            <Button variant="primary" size="sm" leftIcon={<Bot className="w-4 h-4" />}>
              AI Assistant
            </Button>
          </Link>
        </div>
      </div>

      {/* Description Card */}
      <Card className="p-6">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Repository Description</h3>
        <p className="text-sm text-slate-200 leading-relaxed">
          {project.description || 'No description provided for this repository.'}
        </p>

        {project.source_url && (
          <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center gap-2 text-xs">
            <span className="text-slate-400">Remote URL:</span>
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

      {/* Pipeline Status Breakdown */}
      <div>
        <h2 className="text-base font-semibold text-white tracking-tight mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          DocPilot Analysis Pipeline Status
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white">1. Discovery & Language</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Phase 2
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Detects Python, TypeScript, and JavaScript sources and creates file inventory.
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white">2. AST Code Analysis</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                Phase 2
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Extracts functions, classes, dependencies, endpoints, and database models.
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white">3. Knowledge & AI Chat</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">
                Phase 3-4
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Synthesizes documentation, generates Mermaid diagrams, and indexes ChromaDB vectors.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
