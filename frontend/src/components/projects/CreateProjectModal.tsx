import React, { useState, useRef } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { useProject } from '../../context/ProjectContext';
import { projectsApi } from '../../api/projects';
import { FolderGit2, Upload, FileCode2, AlertTriangle, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ isOpen, onClose }) => {
  const { createProject, refreshProjects, setActiveProject } = useProject();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sourceType, setSourceType] = useState<'github' | 'zip' | 'local'>('github');
  const [sourceUrl, setSourceUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusStep, setStatusStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setName('');
    setDescription('');
    setSourceUrl('');
    setSelectedFile(null);
    setUploadProgress(null);
    setStatusStep('');
    setError(null);
  };

  const handleFileChange = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a valid .zip archive file.');
      return;
    }
    const maxBytes = 50 * 1024 * 1024; // 50MB
    if (file.size > maxBytes) {
      setError('File size exceeds the 50MB limit.');
      return;
    }
    setError(null);
    setSelectedFile(file);
    if (!name.trim()) {
      const suggestedName = file.name.replace(/\.zip$/i, '');
      setName(suggestedName);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a project or repository name.');
      return;
    }

    if (sourceType === 'github' && !sourceUrl.trim()) {
      setError('Please provide a public GitHub repository URL.');
      return;
    }

    if (sourceType === 'zip' && !selectedFile) {
      setError('Please select a ZIP file to upload.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setStatusStep('Initializing project record...');

      // 1. Create project record
      const project = await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        source_type: sourceType,
        source_url: sourceType === 'github' ? sourceUrl.trim() : undefined,
      });

      // 2. Perform ingestion based on source type
      if (sourceType === 'zip' && selectedFile) {
        setStatusStep('Uploading and extracting ZIP archive...');
        await projectsApi.uploadZip(project.id, selectedFile, (progress) => {
          setUploadProgress(progress);
        });
      } else if (sourceType === 'github') {
        setStatusStep(`Cloning repository from GitHub (${sourceUrl})...`);
        await projectsApi.cloneRepo(project.id, sourceUrl.trim());
      }

      await refreshProjects();
      const updatedProject = await projectsApi.getById(project.id);
      setActiveProject(updatedProject);

      resetForm();
      onClose();
      navigate(`/projects/${project.id}`);
    } catch (err: any) {
      console.error('Project creation error:', err);
      setError(err.message || 'Failed to create and ingest project.');
    } finally {
      setIsSubmitting(false);
      setUploadProgress(null);
      setStatusStep('');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!isSubmitting) {
          resetForm();
          onClose();
        }
      }}
      title="Add New Repository"
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-xs rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Source Type Selector */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              setSourceType('github');
              setError(null);
            }}
            className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all ${
              sourceType === 'github'
                ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-glow'
                : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <FolderGit2 className="w-4 h-4 text-indigo-400" />
            GitHub Repository
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              setSourceType('zip');
              setError(null);
            }}
            className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all ${
              sourceType === 'zip'
                ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-glow'
                : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4 text-indigo-400" />
            Upload ZIP Archive
          </button>
        </div>

        {/* Project Name */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Project / Repository Name <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            required
            disabled={isSubmitting}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. FastAPI Web Framework"
            className="w-full px-3.5 py-2 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Source Inputs */}
        {sourceType === 'github' ? (
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Public GitHub Repository URL <span className="text-rose-400">*</span>
            </label>
            <input
              type="url"
              required
              disabled={isSubmitting}
              value={sourceUrl}
              onChange={(e) => {
                setSourceUrl(e.target.value);
                if (!name.trim()) {
                  // Extract repository name from URL
                  const parts = e.target.value.replace(/\.git$/i, '').split('/');
                  if (parts.length > 1 && parts[parts.length - 1]) {
                    setName(parts[parts.length - 1]);
                  }
                }
              }}
              placeholder="https://github.com/organization/repository"
              className="w-full px-3.5 py-2 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono"
            />
            <span className="text-[11px] text-slate-500 mt-1 block">
              Direct depth-1 clone. Code is never executed.
            </span>
          </div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              ZIP Project Archive <span className="text-rose-400">*</span>
            </label>
            <input
              type="file"
              ref={fileInputRef}
              accept=".zip"
              disabled={isSubmitting}
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileChange(e.target.files[0]);
                }
              }}
            />

            {!selectedFile ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileChange(e.dataTransfer.files[0]);
                  }
                }}
                className={`p-6 border-2 border-dashed rounded-xl text-center cursor-pointer transition-all ${
                  isDragOver
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/70'
                }`}
              >
                <Upload className="w-7 h-7 text-indigo-400 mx-auto mb-2" />
                <div className="text-xs font-semibold text-slate-200">
                  Click to select or drag & drop .ZIP archive
                </div>
                <div className="text-[11px] text-slate-500 mt-1">
                  Supports up to 50MB. Automatically strips node_modules, __pycache__, and .git.
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300">
                    <Upload className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-mono font-medium text-white truncate max-w-xs">
                      {selectedFile.name}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </div>
                  </div>
                </div>
                {!isSubmitting && (
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Description <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <textarea
            rows={2}
            disabled={isSubmitting}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief overview of repository architecture or purpose..."
            className="w-full px-3.5 py-2 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Ingestion Progress State */}
        {isSubmitting && (
          <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 space-y-2 animate-pulse">
            <div className="flex items-center justify-between text-xs text-indigo-300 font-medium">
              <span>{statusStep || 'Processing repository ingestion...'}</span>
              {uploadProgress !== null && <span>{uploadProgress}%</span>}
            </div>
            {uploadProgress !== null && (
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
          <Button
            variant="outline"
            size="md"
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              resetForm();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            type="submit"
            isLoading={isSubmitting}
            leftIcon={<FileCode2 className="w-4 h-4" />}
          >
            {sourceType === 'zip' ? 'Upload & Ingest' : 'Clone & Ingest'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
