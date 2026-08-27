import React from 'react';
import { FrameworkInfo, InfrastructureInfo } from '../../types';
import {
  Cpu,
  Server,
  Layers,
  Container,
  GitPullRequest,
  Box,
  FileKey2,
  Database,
} from 'lucide-react';

interface TechStackCardProps {
  frameworks: FrameworkInfo[];
  infrastructure: InfrastructureInfo[];
}

const getFrameworkIcon = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.includes('react') || lower.includes('next')) {
    return <Layers className="w-5 h-5 text-cyan-400" />;
  }
  if (lower.includes('fastapi') || lower.includes('flask') || lower.includes('django')) {
    return <Server className="w-5 h-5 text-emerald-400" />;
  }
  if (lower.includes('express') || lower.includes('node')) {
    return <Cpu className="w-5 h-5 text-amber-400" />;
  }
  return <Cpu className="w-5 h-5 text-indigo-400" />;
};

const getInfraIcon = (type: string) => {
  const lower = type.toLowerCase();
  if (lower.includes('container') || lower.includes('docker')) {
    return <Container className="w-5 h-5 text-blue-400" />;
  }
  if (lower.includes('workflow') || lower.includes('ci')) {
    return <GitPullRequest className="w-5 h-5 text-violet-400" />;
  }
  if (lower.includes('iac') || lower.includes('terraform')) {
    return <Box className="w-5 h-5 text-purple-400" />;
  }
  if (lower.includes('environment') || lower.includes('config')) {
    return <FileKey2 className="w-5 h-5 text-amber-400" />;
  }
  if (lower.includes('database')) {
    return <Database className="w-5 h-5 text-indigo-400" />;
  }
  return <Layers className="w-5 h-5 text-slate-400" />;
};

export const TechStackCard: React.FC<TechStackCardProps> = ({
  frameworks,
  infrastructure,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Detected Frameworks Card */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Server className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-white tracking-tight uppercase">
                  Detected Frameworks & Runtimes
                </h3>
                <span className="text-[11px] text-slate-400">
                  {frameworks.length} Framework(s) Identified
                </span>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
              Heuristic Scan
            </span>
          </div>

          {frameworks.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No standard framework dependencies or imports detected.
            </div>
          ) : (
            <div className="space-y-3">
              {frameworks.map((fw) => (
                <div
                  key={fw.name}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getFrameworkIcon(fw.name)}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">{fw.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          {fw.category}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex flex-wrap gap-1">
                        {fw.indicators.map((ind, i) => (
                          <span
                            key={i}
                            className="inline-block bg-slate-900 px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400 border border-slate-800"
                          >
                            {ind}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase border shrink-0 ${
                      fw.confidence === 'HIGH'
                        ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                    }`}
                  >
                    {fw.confidence} CONFIDENCE
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detected Infrastructure Card */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <Container className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-white tracking-tight uppercase">
                  Infrastructure & DevOps Tools
                </h3>
                <span className="text-[11px] text-slate-400">
                  {infrastructure.length} Tool(s) Configured
                </span>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
              Config Manifests
            </span>
          </div>

          {infrastructure.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No Docker, CI/CD, Kubernetes, or Terraform configurations found.
            </div>
          ) : (
            <div className="space-y-3">
              {infrastructure.map((inf) => (
                <div
                  key={inf.name}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getInfraIcon(inf.type)}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">{inf.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          {inf.type}
                        </span>
                      </div>
                      {inf.details && (
                        <div className="text-[11px] text-slate-400 mt-0.5">{inf.details}</div>
                      )}
                      <div className="flex flex-wrap gap-1 mt-1">
                        {inf.files.map((file, i) => (
                          <span
                            key={i}
                            className="bg-slate-900 px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400 border border-slate-800"
                          >
                            {file}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 uppercase shrink-0">
                    ACTIVE
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
