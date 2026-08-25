import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Project, ProjectCreateInput } from '../types';
import { projectsApi } from '../api/projects';

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  isLoading: boolean;
  error: string | null;
  setActiveProject: (project: Project | null) => void;
  setActiveProjectId: (id: string) => void;
  refreshProjects: () => Promise<void>;
  createProject: (input: ProjectCreateInput) => Promise<Project>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshProjects = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await projectsApi.list();
      setProjects(data);
      if (data.length > 0 && !activeProject) {
        // Retrieve stored active project ID from localStorage or default to first
        const savedId = localStorage.getItem('docpilot_active_project_id');
        const found = data.find((p) => p.id === savedId);
        setActiveProject(found || data[0]);
      }
    } catch (err: any) {
      console.error('Failed to fetch projects:', err);
      setError(err.message || 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    refreshProjects();
  }, []);

  const handleSetActiveProject = (project: Project | null) => {
    setActiveProject(project);
    if (project) {
      localStorage.setItem('docpilot_active_project_id', project.id);
    } else {
      localStorage.removeItem('docpilot_active_project_id');
    }
  };

  const setActiveProjectId = (id: string) => {
    const found = projects.find((p) => p.id === id);
    if (found) {
      handleSetActiveProject(found);
    }
  };

  const createProject = async (input: ProjectCreateInput): Promise<Project> => {
    const newProj = await projectsApi.create(input);
    setProjects((prev) => [newProj, ...prev]);
    handleSetActiveProject(newProj);
    return newProj;
  };

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        isLoading,
        error,
        setActiveProject: handleSetActiveProject,
        setActiveProjectId,
        refreshProjects,
        createProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = (): ProjectContextType => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};
