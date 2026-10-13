import {
  Project,
  ProjectCreatePayload,
  ProjectFilesResponse,
  ProjectStructureResponse,
  ProjectTechnologiesResponse,
  ProjectStatisticsResponse,
  ProjectScanResponse,
  CodeEntity,
  ProjectParseResponse,
  SystemStatus,
  DocumentItem,
  DiagramItem,
  ChatMessage,
  ProviderSettings,
} from '../types';



const API_V1 = '/api/v1';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_V1}/system/status`);
  if (!res.ok) throw new Error('Failed to fetch system status');
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${API_V1}/projects`);
  if (!res.ok) throw new Error('Failed to fetch projects');
  return res.json();
}

export async function fetchProject(id: string): Promise<Project> {
  const res = await fetch(`${API_V1}/projects/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Project not found' } }));
    throw new Error(err.error?.message || 'Failed to fetch project');
  }
  return res.json();
}

export async function createProject(payload: ProjectCreatePayload): Promise<Project> {
  const res = await fetch(`${API_V1}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Failed to create project' } }));
    throw new Error(err.error?.message || 'Failed to create project');
  }
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API_V1}/projects/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete project');
}

export async function uploadProjectZip(id: string, file: File): Promise<Project> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_V1}/projects/${id}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Upload failed' } }));
    throw new Error(err.error?.message || 'Upload failed');
  }
  return res.json();
}

export async function cloneProjectGit(id: string, sourceUrl?: string): Promise<Project> {
  const res = await fetch(`${API_V1}/projects/${id}/clone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_url: sourceUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Clone failed' } }));
    throw new Error(err.error?.message || 'Clone failed');
  }
  return res.json();
}

export async function fetchProjectFiles(id: string): Promise<ProjectFilesResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/files`);
  if (!res.ok) throw new Error('Failed to fetch project files');
  return res.json();
}

export async function scanProject(id: string): Promise<ProjectScanResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/scan`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Scan failed' } }));
    throw new Error(err.error?.message || 'Scan failed');
  }
  return res.json();
}

export async function fetchProjectStructure(id: string): Promise<ProjectStructureResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/structure`);
  if (!res.ok) throw new Error('Failed to fetch project structure');
  return res.json();
}

export async function fetchProjectTechnologies(id: string): Promise<ProjectTechnologiesResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/technologies`);
  if (!res.ok) throw new Error('Failed to fetch project technologies');
  return res.json();
}

export async function fetchProjectStatistics(id: string): Promise<ProjectStatisticsResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/statistics`);
  if (!res.ok) throw new Error('Failed to fetch project statistics');
  return res.json();
}

export async function parseProjectCode(id: string): Promise<ProjectParseResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/parse`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Code parsing failed' } }));
    throw new Error(err.error?.message || 'Code parsing failed');
  }
  return res.json();
}

export async function fetchProjectEntities(
  id: string,
  options?: { entity_type?: string; file_path?: string; name?: string }
): Promise<CodeEntity[]> {
  const params = new URLSearchParams();
  if (options?.entity_type) params.append('entity_type', options.entity_type);
  if (options?.file_path) params.append('file_path', options.file_path);
  if (options?.name) params.append('name', options.name);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/entities${query}`);
  if (!res.ok) throw new Error('Failed to fetch project entities');
  return res.json();
}

export async function fetchProjectEntity(id: string, entityId: string): Promise<CodeEntity> {
  const res = await fetch(`${API_V1}/projects/${id}/entities/${entityId}`);
  if (!res.ok) throw new Error('Failed to fetch entity details');
  return res.json();
}

export async function fetchFileEntities(id: string, filePathOrId: string): Promise<CodeEntity[]> {
  // Support slashes by URL encoding or raw path
  const encoded = encodeURIComponent(filePathOrId);
  const res = await fetch(`${API_V1}/projects/${id}/files/${encoded}/entities`);
  if (!res.ok) throw new Error('Failed to fetch file entities');
  return res.json();
}



export async function fetchDocuments(projectId: string): Promise<DocumentItem[]> {
  const res = await fetch(`${API_V1}/repositories/${projectId}/documents`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchDiagrams(projectId: string): Promise<DiagramItem[]> {
  const res = await fetch(`${API_V1}/repositories/${projectId}/diagrams`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchChatHistory(projectId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_V1}/repositories/${projectId}/chat`);
  if (!res.ok) return [];
  return res.json();
}

export async function sendChatMessage(projectId: string, content: string): Promise<ChatMessage> {
  const res = await fetch(`${API_V1}/repositories/${projectId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function fetchSettings(): Promise<ProviderSettings> {
  const res = await fetch(`${API_V1}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(payload: any): Promise<ProviderSettings> {
  const res = await fetch(`${API_V1}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update settings');
  return res.json();
}

// Aliases and helpers for backward compatibility
export const fetchRepositories = fetchProjects;
export const fetchRepository = fetchProject;
export const deleteRepository = deleteProject;

export async function uploadZip(file: File, name?: string): Promise<Project> {
  const proj = await createProject({
    name: name || file.name.replace(/\.zip$/i, ''),
    source_type: 'zip',
  });
  return uploadProjectZip(proj.id, file);
}

export async function cloneGit(sourceUrl: string, name?: string): Promise<Project> {
  const repoName = name || sourceUrl.split('/').pop()?.replace(/\.git$/i, '') || 'git-project';
  const proj = await createProject({
    name: repoName,
    source_type: 'git',
    source_url: sourceUrl,
  });
  return cloneProjectGit(proj.id, sourceUrl);
}

export async function fetchProgress(id: string): Promise<any> {
  const proj = await fetchProject(id);
  return {
    repository_id: proj.id,
    status: proj.status,
    current_step: proj.status,
    progress_percent: proj.status === 'READY' ? 100 : proj.status === 'FAILED' ? 0 : 50,
    error_message: proj.error_message,
  };
}

export async function syncRepository(id: string): Promise<any> {
  return fetchProject(id);
}

export async function triggerAnalysis(id: string): Promise<any> {
  return fetchProject(id);
}

