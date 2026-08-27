import React, { useState } from 'react';
import { ApiEndpoint } from '../../types';
import {
  Lock,
  Unlock,
  FileCode,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Tag,
  Shield,
} from 'lucide-react';

interface ApiEndpointCardProps {
  endpoint: ApiEndpoint;
}

const getMethodStyle = (method: string) => {
  switch (method.toUpperCase()) {
    case 'GET':
      return {
        badge: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30 font-bold',
        text: 'text-cyan-400',
        glow: 'border-l-cyan-500',
      };
    case 'POST':
      return {
        badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-bold',
        text: 'text-emerald-400',
        glow: 'border-l-emerald-500',
      };
    case 'PUT':
      return {
        badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30 font-bold',
        text: 'text-amber-400',
        glow: 'border-l-amber-500',
      };
    case 'DELETE':
      return {
        badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30 font-bold',
        text: 'text-rose-400',
        glow: 'border-l-rose-500',
      };
    case 'PATCH':
      return {
        badge: 'bg-purple-500/15 text-purple-400 border-purple-500/30 font-bold',
        text: 'text-purple-400',
        glow: 'border-l-purple-500',
      };
    default:
      return {
        badge: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30 font-bold',
        text: 'text-indigo-400',
        glow: 'border-l-indigo-500',
      };
  }
};

export const ApiEndpointCard: React.FC<ApiEndpointCardProps> = ({ endpoint }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const methodStyle = getMethodStyle(endpoint.method);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(`${endpoint.method} ${endpoint.path}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const params = endpoint.request_schema?.parameters || [];
  const bodyModel = endpoint.request_schema?.body_model;
  const responseModel = endpoint.response_schema?.response_model || endpoint.response_schema?.return_type;
  const statusCode = endpoint.response_schema?.status_code || 200;

  return (
    <div
      className={`rounded-2xl bg-slate-900/80 border border-slate-800/90 border-l-4 ${methodStyle.glow} hover:border-slate-700 transition-all duration-200 overflow-hidden shadow-lg`}
    >
      {/* Header Row */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer select-none hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className={`px-2.5 py-1 rounded-lg border text-xs font-mono tracking-wider uppercase ${methodStyle.badge}`}
          >
            {endpoint.method}
          </span>

          <span className="text-sm md:text-base font-bold font-mono text-white tracking-tight">
            {endpoint.path}
          </span>

          {endpoint.authentication_required ? (
            <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold">
              <Lock className="w-3 h-3 text-amber-400" />
              Auth Required
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              <Unlock className="w-3 h-3 text-slate-500" />
              Public
            </span>
          )}

          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            {endpoint.framework}
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-1.5 font-mono text-slate-300">
            <span className="text-slate-500">handler:</span>
            <span className="text-white font-semibold">{endpoint.handler_name}</span>
          </div>

          <button
            onClick={handleCopy}
            title="Copy method and path"
            className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button className="p-1 text-slate-400 hover:text-white transition-colors">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Details Body */}
      {isExpanded && (
        <div className="p-5 pt-2 border-t border-slate-800/80 bg-slate-950/40 space-y-4">
          {/* File location & Summary */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-slate-400">
              <FileCode className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {endpoint.file_path}
                {endpoint.line_number && <span className="text-indigo-400">:{endpoint.line_number}</span>}
              </span>
            </div>

            {endpoint.tags.length > 0 && (
              <div className="flex items-center gap-1.5">
                <Tag className="w-3 h-3 text-slate-500" />
                {endpoint.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.2 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* AI Purpose Placeholder Banner */}
          <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/20 flex items-start gap-2.5 text-xs text-indigo-200">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-indigo-300">
                {endpoint.summary || endpoint.docstring || `${endpoint.method} ${endpoint.path}`}
              </div>
              <p className="text-[11px] text-indigo-400/80 mt-0.5">
                Static analysis detected. High-level business purpose and semantic documentation will be generated by AI in Phase 7.
              </p>
            </div>
          </div>

          {/* Parameters & Request Schema */}
          <div className="space-y-2">
            <div className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
              <span>Request Parameters & Body ({params.length + (bodyModel ? 1 : 0)})</span>
              {bodyModel && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">
                  Body: {bodyModel}
                </span>
              )}
            </div>

            {params.length === 0 && !bodyModel ? (
              <div className="text-xs text-slate-500 italic p-3 rounded-lg bg-slate-900/40 border border-slate-800">
                No parameters required for this endpoint.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                    <tr>
                      <th className="py-2 px-3">Parameter</th>
                      <th className="py-2 px-3">In</th>
                      <th className="py-2 px-3">Type</th>
                      <th className="py-2 px-3">Required</th>
                      <th className="py-2 px-3">Default / Injection</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {params.map((p) => (
                      <tr key={p.name} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2 px-3 font-semibold text-white">{p.name}</td>
                        <td className="py-2 px-3">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] uppercase ${
                              p.in_location === 'path'
                                ? 'bg-cyan-500/20 text-cyan-300'
                                : p.in_location === 'dependency'
                                ? 'bg-amber-500/20 text-amber-300'
                                : p.in_location === 'body'
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {p.in_location}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-indigo-300 truncate max-w-[150px]">
                          {p.type || 'any'}
                        </td>
                        <td className="py-2 px-3">
                          {p.required ? (
                            <span className="text-rose-400 font-bold">Yes</span>
                          ) : (
                            <span className="text-slate-500">No</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-slate-400 truncate max-w-[200px]">
                          {p.default || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Response Schema & Status */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono border-t border-slate-800/80">
            <div className="flex items-center gap-2">
              <span className="text-slate-500 uppercase text-[10px]">Expected Response:</span>
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/40 font-bold">
                {statusCode} OK
              </span>
              {responseModel && (
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
                  Model: <strong className="text-indigo-400">{responseModel}</strong>
                </span>
              )}
            </div>

            <div className="text-[11px] text-slate-500 flex items-center gap-1">
              <Shield className="w-3 h-3 text-emerald-400" />
              <span>Static route mapping verified</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
