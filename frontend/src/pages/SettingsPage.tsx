import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon,
  Key,
  Cpu,
  Globe,
  Check,
  AlertCircle,
  Sparkles,
  Shield,
  Database,
  Layers,
  Activity,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { ProviderSettings } from '../types';
import { fetchSettings, updateSettings } from '../api/client';
import { useProjects } from '../context/ProjectContext';

export const SettingsPage: React.FC = () => {
  const { systemStatus, refreshStatus } = useProjects();
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [provider, setProvider] = useState<string>('gemini');
  const [apiKey, setApiKey] = useState<string>('');
  const [model, setModel] = useState<string>('gemini-2.5-pro');
  const [baseUrl, setBaseUrl] = useState<string>('');
  const [githubToken, setGithubToken] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
    refreshStatus();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setSettings(data);
      if (data.llm_provider) setProvider(data.llm_provider);
      if (data.llm_model) setModel(data.llm_model);
      if (data.llm_base_url) setBaseUrl(data.llm_base_url);
    } catch (err) {
      console.warn('Could not load provider settings', err);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    try {
      const updated = await updateSettings({
        llm_provider: provider,
        llm_api_key: apiKey || undefined,
        llm_model: model,
        llm_base_url: baseUrl || undefined,
        github_token: githubToken || undefined,
      });
      setSettings(updated);
      setApiKey('');
      setGithubToken('');
      setSuccessMsg('Settings updated successfully!');
      refreshStatus();
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const isOperational = systemStatus?.status === 'operational';

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3 pb-2 border-b border-slate-800">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
          <SettingsIcon className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Settings & Status</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time infrastructure health, AI provider configuration, and safe sandboxing controls
          </p>
        </div>
      </div>

      {/* System Status Breakdown Cards */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-brand-400" />
          <span>System Status Summary (GET /api/v1/system/status)</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Application */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-slate-400 font-semibold">Application</span>
              <span
                className={`w-2.5 h-2.5 rounded-full ${isOperational ? 'bg-emerald-400' : 'bg-amber-400'}`}
              />
            </div>
            <p className="text-sm font-bold text-white">{systemStatus?.application?.name || 'DocPilot AI API'}</p>
            <div className="mt-2 text-[11px] text-slate-400 space-y-1">
              <p>Status: <span className="text-emerald-400 font-semibold">{systemStatus?.application?.status || 'operational'}</span></p>
              <p>Version: <span className="font-mono text-slate-300">{systemStatus?.application?.version || '1.0.0'}</span></p>
              <p>Env: <span className="capitalize">{systemStatus?.application?.environment || 'Development'}</span></p>
            </div>
          </div>

          {/* Database */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-slate-400 font-semibold">Database</span>
              <Database className="w-4 h-4 text-brand-400" />
            </div>
            <p className="text-sm font-bold text-white capitalize">{systemStatus?.database?.type || 'SQLite (Local)'}</p>
            <div className="mt-2 text-[11px] text-slate-400 space-y-1">
              <p>Status: <span className="text-emerald-400 font-semibold">{systemStatus?.database?.status || 'connected'}</span></p>
              <p>Driver: <span className="font-mono text-slate-300">SQLAlchemy Async</span></p>
              <p>Dialect: <span className="text-slate-300">SQLite / PostgreSQL</span></p>
            </div>
          </div>

          {/* AI Provider */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-slate-400 font-semibold">AI Provider</span>
              <Cpu className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-sm font-bold text-white capitalize">{systemStatus?.ai_provider?.provider || 'Gemini'}</p>
            <div className="mt-2 text-[11px] text-slate-400 space-y-1">
              <p>Model: <span className="font-mono text-brand-300 text-[10px]">{systemStatus?.ai_provider?.model || 'gemini-2.5-pro'}</span></p>
              <p>
                Configured:{' '}
                <span className={systemStatus?.ai_provider?.is_configured ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
                  {systemStatus?.ai_provider?.is_configured ? 'Yes (Active)' : 'No (Offline Mode)'}
                </span>
              </p>
              <p>Secrets: <span className="text-emerald-400">Masked (Zero Secret Leak)</span></p>
            </div>
          </div>

          {/* Vector Database */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-slate-400 font-semibold">Vector Storage</span>
              <Layers className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-sm font-bold text-white capitalize">{systemStatus?.vector_database?.type || 'ChromaDB'}</p>
            <div className="mt-2 text-[11px] text-slate-400 space-y-1">
              <p>Status: <span className="text-emerald-400 font-semibold">{systemStatus?.vector_database?.status || 'ready'}</span></p>
              <p>Storage: <span className="text-slate-300">Local Vector Index</span></p>
              <p>RAG Readiness: <span className="text-cyan-400">Phase 5</span></p>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration & Security Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Settings Form */}
        <div className="md:col-span-2 space-y-6">
          <form onSubmit={handleSave} className="p-6 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">AI Provider Configuration</h3>
              <span className="text-[10px] font-semibold text-emerald-400 flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>Zero Secrets Exposed</span>
              </span>
            </div>

            {successMsg && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Provider Selection */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-brand-400" />
                <span>LLM Provider</span>
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 cursor-pointer"
              >
                <option value="gemini">Google Gemini (Recommended)</option>
                <option value="openai">OpenAI (GPT-4o, GPT-4o-mini)</option>
                <option value="anthropic">Anthropic Claude</option>
                <option value="ollama">Ollama (Offline Local LLM)</option>
                <option value="custom">Custom OpenAI-Compatible Endpoint</option>
              </select>
            </div>

            {/* API Key */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Key className="w-3.5 h-3.5 text-brand-400" />
                <span>API Key</span>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={settings?.is_configured ? '•••••••••••••••• (Configured securely in environment)' : 'Enter API Key...'}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
              <p className="text-[10px] text-slate-500 mt-1">
                Secrets are stored strictly in environment memory and never exposed through status endpoints.
              </p>
            </div>

            {/* Model Name */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-brand-400" />
                <span>Model Identifier</span>
              </label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="gemini-2.5-pro, gpt-4o-mini, etc."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
              />
            </div>

            {/* Base URL */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-brand-400" />
                <span>Custom Endpoint URL (Optional)</span>
              </label>
              <input
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
              />
            </div>

            {/* GitHub Token */}
            <div className="pt-2 border-t border-slate-800">
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                <span>GitHub Personal Access Token (Optional)</span>
              </label>
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder={settings?.github_token_configured ? '•••••••• (Token configured)' : 'ghp_...'}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-500/20 transition-all flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </form>
        </div>

        {/* Security & Isolation Panel */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center gap-2 text-white font-bold text-xs">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Security & Sandboxing Principles</span>
            </div>
            <ul className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  <strong className="text-white">Zero Execution:</strong> Repository code is never executed, run, or evaluated. Only parsed statically.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  <strong className="text-white">Path Traversal Defense:</strong> All ZIP archive members are checked against directory boundary breakouts.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>
                  <strong className="text-white">Isolated Workspaces:</strong> Each project is given a dedicated directory in storage.
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
