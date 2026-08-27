import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Documentation } from '../../types';
import { Button } from '../common/Button';
import {
  FileText,
  Copy,
  Check,
  Download,
  RefreshCw,
  Layers,
  Globe,
  Database,
  Box,
  Code2,
  Folder,
  FileCode,
  Sparkles,
  Calendar,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface DocReaderProps {
  doc: Documentation;
  onRegenerate: (docId: string) => Promise<void>;
  isRegenerating: boolean;
}

const getCategoryBadgeClass = (type: string) => {
  switch (type.toUpperCase()) {
    case 'PROJECT_OVERVIEW':
      return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
    case 'README':
      return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    case 'ARCHITECTURE_OVERVIEW':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    case 'API_DOCUMENTATION':
      return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
    case 'DATABASE_DOCUMENTATION':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
    case 'FOLDER_DOC':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    case 'FILE_DOC':
      return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    case 'CLASS_DOC':
      return 'bg-pink-500/20 text-pink-300 border-pink-500/30';
    case 'FUNCTION_DOC':
      return 'bg-teal-500/20 text-teal-300 border-teal-500/30';
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700';
  }
};

const getCategoryIcon = (type: string) => {
  switch (type.toUpperCase()) {
    case 'PROJECT_OVERVIEW':
      return <Sparkles className="w-4 h-4 text-indigo-400" />;
    case 'README':
      return <FileText className="w-4 h-4 text-emerald-400" />;
    case 'ARCHITECTURE_OVERVIEW':
      return <Layers className="w-4 h-4 text-purple-400" />;
    case 'API_DOCUMENTATION':
      return <Globe className="w-4 h-4 text-cyan-400" />;
    case 'DATABASE_DOCUMENTATION':
      return <Database className="w-4 h-4 text-amber-400" />;
    case 'FOLDER_DOC':
      return <Folder className="w-4 h-4 text-purple-400" />;
    case 'FILE_DOC':
      return <FileCode className="w-4 h-4 text-blue-400" />;
    case 'CLASS_DOC':
      return <Box className="w-4 h-4 text-pink-400" />;
    case 'FUNCTION_DOC':
      return <Code2 className="w-4 h-4 text-teal-400" />;
    default:
      return <FileText className="w-4 h-4 text-slate-400" />;
  }
};

export const DocReader: React.FC<DocReaderProps> = ({ doc, onRegenerate, isRegenerating }) => {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(doc.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([doc.content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${doc.document_type.toLowerCase()}_v${doc.version}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const formattedDate = new Date(doc.updated_at || doc.generated_at).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="flex-1 bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden flex flex-col backdrop-blur-xl">
      {/* Header Toolbar */}
      <div className="p-5 border-b border-slate-800 bg-slate-950/60 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <div className="w-7 h-7 rounded-lg bg-slate-900 border border-slate-700 flex items-center justify-center">
              {getCategoryIcon(doc.document_type)}
            </div>
            <span
              className={`px-2.5 py-0.5 rounded-lg border text-xs font-mono font-bold uppercase tracking-wider ${getCategoryBadgeClass(
                doc.document_type
              )}`}
            >
              {doc.document_type.replace(/_/g, ' ')}
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 font-mono text-[11px]">
              v{doc.version}
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 font-mono text-[11px]">
              {doc.model}
            </span>
          </div>

          <h2 className="text-xl font-bold text-white tracking-tight">{doc.title}</h2>

          <div className="flex items-center gap-2 mt-1 text-xs text-slate-400 font-mono">
            <Calendar className="w-3.5 h-3.5" />
            <span>Updated {formattedDate}</span>
            {doc.metadata_json?.tokens_used && (
              <>
                <span>•</span>
                <span>{doc.metadata_json.tokens_used} tokens</span>
              </>
            )}
            {doc.metadata_json?.duration_ms && (
              <>
                <span>•</span>
                <span>{doc.metadata_json.duration_ms}ms</span>
              </>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            leftIcon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            leftIcon={<Download className="w-3.5 h-3.5" />}
          >
            Download .md
          </Button>

          <Button
            variant="primary"
            size="sm"
            isLoading={isRegenerating}
            onClick={() => onRegenerate(doc.id)}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />}
          >
            Regenerate
          </Button>
        </div>
      </div>

      {/* Source References Accordion */}
      {doc.source_entities && doc.source_entities.length > 0 && (
        <div className="border-b border-slate-800 bg-slate-950/40">
          <button
            onClick={() => setShowSources(!showSources)}
            className="w-full px-5 py-2.5 flex items-center justify-between text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
          >
            <div className="flex items-center gap-2">
              <ExternalLink className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                <strong>Referenced Entities & Source Files</strong> ({doc.source_entities.length})
              </span>
            </div>
            {showSources ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showSources && (
            <div className="px-5 pb-3.5 pt-1 flex flex-wrap gap-1.5 font-mono text-xs max-h-36 overflow-y-auto">
              {doc.source_entities.map((item, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-1 text-[11px]"
                >
                  <FileCode className="w-3 h-3 text-slate-500" />
                  <code>{item}</code>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Markdown Document Content */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-none prose prose-invert prose-indigo">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ node, ...props }) => (
              <h1 className="text-2xl font-bold text-white border-b border-slate-800 pb-3 mb-6 mt-2" {...props} />
            ),
            h2: ({ node, ...props }) => (
              <h2 className="text-lg font-bold text-indigo-300 border-b border-slate-800/80 pb-2 mb-4 mt-8 flex items-center gap-2" {...props} />
            ),
            h3: ({ node, ...props }) => (
              <h3 className="text-base font-semibold text-slate-100 mb-3 mt-6" {...props} />
            ),
            p: ({ node, ...props }) => (
              <p className="text-sm text-slate-300 leading-relaxed mb-4" {...props} />
            ),
            ul: ({ node, ...props }) => (
              <ul className="list-disc list-inside space-y-1.5 text-sm text-slate-300 mb-4 ml-2" {...props} />
            ),
            ol: ({ node, ...props }) => (
              <ol className="list-decimal list-inside space-y-1.5 text-sm text-slate-300 mb-4 ml-2" {...props} />
            ),
            li: ({ node, ...props }) => (
              <li className="text-slate-300" {...props} />
            ),
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto my-6 rounded-xl border border-slate-800 bg-slate-950">
                <table className="w-full text-left text-xs border-collapse font-mono" {...props} />
              </div>
            ),
            thead: ({ node, ...props }) => (
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-300 uppercase tracking-wider" {...props} />
            ),
            th: ({ node, ...props }) => (
              <th className="py-3 px-4 font-bold" {...props} />
            ),
            td: ({ node, ...props }) => (
              <td className="py-2.5 px-4 border-b border-slate-900 text-slate-300" {...props} />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote className="border-l-4 border-indigo-500 pl-4 py-1.5 my-4 bg-indigo-500/10 rounded-r-xl text-slate-300 text-sm italic" {...props} />
            ),
            code: ({ node, inline, className, children, ...props }: any) => {
              if (inline) {
                return (
                  <code className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-indigo-300 text-xs font-mono" {...props}>
                    {children}
                  </code>
                );
              }
              return (
                <div className="relative my-4 rounded-xl overflow-hidden border border-slate-800 bg-slate-950 font-mono text-xs">
                  <div className="px-4 py-2 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between text-slate-400">
                    <span>Code Snippet</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
                      }}
                      className="hover:text-white transition-colors"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <pre className="p-4 overflow-x-auto text-slate-200">
                    <code>{children}</code>
                  </pre>
                </div>
              );
            },
          }}
        >
          {doc.content}
        </ReactMarkdown>
      </div>
    </div>
  );
};
