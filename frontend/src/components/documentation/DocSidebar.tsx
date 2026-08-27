import React from 'react';
import { Documentation } from '../../types';
import { Button } from '../common/Button';
import {
  FileText,
  Search,
  Plus,
  Sparkles,
  Layers,
  Globe,
  Database,
  Box,
  Code2,
  Folder,
  FileCode,
} from 'lucide-react';

interface DocSidebarProps {
  documents: Documentation[];
  selectedDocId: string | null;
  onSelectDoc: (id: string) => void;
  selectedType: string;
  onSelectType: (type: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onOpenGenerateModal: () => void;
  countsByType: Record<string, number>;
}

const CATEGORY_TABS = [
  { id: 'ALL', label: 'All Docs' },
  { id: 'PROJECT_OVERVIEW', label: 'Overview' },
  { id: 'README', label: 'README' },
  { id: 'ARCHITECTURE_OVERVIEW', label: 'Architecture' },
  { id: 'API_DOCUMENTATION', label: 'APIs' },
  { id: 'DATABASE_DOCUMENTATION', label: 'Database' },
  { id: 'FOLDER_DOC', label: 'Folders' },
  { id: 'FILE_DOC', label: 'Files' },
  { id: 'CLASS_DOC', label: 'Classes' },
  { id: 'FUNCTION_DOC', label: 'Functions' },
];

const getCategoryIcon = (type: string) => {
  switch (type.toUpperCase()) {
    case 'PROJECT_OVERVIEW':
      return <Sparkles className="w-3.5 h-3.5 text-indigo-400" />;
    case 'README':
      return <FileText className="w-3.5 h-3.5 text-emerald-400" />;
    case 'ARCHITECTURE_OVERVIEW':
      return <Layers className="w-3.5 h-3.5 text-purple-400" />;
    case 'API_DOCUMENTATION':
      return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
    case 'DATABASE_DOCUMENTATION':
      return <Database className="w-3.5 h-3.5 text-amber-400" />;
    case 'FOLDER_DOC':
      return <Folder className="w-3.5 h-3.5 text-purple-400" />;
    case 'FILE_DOC':
      return <FileCode className="w-3.5 h-3.5 text-blue-400" />;
    case 'CLASS_DOC':
      return <Box className="w-3.5 h-3.5 text-pink-400" />;
    case 'FUNCTION_DOC':
      return <Code2 className="w-3.5 h-3.5 text-teal-400" />;
    default:
      return <FileText className="w-3.5 h-3.5 text-slate-400" />;
  }
};

export const DocSidebar: React.FC<DocSidebarProps> = ({
  documents,
  selectedDocId,
  onSelectDoc,
  selectedType,
  onSelectType,
  searchQuery,
  onSearchChange,
  onOpenGenerateModal,
  countsByType,
}) => {
  const filteredDocs = documents.filter((doc) => {
    const matchesType = selectedType === 'ALL' || doc.document_type === selectedType;
    const matchesSearch =
      !searchQuery.trim() ||
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.document_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.content.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="w-full lg:w-80 bg-slate-900/70 border border-slate-800 rounded-2xl flex flex-col backdrop-blur-xl overflow-hidden shrink-0">
      {/* Header with Generate Button */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between gap-2 bg-slate-950/60">
        <div>
          <h3 className="text-sm font-bold text-white tracking-tight uppercase">Documentation</h3>
          <p className="text-[11px] text-slate-400 font-mono">
            {documents.length} document{documents.length !== 1 ? 's' : ''} generated
          </p>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenGenerateModal}
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          Generate
        </Button>
      </div>

      {/* Search Input */}
      <div className="p-3 border-b border-slate-800 bg-slate-950/30">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search documentation..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>
      </div>

      {/* Category Tabs */}
      <div className="px-3 py-2 border-b border-slate-800 flex items-center gap-1 overflow-x-auto no-scrollbar bg-slate-950/20 text-xs font-mono">
        {CATEGORY_TABS.map((tab) => {
          const count =
            tab.id === 'ALL'
              ? documents.length
              : countsByType[tab.id] || 0;
          const isSelected = selectedType === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onSelectType(tab.id)}
              className={`px-2.5 py-1 rounded-lg border whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 shadow-sm'
                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              <span>{tab.label}</span>
              {count > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-900 text-slate-400">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredDocs.length === 0 ? (
          <div className="text-center py-12 px-4">
            <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-mono">No matching documents found.</p>
          </div>
        ) : (
          filteredDocs.map((doc) => {
            const isSelected = doc.id === selectedDocId;

            return (
              <div
                key={doc.id}
                onClick={() => onSelectDoc(doc.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-indigo-600/15 border-indigo-500/50 shadow-md'
                    : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    {getCategoryIcon(doc.document_type)}
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                      {doc.document_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    v{doc.version}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-white tracking-tight line-clamp-1">
                  {doc.title}
                </h4>

                <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 font-mono leading-snug">
                  {doc.content.replace(/[#*`_]/g, '').slice(0, 120)}...
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
