import {
  Repository,
  PipelineProgress,
  DocumentItem,
  DiagramItem,
  ChatMessage,
  ProviderSettings,
  SyncResult,
} from '../types';

const API_BASE = '/api';

export async function fetchRepositories(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/repositories`);
  if (!res.ok) throw new Error('Failed to fetch repositories');
  return res.json();
}

export async function fetchRepository(id: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/${id}`);
  if (!res.ok) throw new Error('Failed to fetch repository details');
  return res.json();
}

export async function uploadZip(file: File, name?: string): Promise<Repository> {
  const formData = new FormData();
  formData.append('file', file);
  if (name) formData.append('name', name);

  const res = await fetch(`${API_BASE}/repositories/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function cloneGit(sourceUrl: string, name?: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/clone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_url: sourceUrl, name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Cloning failed' }));
    throw new Error(err.detail || 'Cloning failed');
  }
  return res.json();
}

export async function deleteRepository(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/repositories/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete repository');
}

export async function fetchProgress(id: string): Promise<PipelineProgress> {
  const res = await fetch(`${API_BASE}/repositories/${id}/progress`);
  if (!res.ok) throw new Error('Failed to fetch pipeline progress');
  return res.json();
}

export async function triggerAnalysis(id: string): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/${id}/analyze`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to start analysis');
  return res.json();
}

export async function fetchDocuments(id: string): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/repositories/${id}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocument(id: string, docType: string): Promise<DocumentItem> {
  const res = await fetch(`${API_BASE}/repositories/${id}/documents/${docType}`);
  if (!res.ok) throw new Error(`Failed to fetch ${docType} document`);
  return res.json();
}

export async function fetchDiagrams(id: string): Promise<DiagramItem[]> {
  const res = await fetch(`${API_BASE}/repositories/${id}/diagrams`);
  if (!res.ok) throw new Error('Failed to fetch diagrams');
  return res.json();
}

export async function fetchChatHistory(id: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/repositories/${id}/chat`);
  if (!res.ok) throw new Error('Failed to fetch chat history');
  return res.json();
}

export async function sendChatMessage(id: string, content: string): Promise<ChatMessage> {
  const res = await fetch(`${API_BASE}/repositories/${id}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error('Failed to send chat message');
  return res.json();
}

export async function syncRepository(id: string): Promise<SyncResult> {
  const res = await fetch(`${API_BASE}/repositories/${id}/sync`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to sync repository');
  return res.json();
}

export async function fetchSettings(): Promise<ProviderSettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(payload: any): Promise<ProviderSettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update settings');
  return res.json();
}
