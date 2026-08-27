import React, { useState, useMemo } from 'react';
import { StructureItem, ProjectStructureResponse } from '../../types';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  FileJson,
  File,
  Search,
  ChevronRight,
  ChevronDown,
  ChevronsDownUp,
  ChevronsUpDown,
  HardDrive,
  Code2,
  FileSpreadsheet,
} from 'lucide-react';

interface FileTreeExplorerProps {
  data: ProjectStructureResponse;
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const getFileIcon = (ext?: string | null, language?: string | null) => {
  if (language === 'Python' || ext === '.py') return <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />;
  if (language === 'TypeScript' || ext === '.ts' || ext === '.tsx') return <FileCode className="w-4 h-4 text-blue-400 shrink-0" />;
  if (language === 'JavaScript' || ext === '.js' || ext === '.jsx' || ext === '.mjs') return <FileCode className="w-4 h-4 text-amber-400 shrink-0" />;
  if (language === 'JSON' || ext === '.json') return <FileJson className="w-4 h-4 text-orange-400 shrink-0" />;
  if (language === 'Markdown' || language === 'Text' || ext === '.md' || ext === '.txt') return <FileText className="w-4 h-4 text-slate-400 shrink-0" />;
  if (language === 'HTML' || language === 'CSS' || language === 'SCSS' || ext === '.html' || ext === '.css' || ext === '.scss') return <FileCode className="w-4 h-4 text-cyan-400 shrink-0" />;
  if (language === 'SQL' || ext === '.sql') return <FileSpreadsheet className="w-4 h-4 text-indigo-400 shrink-0" />;
  if (language === 'Dockerfile' || ext === '.dockerfile') return <FileCode className="w-4 h-4 text-sky-400 shrink-0" />;
  return <File className="w-4 h-4 text-slate-400 shrink-0" />;
};

const getCategoryBadge = (category: string) => {
  switch (category) {
    case 'source_code':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">code</span>;
    case 'configuration':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">config</span>;
    case 'documentation':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-700/40 text-slate-300 border border-slate-600/40">docs</span>;
    case 'infrastructure':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">infra</span>;
    case 'style':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">style</span>;
    case 'data':
      return <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">data</span>;
    default:
      return null;
  }
};

interface TreeNodeProps {
  item: StructureItem;
  search: string;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
  depth?: number;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  item,
  search,
  expandedDirs,
  toggleDir,
  depth = 0,
}) => {
  const isDir = item.type === 'directory';
  const isExpanded = expandedDirs.has(item.path);

  // Search filter
  const matchesSearch = useMemo(() => {
    if (!search.trim()) return true;
    const query = search.toLowerCase();
    if (
      item.name.toLowerCase().includes(query) ||
      item.path.toLowerCase().includes(query) ||
      (item.language && item.language.toLowerCase().includes(query))
    ) {
      return true;
    }
    const checkChildren = (children?: StructureItem[] | null): boolean => {
      if (!children) return false;
      return children.some(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.path.toLowerCase().includes(query) ||
          (c.language && c.language.toLowerCase().includes(query)) ||
          checkChildren(c.children)
      );
    };
    return checkChildren(item.children);
  }, [item, search]);

  if (!matchesSearch) return null;

  return (
    <div>
      <div
        onClick={() => {
          if (isDir) toggleDir(item.path);
        }}
        style={{ paddingLeft: `${depth * 18 + 8}px` }}
        className={`flex items-center justify-between py-1.5 pr-3 rounded-lg text-xs cursor-pointer select-none transition-colors group ${
          isDir
            ? 'hover:bg-slate-800/70 text-slate-200 font-medium'
            : 'hover:bg-slate-800/40 text-slate-300'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {isDir ? (
            <>
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              )}
              {isExpanded ? (
                <FolderOpen className="w-4 h-4 text-indigo-400 shrink-0" />
              ) : (
                <Folder className="w-4 h-4 text-indigo-400 shrink-0" />
              )}
            </>
          ) : (
            <>
              <span className="w-3.5 h-3.5 shrink-0" />
              {getFileIcon(item.extension, item.language)}
            </>
          )}

          <span className="truncate font-mono group-hover:text-white transition-colors">
            {item.name}
          </span>

          {!isDir && getCategoryBadge(item.category)}
        </div>

        <div className="flex items-center gap-3 text-[11px] text-slate-500 shrink-0 font-mono">
          {isDir ? (
            <span>
              {item.children?.length || 0} items • {item.lines.toLocaleString()} L
            </span>
          ) : (
            <div className="flex items-center gap-2">
              {item.lines > 0 && (
                <span className="text-slate-400 font-semibold">{item.lines} L</span>
              )}
              <span>{formatBytes(item.size)}</span>
            </div>
          )}
        </div>
      </div>

      {isDir && isExpanded && item.children && (
        <div className="space-y-0.5">
          {item.children.map((child) => (
            <TreeNode
              key={child.path}
              item={child}
              search={search}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FileTreeExplorer: React.FC<FileTreeExplorerProps> = ({ data }) => {
  const [search, setSearch] = useState('');

  // Collect all directory paths for expand all / collapse all
  const allDirPaths = useMemo(() => {
    const paths = new Set<string>();
    const collect = (items: StructureItem[]) => {
      for (const item of items) {
        if (item.type === 'directory') {
          paths.add(item.path);
          if (item.children) collect(item.children);
        }
      }
    };
    collect(data.structure);
    return paths;
  }, [data.structure]);

  // Expand first level directories by default
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const item of data.structure) {
      if (item.type === 'directory') {
        initial.add(item.path);
      }
    }
    return initial;
  });

  const toggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const handleExpandAll = () => setExpandedDirs(new Set(allDirPaths));
  const handleCollapseAll = () => setExpandedDirs(new Set());

  return (
    <div className="space-y-4">
      {/* Top Overview Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5 text-slate-300">
            <Code2 className="w-4 h-4 text-indigo-400" />
            <span>
              <strong className="text-white font-bold">{data.total_files}</strong> Files
            </span>
          </div>
          <span className="text-slate-700">•</span>
          <div className="flex items-center gap-1.5 text-slate-300">
            <Folder className="w-4 h-4 text-cyan-400" />
            <span>
              <strong className="text-white font-bold">{data.total_directories}</strong> Folders
            </span>
          </div>
          <span className="text-slate-700">•</span>
          <div className="flex items-center gap-1.5 text-slate-300">
            <HardDrive className="w-4 h-4 text-violet-400" />
            <span>
              <strong className="text-white font-bold">{formatBytes(data.total_size_bytes)}</strong>
            </span>
          </div>
          <span className="text-slate-700">•</span>
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="text-emerald-400 font-bold font-mono">
              {data.total_lines.toLocaleString()}
            </span>{' '}
            Lines of Code
          </div>
        </div>
      </div>

      {/* Search & Actions Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter files, folders, or languages..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleExpandAll}
            title="Expand All Folders"
            className="flex items-center gap-1 px-2.5 py-1.5 text-[11px] rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
          >
            <ChevronsUpDown className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Expand All</span>
          </button>
          <button
            onClick={handleCollapseAll}
            title="Collapse All Folders"
            className="flex items-center gap-1 px-2.5 py-1.5 text-[11px] rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
          >
            <ChevronsDownUp className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Collapse All</span>
          </button>
        </div>
      </div>

      {/* Tree Content Canvas */}
      <div className="p-3 rounded-xl bg-[#0F172A]/70 border border-slate-800 max-h-[500px] overflow-y-auto space-y-0.5">
        {data.structure.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No files found in the repository.
          </div>
        ) : (
          data.structure.map((item) => (
            <TreeNode
              key={item.path}
              item={item}
              search={search}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
              depth={0}
            />
          ))
        )}
      </div>
    </div>
  );
};
