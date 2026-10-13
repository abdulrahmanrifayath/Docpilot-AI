import React, { createContext, useContext, useState, useEffect } from 'react';
import { Project, SystemStatus } from '../types';
import { fetchProjects, fetchSystemStatus } from '../api/client';

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  setActiveProject: (project: Project | null) => void;
  systemStatus: SystemStatus | null;
  refreshProjects: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  loading: boolean;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProjectState] = useState<Project | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshProjects = async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);

      // Restore or default active project
      const savedId = localStorage.getItem('docpilot_active_project_id');
      if (savedId) {
        const found = data.find((p) => p.id === savedId);
        if (found) {
          setActiveProjectState(found);
          return;
        }
      }
      if (data.length > 0 && !activeProject) {
        setActiveProjectState(data[0]);
      }
    } catch (err) {
      console.error('Failed to load projects', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    try {
      const status = await fetchSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Failed to fetch system status', err);
    }
  };

  const setActiveProject = (project: Project | null) => {
    setActiveProjectState(project);
    if (project) {
      localStorage.setItem('docpilot_active_project_id', project.id);
    } else {
      localStorage.removeItem('docpilot_active_project_id');
    }
  };

  useEffect(() => {
    refreshProjects();
    refreshStatus();

    // Poll status and projects periodically
    const timer = setInterval(() => {
      refreshStatus();
      refreshProjects();
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        setActiveProject,
        systemStatus,
        refreshProjects,
        refreshStatus,
        loading,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjects = () => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjects must be used within a ProjectProvider');
  }
  return context;
};
