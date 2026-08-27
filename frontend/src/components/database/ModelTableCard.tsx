import React, { useState } from 'react';
import { DatabaseModel, DatabaseField, DatabaseRelationship } from '../../types';
import { Card } from '../common/Card';
import {
  Table2,
  Key,
  Link2,
  ChevronDown,
  ChevronUp,
  FileCode,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface ModelTableCardProps {
  model: DatabaseModel;
}

const getTypeColor = (type: string) => {
  const t = type.toUpperCase();
  if (t.includes('INT')) return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
  if (t.includes('VARCHAR') || t.includes('STR') || t.includes('TEXT'))
    return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
  if (t.includes('BOOL')) return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
  if (t.includes('TIME') || t.includes('DATE')) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  if (t.includes('JSON') || t.includes('DICT')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  if (t.includes('FLOAT') || t.includes('NUM') || t.includes('DEC'))
    return 'text-teal-400 bg-teal-500/10 border-teal-500/30';
  return 'text-slate-300 bg-slate-800 border-slate-700';
};

const getRelBadgeColor = (relType: string) => {
  switch (relType) {
    case 'ONE_TO_ONE':
      return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
    case 'MANY_TO_MANY':
      return 'bg-pink-500/20 text-pink-300 border-pink-500/40';
    case 'FOREIGN_KEY':
      return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    case 'ONE_TO_MANY':
    default:
      return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
  }
};

export const ModelTableCard: React.FC<ModelTableCardProps> = ({ model }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const pkCount = model.fields.filter((f) => f.primary_key).length;
  const fkCount = model.fields.filter((f) => f.foreign_key).length;

  return (
    <Card className="overflow-hidden border border-slate-800 bg-slate-900/90 hover:border-slate-700 transition-all">
      {/* Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-4 cursor-pointer flex items-center justify-between gap-4 select-none hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Table2 className="w-5 h-5" />
          </div>

          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h4 className="text-sm font-bold text-white font-mono">{model.table_name}</h4>
              <span className="text-xs px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 font-mono">
                class {model.model_name}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-lg bg-cyan-950/60 border border-cyan-800 text-cyan-300 font-mono">
                {model.orm_framework}
              </span>
            </div>

            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1 text-[11px]">
                <FileCode className="w-3.5 h-3.5 text-slate-500" />
                {model.file_path}
                {model.line_number && `:${model.line_number}`}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <span className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-slate-300">
              {model.fields.length} columns
            </span>
            {pkCount > 0 && (
              <span className="px-2 py-0.5 rounded-md bg-emerald-950/60 border border-emerald-800 text-emerald-300 flex items-center gap-1">
                <Key className="w-3 h-3" />
                {pkCount} PK
              </span>
            )}
            {fkCount > 0 && (
              <span className="px-2 py-0.5 rounded-md bg-amber-950/60 border border-amber-800 text-amber-300 flex items-center gap-1">
                <Link2 className="w-3 h-3" />
                {fkCount} FK
              </span>
            )}
            {model.relationships.length > 0 && (
              <span className="px-2 py-0.5 rounded-md bg-indigo-950/60 border border-indigo-800 text-indigo-300 flex items-center gap-1">
                <Layers className="w-3 h-3" />
                {model.relationships.length} Rel
              </span>
            )}
          </div>

          <button className="text-slate-400 hover:text-white p-1">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Table Schema Body */}
      {isExpanded && (
        <div className="border-t border-slate-800/80 bg-slate-950/50 p-4 space-y-4">
          {model.docstring && (
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 italic">
              {model.docstring}
            </div>
          )}

          {/* Columns Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                  <th className="py-2 px-3">Column Name</th>
                  <th className="py-2 px-3">Data Type</th>
                  <th className="py-2 px-3">Constraints / Keys</th>
                  <th className="py-2 px-3">Nullable</th>
                  <th className="py-2 px-3">Default</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {model.fields.map((field: DatabaseField) => (
                  <tr key={field.name} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2 px-3 font-semibold text-white flex items-center gap-1.5">
                      {field.primary_key && <Key className="w-3 h-3 text-emerald-400 shrink-0" />}
                      {field.foreign_key && <Link2 className="w-3 h-3 text-amber-400 shrink-0" />}
                      <span>{field.name}</span>
                    </td>

                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded-md border text-[11px] font-bold ${getTypeColor(field.data_type)}`}>
                        {field.data_type}
                      </span>
                    </td>

                    <td className="py-2 px-3 space-x-1.5">
                      {field.primary_key && (
                        <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold">
                          PRIMARY KEY
                        </span>
                      )}
                      {field.foreign_key && (
                        <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold">
                          FK → {field.foreign_key}
                        </span>
                      )}
                      {field.unique && (
                        <span className="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px]">
                          UNIQUE
                        </span>
                      )}
                      {field.index && (
                        <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 text-[10px]">
                          INDEX
                        </span>
                      )}
                      {!field.primary_key && !field.foreign_key && !field.unique && !field.index && (
                        <span className="text-slate-600">-</span>
                      )}
                    </td>

                    <td className="py-2 px-3">
                      {field.nullable ? (
                        <span className="text-slate-400">NULL</span>
                      ) : (
                        <span className="text-rose-400 font-semibold">NOT NULL</span>
                      )}
                    </td>

                    <td className="py-2 px-3 text-slate-400">
                      {field.default ? field.default : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Relationships List */}
          {model.relationships.length > 0 && (
            <div className="pt-3 border-t border-slate-800/80">
              <h5 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                Declared Entity Relationships ({model.relationships.length})
              </h5>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {model.relationships.map((rel: DatabaseRelationship, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-slate-200 font-semibold">{rel.name || rel.source_model}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="text-indigo-400 font-semibold">{rel.target_model}</span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className={`px-2 py-0.5 rounded-md border text-[10px] font-bold ${getRelBadgeColor(rel.relationship_type)}`}>
                        {rel.cardinality_mermaid} {rel.relationship_type.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
