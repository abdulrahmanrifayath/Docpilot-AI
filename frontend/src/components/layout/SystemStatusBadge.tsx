import React, { useState } from 'react';
import { useSystem } from '../../context/SystemContext';
import { Activity, Database, Cpu, HardDrive, RefreshCw, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';

export const SystemStatusBadge: React.FC = () => {
  const { status, isLoading, refreshStatus, error } = useSystem();
  const [isOpen, setIsOpen] = useState(false);

  const getStatusColor = () => {
    if (error || !status) return 'bg-rose-500 text-rose-400 border-rose-500/30';
    if (status.status === 'healthy') return 'bg-emerald-500 text-emerald-400 border-emerald-500/30';
    if (status.status === 'degraded') return 'bg-amber-500 text-amber-400 border-amber-500/30';
    return 'bg-rose-500 text-rose-400 border-rose-500/30';
  };

  const getStatusDot = () => {
    if (error || !status) return 'bg-rose-400 animate-pulse';
    if (status.status === 'healthy') return 'bg-emerald-400';
    if (status.status === 'degraded') return 'bg-amber-400 animate-pulse';
    return 'bg-rose-400 animate-pulse';
  };

  const getStatusText = () => {
    if (error || !status) return 'Offline';
    if (status.status === 'healthy') return 'System Operational';
    if (status.status === 'degraded') return 'Degraded (AI key required)';
    return 'Unhealthy';
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-900/80 border transition-all hover:bg-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-600 ${getStatusColor()}`}
        title="View detailed system health and connection statuses"
      >
        <span className={`w-2 h-2 rounded-full ${getStatusDot()}`} />
        <span className="font-mono">{getStatusText()}</span>
        <Activity className="w-3.5 h-3.5 opacity-70 ml-0.5" />
      </button>

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="System Status & Services" maxWidth="lg">
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <div>
              <div className="text-xs text-slate-400">Overall System Health</div>
              <div className="text-sm font-semibold capitalize text-white flex items-center gap-2 mt-0.5">
                {status?.status === 'healthy' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                {status?.status === 'degraded' && <AlertTriangle className="w-4 h-4 text-amber-400" />}
                {(status?.status === 'unhealthy' || error) && <XCircle className="w-4 h-4 text-rose-400" />}
                <span>{status ? `${status.status.toUpperCase()} (${status.environment})` : 'BACKEND OFFLINE'}</span>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              isLoading={isLoading}
              onClick={refreshStatus}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Database Card */}
            <div className="p-3.5 rounded-lg bg-[#0F172A] border border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                  <Database className="w-4 h-4 text-indigo-400" />
                  <span>Database</span>
                </div>
                <span className={`text-[11px] px-1.5 py-0.5 rounded font-mono ${
                  status?.database.status === 'connected' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                }`}>
                  {status?.database.status || 'offline'}
                </span>
              </div>
              <div className="text-xs text-slate-400">Engine: <span className="font-mono text-slate-200 uppercase">{status?.database.engine || 'N/A'}</span></div>
              <div className="text-[11px] text-slate-500 mt-1 truncate">{status?.database.message || 'Connecting...'}</div>
            </div>

            {/* AI Provider Card */}
            <div className="p-3.5 rounded-lg bg-[#0F172A] border border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <span>AI Engine</span>
                </div>
                <span className={`text-[11px] px-1.5 py-0.5 rounded font-mono ${
                  status?.ai_provider.configured ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                }`}>
                  {status?.ai_provider.configured ? 'Ready' : 'Unconfigured'}
                </span>
              </div>
              <div className="text-xs text-slate-400">Model: <span className="font-mono text-slate-200">{status?.ai_provider.model || 'N/A'}</span></div>
              <div className="text-[11px] text-slate-500 mt-1 truncate">{status?.ai_provider.message || 'Check OPENAI_API_KEY in .env'}</div>
            </div>

            {/* Vector DB Card */}
            <div className="p-3.5 rounded-lg bg-[#0F172A] border border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                  <HardDrive className="w-4 h-4 text-violet-400" />
                  <span>Vector DB</span>
                </div>
                <span className={`text-[11px] px-1.5 py-0.5 rounded font-mono ${
                  status?.vector_db.status === 'ready' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                }`}>
                  {status?.vector_db.status || 'uninitialized'}
                </span>
              </div>
              <div className="text-xs text-slate-400">Provider: <span className="font-mono text-slate-200 uppercase">{status?.vector_db.provider || 'ChromaDB'}</span></div>
              <div className="text-[11px] text-slate-500 mt-1 truncate">{status?.vector_db.message || 'Ready'}</div>
            </div>
          </div>

          <div className="text-xs text-slate-500 border-t border-slate-800 pt-3 flex justify-between items-center">
            <span>DocPilot AI Core v{status?.version || '1.0.0'}</span>
            <span>{status?.timestamp ? new Date(status.timestamp).toLocaleTimeString() : 'N/A'}</span>
          </div>
        </div>
      </Modal>
    </>
  );
};
