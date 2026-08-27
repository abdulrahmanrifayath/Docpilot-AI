import React, { useState, useEffect, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import { projectsApi } from '../api/projects';
import { DocumentationListResponse } from '../types';
import { DocSidebar } from '../components/documentation/DocSidebar';
import { DocReader } from '../components/documentation/DocReader';
import { DocGenerateModal } from '../components/documentation/DocGenerateModal';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import {
  BookOpen,
  Sparkles,
  Info,
  RefreshCw,
  FileText,
} from 'lucide-react';

export const DocumentationPage: React.FC = () => {
  const { activeProject } = useProject();
  const [docList, setDocList] = useState<DocumentationListResponse | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [isLoading, setIsLoading] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);

  const fetchDocs = useCallback(async () => {
    if (!activeProject) return;

    try {
      setIsLoading(true);
      const data = await projectsApi.getDocs(activeProject.id);
      setDocList(data);

      if (data.documents.length > 0 && !selectedDocId) {
        setSelectedDocId(data.documents[0].id);
      } else if (
        selectedDocId &&
        !data.documents.some((d) => d.id === selectedDocId) &&
        data.documents.length > 0
      ) {
        setSelectedDocId(data.documents[0].id);
      }
    } catch (err) {
      console.error('Failed to load project documentation:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeProject, selectedDocId]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleRegenerate = async (docId: string) => {
    if (!activeProject) return;

    try {
      setIsRegenerating(true);
      const updated = await projectsApi.regenerateDoc(activeProject.id, docId);

      setDocList((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          documents: prev.documents.map((d) => (d.id === updated.id ? updated : d)),
        };
      });
    } catch (err) {
      console.error('Failed to regenerate document:', err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const selectedDoc = docList?.documents.find((d) => d.id === selectedDocId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-indigo-400" />
            Documentation Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            AI-powered software documentation grounded in repository code, APIs, and database models.
          </p>
        </div>

        {activeProject && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchDocs}
              isLoading={isLoading}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsGenerateModalOpen(true)}
              leftIcon={<Sparkles className="w-3.5 h-3.5" />}
            >
              Generate AI Docs
            </Button>
          </div>
        )}
      </div>

      {/* Main Content */}
      {!activeProject ? (
        <Card className="p-12 text-center border-dashed">
          <Info className="w-8 h-8 text-slate-500 mx-auto mb-2" />
          <h3 className="text-sm font-bold text-white">No Project Selected</h3>
          <p className="text-xs text-slate-400 mt-1">
            Please select or create a project from the project list to view or generate documentation.
          </p>
        </Card>
      ) : isLoading && !docList ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 text-indigo-500 border-2 border-current border-t-transparent rounded-full" />
        </div>
      ) : docList?.documents.length === 0 ? (
        <Card className="p-12 text-center border-dashed bg-slate-900/50">
          <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white">No Documentation Generated Yet</h3>
          <p className="text-xs text-slate-400 mt-1.5 max-w-md mx-auto leading-relaxed">
            DocPilot AI can automatically generate comprehensive project overviews, READMEs, architectural designs, API reference specs, and database documentation for <strong className="text-slate-200">{activeProject.name}</strong>.
          </p>
          <div className="mt-5">
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsGenerateModalOpen(true)}
              leftIcon={<Sparkles className="w-4 h-4" />}
            >
              Generate AI Documentation
            </Button>
          </div>
        </Card>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6 min-h-[680px]">
          {/* Left Sidebar */}
          <DocSidebar
            documents={docList?.documents || []}
            selectedDocId={selectedDocId}
            onSelectDoc={(id) => setSelectedDocId(id)}
            selectedType={selectedType}
            onSelectType={(t) => setSelectedType(t)}
            searchQuery={searchQuery}
            onSearchChange={(q) => setSearchQuery(q)}
            onOpenGenerateModal={() => setIsGenerateModalOpen(true)}
            countsByType={docList?.counts_by_type || {}}
          />

          {/* Right Main Viewer */}
          {selectedDoc ? (
            <DocReader
              doc={selectedDoc}
              onRegenerate={handleRegenerate}
              isRegenerating={isRegenerating}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 bg-slate-900/50 border border-slate-800 rounded-2xl">
              <p className="text-xs text-slate-500 font-mono">Select a document from the left to read.</p>
            </div>
          )}
        </div>
      )}

      {/* Generate Modal */}
      {activeProject && (
        <DocGenerateModal
          projectId={activeProject.id}
          isOpen={isGenerateModalOpen}
          onClose={() => setIsGenerateModalOpen(false)}
          onSuccess={fetchDocs}
        />
      )}
    </div>
  );
};
