import React from 'react';
import { useSystem } from '../context/SystemContext';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import {
  Settings,
  Database,
  Cpu,
  HardDrive,
  RefreshCw,
  Server,
  Key,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { status, isLoading, refreshStatus } = useSystem();

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Settings className="w-6 h-6 text-slate-400" />
            System & Provider Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Overview of database connectivity, LLM provider settings, and vector store configuration.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          isLoading={isLoading}
          onClick={refreshStatus}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Refresh Status
        </Button>
      </div>

      {/* Database Configuration Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <Database className="w-5 h-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Database Configuration</h3>
          </div>
          <Badge variant={status?.database.status === 'connected' ? 'success' : 'danger'} dot>
            {status?.database.status || 'disconnected'}
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block mb-1">Database Engine</span>
            <span className="font-mono text-white uppercase bg-slate-900 px-2.5 py-1 rounded border border-slate-800 inline-block">
              {status?.database.engine || 'SQLite'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block mb-1">Storage Mode</span>
            <span className="text-slate-200">
              {status?.database.engine === 'sqlite'
                ? 'Local Zero-Config SQLite (docpilot.db)'
                : 'PostgreSQL Server'}
            </span>
          </div>
        </div>
      </Card>

      {/* AI Provider Configuration Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">AI Provider (OpenAI Compatible)</h3>
          </div>
          <Badge variant={status?.ai_provider.configured ? 'success' : 'warning'} dot>
            {status?.ai_provider.configured ? 'Configured' : 'Missing Key'}
          </Badge>
        </div>

        <div className="space-y-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-slate-400 block mb-1">Target Chat Model</span>
              <span className="font-mono text-white bg-slate-900 px-2.5 py-1 rounded border border-slate-800 inline-block">
                {status?.ai_provider.model || 'gpt-4o-mini'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block mb-1">Embedding Model</span>
              <span className="font-mono text-white bg-slate-900 px-2.5 py-1 rounded border border-slate-800 inline-block">
                {status?.ai_provider.embedding_model || 'text-embedding-3-small'}
              </span>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
            <Key className="w-4 h-4 text-slate-500 shrink-0" />
            <span>
              API keys are safely loaded from <code className="text-indigo-300">backend/.env</code> and never exposed to the frontend client.
            </span>
          </div>
        </div>
      </Card>

      {/* Vector Store Card */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <HardDrive className="w-5 h-5 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">Vector Storage & Embeddings</h3>
          </div>
          <Badge variant={status?.vector_db.status === 'ready' ? 'success' : 'danger'} dot>
            {status?.vector_db.status || 'uninitialized'}
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block mb-1">Vector Provider</span>
            <span className="font-mono text-white uppercase bg-slate-900 px-2.5 py-1 rounded border border-slate-800 inline-block">
              {status?.vector_db.provider || 'ChromaDB'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block mb-1">Local Storage Directory</span>
            <span className="font-mono text-slate-300 bg-slate-900 px-2.5 py-1 rounded border border-slate-800 inline-block">
              {status?.vector_db.storage_path || './chroma_db'}
            </span>
          </div>
        </div>
      </Card>

      {/* Environment info */}
      <Card className="p-6 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <Server className="w-4 h-4 text-slate-400" />
          <span>Application Environment</span>
        </div>
        <div className="flex items-center gap-6 text-xs text-slate-400">
          <div>
            <span>DocPilot Core:</span>{' '}
            <span className="font-mono text-white">v{status?.version || '1.0.0'}</span>
          </div>
          <div>
            <span>Environment:</span>{' '}
            <span className="font-mono text-white uppercase">{status?.environment || 'development'}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};
