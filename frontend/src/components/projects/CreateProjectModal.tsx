import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { useProject } from '../../context/ProjectContext';
import { FolderGit2, Upload, FileCode2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ isOpen, onClose }) => {
  const { createProject } = useProject();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sourceType, setSourceType] = useState<'zip' | 'github'>('github');
  const [sourceUrl, setSourceUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a project name.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      const project = await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        source_type: sourceType,
        source_url: sourceType === 'github' ? sourceUrl.trim() : undefined,
      });
      onClose();
      // Reset fields
      setName('');
      setDescription('');
      setSourceUrl('');
      // Navigate to project details
      navigate(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create project.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add New Repository" maxWidth="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-xs rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300">
            {error}
          </div>
        )}

        {/* Source Type Selector */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setSourceType('github')}
            className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-all ${
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
            onClick={() => setSourceType('zip')}
            className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-sm font-medium transition-all ${
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
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. DocPilot AI Core"
            className="w-full px-3.5 py-2 text-sm bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* GitHub URL or ZIP note */}
        {sourceType === 'github' ? (
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              GitHub Repository URL
            </label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://github.com/organization/repository"
              className="w-full px-3.5 py-2 text-sm bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-xs"
            />
          </div>
        ) : (
          <div className="p-4 border-2 border-dashed border-slate-800 rounded-lg text-center hover:border-indigo-500/50 transition-colors">
            <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
            <div className="text-xs text-slate-300 font-medium">ZIP Archive Upload</div>
            <p className="text-[11px] text-slate-500 mt-1">
              Supports .zip project bundles (will be extracted and analyzed in Phase 2)
            </p>
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Description <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief overview of the codebase architecture and objectives..."
            className="w-full px-3.5 py-2 text-sm bg-slate-900 border border-slate-700/80 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
          <Button variant="outline" size="md" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            type="submit"
            isLoading={isSubmitting}
            leftIcon={<FileCode2 className="w-4 h-4" />}
          >
            Create Project
          </Button>
        </div>
      </form>
    </Modal>
  );
};
