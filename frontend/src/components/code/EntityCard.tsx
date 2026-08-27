import React, { useState } from 'react';
import { CodeEntity, EntityType } from '../../types';
import {
  Code2,
  Box,
  Layers,
  Copy,
  Check,
  Cpu,
  FileCode,
  CornerDownRight,
  Braces,
} from 'lucide-react';

interface EntityCardProps {
  entity: CodeEntity;
}

const getEntityBadgeColor = (type: EntityType) => {
  switch (type) {
    case 'CLASS':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    case 'FUNCTION':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    case 'METHOD':
      return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    case 'INTERFACE':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
    case 'COMPONENT':
      return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
    case 'MODULE':
    default:
      return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
  }
};

const getEntityIcon = (type: EntityType) => {
  switch (type) {
    case 'CLASS':
      return <Box className="w-3.5 h-3.5" />;
    case 'FUNCTION':
      return <Code2 className="w-3.5 h-3.5" />;
    case 'METHOD':
      return <Braces className="w-3.5 h-3.5" />;
    case 'INTERFACE':
      return <Layers className="w-3.5 h-3.5" />;
    case 'COMPONENT':
      return <Cpu className="w-3.5 h-3.5" />;
    case 'MODULE':
    default:
      return <FileCode className="w-3.5 h-3.5" />;
  }
};

export const EntityCard: React.FC<EntityCardProps> = ({ entity }) => {
  const [copied, setCopied] = useState(false);

  const handleCopySignature = () => {
    if (entity.signature) {
      navigator.clipboard.writeText(entity.signature);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const params = entity.metadata_json?.parameters || [];
  const decorators = entity.metadata_json?.decorators || [];
  const bases = entity.metadata_json?.bases || [];
  const isAsync = entity.metadata_json?.is_async || false;
  const returnType = entity.metadata_json?.return_type;

  return (
    <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-all space-y-3">
      {/* Top Meta: Type badge, Name, Line Range */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border uppercase ${getEntityBadgeColor(
              entity.entity_type
            )}`}
          >
            {getEntityIcon(entity.entity_type)}
            {entity.entity_type}
          </span>

          <span className="text-sm font-bold text-white font-mono truncate">{entity.name}</span>

          {isAsync && (
            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
              async
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            Lines {entity.start_line} – {entity.end_line}
          </span>
        </div>
      </div>

      {/* Parent Class Linkage if Method */}
      {entity.parent_entity && (
        <div className="flex items-center gap-1.5 text-xs text-indigo-400 font-mono">
          <CornerDownRight className="w-3.5 h-3.5 text-indigo-500" />
          <span>Member of class <strong className="text-white">{entity.parent_entity}</strong></span>
        </div>
      )}

      {/* Decorators */}
      {decorators.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {decorators.map((dec: string, i: number) => (
            <span
              key={i}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/40"
            >
              @{dec.replace(/^@/, '')}
            </span>
          ))}
        </div>
      )}

      {/* Class Inheritance Bases */}
      {bases.length > 0 && (
        <div className="text-xs text-slate-400 font-mono flex items-center gap-1.5">
          <span className="text-slate-500">Inherits from:</span>
          {bases.map((b: string, i: number) => (
            <span
              key={i}
              className="text-[11px] px-2 py-0.5 rounded bg-slate-900 text-slate-200 border border-slate-800"
            >
              {b}
            </span>
          ))}
        </div>
      )}

      {/* Code Signature Box */}
      {entity.signature && (
        <div className="relative group">
          <pre className="p-3 rounded-lg bg-slate-900/90 border border-slate-800/90 text-xs font-mono text-indigo-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            <code>{entity.signature}</code>
          </pre>
          <button
            onClick={handleCopySignature}
            title="Copy Signature"
            className="absolute top-2 right-2 p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          </button>
        </div>
      )}

      {/* Parameters & Return Type Breakdown */}
      {(params.length > 0 || returnType) && (
        <div className="pt-2 border-t border-slate-850 flex flex-wrap items-center gap-2 text-xs">
          {params.length > 0 && (
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-[10px] text-slate-500 font-mono uppercase">Params:</span>
              {params.map((p: any, i: number) => (
                <span
                  key={i}
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300"
                >
                  <strong className="text-white">{p.name}</strong>
                  {p.type && <span className="text-indigo-400">: {p.type}</span>}
                  {p.default && <span className="text-slate-500"> = {p.default}</span>}
                </span>
              ))}
            </div>
          )}

          {returnType && (
            <div className="flex items-center gap-1 ml-auto">
              <span className="text-[10px] text-slate-500 font-mono uppercase">Returns:</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-400 font-semibold">
                {returnType}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Docstring */}
      {entity.docstring && (
        <div className="p-2.5 rounded-lg bg-slate-900/50 border-l-2 border-indigo-500 text-xs text-slate-300 italic leading-relaxed">
          {entity.docstring}
        </div>
      )}
    </div>
  );
};
