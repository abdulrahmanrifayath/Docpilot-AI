import React, { useState, useEffect, useMemo } from 'react';
import { projectsApi } from '../../api/projects';
import {
  CodeEntity,
  ProjectEntitiesResponse,
  ParseResponse,
} from '../../types';
import { EntityCard } from './EntityCard';
import { Button } from '../common/Button';
import {
  Code2,
  Search,
  RefreshCw,
  FileCode,
  CheckCircle2,
} from 'lucide-react';

interface CodeEntityInspectorProps {
  projectId: string;
}

export const CodeEntityInspector: React.FC<CodeEntityInspectorProps> = ({ projectId }) => {
  const [entitiesData, setEntitiesData] = useState<ProjectEntitiesResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [searchFile, setSearchFile] = useState<string>('');
  const [searchEntity, setSearchEntity] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isParsing, setIsParsing] = useState<boolean>(false);
  const [parseResult, setParseResult] = useState<ParseResponse | null>(null);

  const fetchEntities = async () => {
    try {
      setIsLoading(true);
      const res = await projectsApi.getEntities(projectId);
      setEntitiesData(res);

      // Select first file if none selected
      if (!selectedFile && res.entities.length > 0) {
        setSelectedFile(res.entities[0].file_path);
      }
    } catch (err) {
      console.error('Failed to fetch project code entities:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEntities();
  }, [projectId]);

  const handleRunParser = async () => {
    try {
      setIsParsing(true);
      const res = await projectsApi.parseCode(projectId);
      setParseResult(res);
      await fetchEntities();
    } catch (err) {
      console.error('Failed to parse codebase:', err);
    } finally {
      setIsParsing(false);
    }
  };

  // Group entities by file
  const filesMap = useMemo(() => {
    if (!entitiesData) return new Map<string, CodeEntity[]>();
    const map = new Map<string, CodeEntity[]>();
    for (const ent of entitiesData.entities) {
      if (!map.has(ent.file_path)) {
        map.set(ent.file_path, []);
      }
      map.get(ent.file_path)!.push(ent);
    }
    return map;
  }, [entitiesData]);

  // Unique files list filtered by search
  const filteredFiles = useMemo(() => {
    const fileList = Array.from(filesMap.keys());
    if (!searchFile.trim()) return fileList;
    return fileList.filter((f) => f.toLowerCase().includes(searchFile.toLowerCase()));
  }, [filesMap, searchFile]);

  // Entities for currently selected file
  const selectedFileEntities = useMemo(() => {
    if (!selectedFile || !filesMap.has(selectedFile)) return [];
    let list = filesMap.get(selectedFile)!;

    if (typeFilter !== 'ALL') {
      list = list.filter((e) => e.entity_type === typeFilter);
    }

    if (searchEntity.trim()) {
      const q = searchEntity.toLowerCase();
      list = list.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          (e.signature && e.signature.toLowerCase().includes(q)) ||
          (e.docstring && e.docstring.toLowerCase().includes(q))
      );
    }

    return list;
  }, [selectedFile, filesMap, typeFilter, searchEntity]);

  const counts = entitiesData?.entity_counts || {};

  return (
    <div className="space-y-5">
      {/* Top Header Overview Bar */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Code2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight uppercase">
                Static Code Parsing Engine
              </h3>
              <p className="text-xs text-slate-400">
                Extracted classes, functions, methods, interfaces, and UI components
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-mono">
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
              <strong className="text-white">{entitiesData?.total_entities || 0}</strong> Entities
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-emerald-300">
              <strong className="text-emerald-400">{counts['CLASS'] || 0}</strong> Classes
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-blue-300">
              <strong className="text-blue-400">{(counts['FUNCTION'] || 0) + (counts['METHOD'] || 0)}</strong> Functions/Methods
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-purple-300">
              <strong className="text-purple-400">{counts['INTERFACE'] || 0}</strong> Interfaces
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300">
              <strong className="text-cyan-400">{counts['COMPONENT'] || 0}</strong> Components
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {parseResult && (
            <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Parsed in {parseResult.duration_ms}ms
            </div>
          )}

          <Button
            variant="primary"
            size="sm"
            isLoading={isParsing}
            onClick={handleRunParser}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isParsing ? 'animate-spin' : ''}`} />}
          >
            {entitiesData && entitiesData.total_entities > 0 ? 'Re-parse Codebase' : 'Parse Codebase'}
          </Button>
        </div>
      </div>

      {/* Main Split Inspector View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[550px]">
        {/* Left Column: Source File Browser */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white uppercase tracking-tight flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
              Source Files ({filteredFiles.length})
            </h4>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchFile}
              onChange={(e) => setSearchFile(e.target.value)}
              placeholder="Search source files..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-1 max-h-[460px] pr-1">
            {isLoading ? (
              <div className="py-8 text-center text-xs text-slate-500">Loading entities...</div>
            ) : filteredFiles.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                No parsed source files match search.
              </div>
            ) : (
              filteredFiles.map((fPath) => {
                const count = filesMap.get(fPath)?.length || 0;
                const isSelected = selectedFile === fPath;
                return (
                  <button
                    key={fPath}
                    onClick={() => setSelectedFile(fPath)}
                    className={`w-full text-left p-2.5 rounded-xl text-xs font-mono transition-all flex items-center justify-between gap-2 ${
                      isSelected
                        ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                        : 'bg-slate-950/40 text-slate-400 hover:bg-slate-800/60 hover:text-white border border-transparent'
                    }`}
                  >
                    <span className="truncate">{fPath}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-md font-mono shrink-0 ${
                        isSelected ? 'bg-indigo-500 text-white' : 'bg-slate-900 text-slate-500 border border-slate-800'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Code Entity Cards */}
        <div className="lg:col-span-8 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col space-y-4">
          {/* Header for Selected File */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div>
              <div className="text-[11px] text-slate-500 font-mono uppercase">Inspecting File</div>
              <h3 className="text-sm font-bold text-white font-mono truncate max-w-md">
                {selectedFile || 'Select a file to inspect'}
              </h3>
            </div>

            <div className="relative sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchEntity}
                onChange={(e) => setSearchEntity(e.target.value)}
                placeholder="Filter entities in file..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            {['ALL', 'CLASS', 'FUNCTION', 'METHOD', 'INTERFACE', 'COMPONENT'].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`text-[11px] font-mono px-2.5 py-1 rounded-lg border transition-colors ${
                  typeFilter === t
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 font-bold'
                    : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:text-white hover:bg-slate-800'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Entity List */}
          <div className="flex-1 overflow-y-auto space-y-3 max-h-[460px] pr-1">
            {selectedFileEntities.length === 0 ? (
              <div className="py-16 text-center text-xs text-slate-500">
                No {typeFilter !== 'ALL' ? typeFilter.toLowerCase() : ''} entities found in this file.
              </div>
            ) : (
              selectedFileEntities.map((ent) => <EntityCard key={ent.id} entity={ent} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
