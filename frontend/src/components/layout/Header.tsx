import React, { useState } from 'react';
import { useProject } from '../../context/ProjectContext';
import { SystemStatusBadge } from './SystemStatusBadge';
import { CreateProjectModal } from '../projects/CreateProjectModal';
import { ChevronDown, Plus, FolderGit2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Header: React.FC = () => {
  const { projects, activeProject, setActiveProject } = useProject();
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <>
      <header className="h-16 border-b border-slate-800/80 bg-[#0B0F17]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
        {/* Left Section: Breadcrumbs or Active Project Indicator */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <button
              onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
              className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 hover:border-slate-700 hover:bg-slate-800/80 transition-all text-xs font-medium text-slate-200 focus:outline-none"
            >
              <FolderGit2 className="w-4 h-4 text-indigo-400" />
              <div className="flex flex-col text-left">
                <span className="text-[10px] text-slate-500 uppercase font-mono tracking-wider leading-none">
                  Active Project
                </span>
                <span className="font-semibold text-slate-200 truncate max-w-[160px]">
                  {activeProject ? activeProject.name : 'No Project Selected'}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
            </button>

            {/* Project Switcher Dropdown */}
            {isProjectDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-20"
                  onClick={() => setIsProjectDropdownOpen(false)}
                />
                <div className="absolute left-0 mt-2 w-64 bg-[#111827] border border-slate-800 rounded-xl shadow-2xl z-30 py-1.5 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-3 py-1.5 text-[11px] font-mono uppercase text-slate-500 border-b border-slate-800">
                    Switch Repository
                  </div>
                  <div className="max-h-48 overflow-y-auto py-1">
                    {projects.length === 0 ? (
                      <div className="px-3 py-3 text-xs text-slate-500 text-center">
                        No projects created yet
                      </div>
                    ) : (
                      projects.map((project) => (
                        <button
                          key={project.id}
                          onClick={() => {
                            setActiveProject(project);
                            setIsProjectDropdownOpen(false);
                            navigate(`/projects/${project.id}`);
                          }}
                          className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800/80 transition-colors ${
                            activeProject?.id === project.id
                              ? 'text-indigo-300 bg-indigo-500/10 font-medium'
                              : 'text-slate-300'
                          }`}
                        >
                          <span className="truncate">{project.name}</span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 capitalize">
                            {project.source_type}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                  <div className="border-t border-slate-800 pt-1 px-1">
                    <button
                      onClick={() => {
                        setIsProjectDropdownOpen(false);
                        setIsCreateModalOpen(true);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 rounded-lg transition-colors font-medium"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add New Project
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Section: System Health + Quick Actions */}
        <div className="flex items-center gap-3">
          <SystemStatusBadge />

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Project</span>
          </button>
        </div>
      </header>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />
    </>
  );
};
