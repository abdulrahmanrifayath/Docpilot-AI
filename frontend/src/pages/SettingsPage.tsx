import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Key, Cpu, Globe, Check, AlertCircle, Sparkles, Shield } from 'lucide-react';
import { ProviderSettings } from '../types';
import { fetchSettings, updateSettings } from '../api/client';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [provider, setProvider] = useState<string>('openai');
  const [apiKey, setApiKey] = useState<string>('');
  const [model, setModel] = useState<string>('gpt-4o-mini');
  const [baseUrl, setBaseUrl] = useState<string>('https://api.openai.com/v1');
  const [githubToken, setGithubToken] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await fetchSettings();
      setSettings(data);
      setProvider(data.llm_provider);
      setModel(data.llm_model);
      if (data.llm_base_url) setBaseUrl(data.llm_base_url);
    } catch (err) {
      console.error(err);
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
        llm_base_url: baseUrl,
        github_token: githubToken || undefined,
      });
      setSettings(updated);
      setSuccessMsg('Settings updated successfully!');
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
          <SettingsIcon className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI & Integration Settings</h1>
          <p className="text-xs text-slate-400 mt-0.5">Configure LLM providers, embedding endpoints, and Git credentials</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Settings Form */}
        <div className="md:col-span-2 space-y-6">
          <form onSubmit={handleSave} className="p-6 rounded-2xl bg-[#111827]/80 border border-slate-800 backdrop-blur-md space-y-5">
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
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="openai">OpenAI (GPT-4o, GPT-4o-mini)</option>
                <option value="gemini">Google Gemini (OpenAI-compatible / Proxy)</option>
                <option value="anthropic">Anthropic (via OpenRouter or OpenAI bridge)</option>
                <option value="ollama">Ollama (Local Offline LLM)</option>
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
                placeholder={settings?.is_configured ? '•••••••••••••••• (API key configured)' : 'sk-...'}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Keys are stored only in environment memory and never hardcoded or transmitted elsewhere.
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
                placeholder="gpt-4o-mini, llama3, etc."
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500 font-mono"
              />
            </div>

            {/* Base URL */}
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-brand-400" />
                <span>API Base URL</span>
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
            <div className="pt-3 border-t border-slate-800">
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
              <p className="text-[11px] text-slate-500 mt-1">
                Required only for cloning private GitHub repositories.
              </p>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-500/20 transition-all flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              <span>{saving ? 'Saving Changes...' : 'Save Configuration'}</span>
            </button>
          </form>
        </div>

        {/* Sidebar Info Card */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 to-[#111827] border border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Provider Status</h3>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-2.5 h-2.5 rounded-full ${settings?.is_configured ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="text-sm font-semibold text-white">
                {settings?.is_configured ? 'LLM Provider Configured' : 'Offline Intelligence Mode'}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              DocPilot AI features deterministic static code analysis, AST parsing, dependency graph creation, and Mermaid diagram synthesis which operate completely offline without requiring any LLM API key!
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 space-y-2">
            <p className="font-semibold text-slate-300">Supported Providers:</p>
            <ul className="list-disc list-inside space-y-1 text-[11px]">
              <li>OpenAI (gpt-4o, gpt-4o-mini)</li>
              <li>Google Gemini API</li>
              <li>Anthropic Claude</li>
              <li>Ollama (Local host)</li>
              <li>Localhost vLLM / LM Studio</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
