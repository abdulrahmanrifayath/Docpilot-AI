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
  DependencyNode,
  DependencyRelationship,
  DependencyGraphResponse,
  DependencyAnalysisResponse,
  EntityDependenciesResponse,
  APIEndpoint,
  APIEndpointDetail,
  APIAnalysisResponse,
  DatabaseModel,
  DatabaseRelationship,
  DatabaseAnalysisResponse,
  DatabaseDiagramResponse,
  KnowledgeNode,
  KnowledgeEdge,
  KnowledgeGraphResponse,
  KnowledgeBuildResponse,
  KnowledgeEntityDetailResponse,
  SystemStatus,
  DocumentItem,
  DocumentGeneratePayload,
  DocumentGenerateResponse,
  DiagramItem,
  DiagramGeneratePayload,
  DiagramGenerateResponse,
  ChatMessage,
  ChatHistoryClearResponse,
  ProviderSettings,
  SequenceDiagramItem,
  SequenceGeneratePayload,
  SequenceGenerateResponse,
  OnboardingGuideResponse,
  OnboardingGenerateRequest,
  ChangeCheckResponse,
  ChangeReportResponse,
  ChangeUpdateRequest,
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

export async function analyzeDependencies(id: string): Promise<DependencyAnalysisResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/dependencies/analyze`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Dependency analysis failed' } }));
    throw new Error(err.error?.message || 'Dependency analysis failed');
  }
  return res.json();
}

export async function fetchDependencies(
  id: string,
  options?: {
    relationship_type?: string;
    source?: string;
    target?: string;
    is_external?: boolean;
    min_confidence?: number;
  }
): Promise<DependencyRelationship[]> {
  const params = new URLSearchParams();
  if (options?.relationship_type) params.append('relationship_type', options.relationship_type);
  if (options?.source) params.append('source', options.source);
  if (options?.target) params.append('target', options.target);
  if (options?.is_external !== undefined) params.append('is_external', String(options.is_external));
  if (options?.min_confidence !== undefined) params.append('min_confidence', String(options.min_confidence));

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/dependencies${query}`);
  if (!res.ok) throw new Error('Failed to fetch dependencies');
  return res.json();
}

export async function fetchDependencyGraph(id: string): Promise<DependencyGraphResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/dependencies/graph`);
  if (!res.ok) throw new Error('Failed to fetch dependency graph');
  return res.json();
}

export async function fetchEntityDependencies(
  id: string,
  entityId: string
): Promise<EntityDependenciesResponse> {
  const encoded = encodeURIComponent(entityId);
  const res = await fetch(`${API_V1}/projects/${id}/dependencies/entity/${encoded}`);
  if (!res.ok) throw new Error('Failed to fetch entity dependencies');
  return res.json();
}

// Phase 6: Automatic API Discovery
export async function analyzeProjectApis(id: string): Promise<APIAnalysisResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/apis/analyze`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'API discovery analysis failed' } }));
    throw new Error(err.error?.message || 'API discovery analysis failed');
  }
  return res.json();
}

export async function fetchProjectApis(
  id: string,
  options?: { method?: string; tag?: string; auth_required?: boolean; search?: string }
): Promise<APIEndpoint[]> {
  const params = new URLSearchParams();
  if (options?.method) params.append('method', options.method);
  if (options?.tag) params.append('tag', options.tag);
  if (options?.auth_required !== undefined) params.append('auth_required', String(options.auth_required));
  if (options?.search) params.append('search', options.search);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/apis${query}`);
  if (!res.ok) throw new Error('Failed to fetch project APIs');
  return res.json();
}

export async function fetchProjectApiDetail(
  id: string,
  apiId: string
): Promise<APIEndpointDetail> {
  const encoded = encodeURIComponent(apiId);
  const res = await fetch(`${API_V1}/projects/${id}/apis/${encoded}`);
  if (!res.ok) throw new Error('Failed to fetch API endpoint details');
  return res.json();
}

// Phase 7: Database Structure Analysis
export async function analyzeProjectDatabase(id: string): Promise<DatabaseAnalysisResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/database/analyze`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: 'Database structure analysis failed' } }));
    throw new Error(err.error?.message || 'Database structure analysis failed');
  }
  return res.json();
}

export async function fetchDatabaseModels(
  id: string,
  options?: { orm_type?: string; search?: string }
): Promise<DatabaseModel[]> {
  const params = new URLSearchParams();
  if (options?.orm_type) params.append('orm_type', options.orm_type);
  if (options?.search) params.append('search', options.search);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/database/models${query}`);
  if (!res.ok) throw new Error('Failed to fetch database models');
  return res.json();
}

export async function fetchDatabaseRelationships(
  id: string,
  options?: { model_name?: string; relationship_type?: string }
): Promise<DatabaseRelationship[]> {
  const params = new URLSearchParams();
  if (options?.model_name) params.append('model_name', options.model_name);
  if (options?.relationship_type) params.append('relationship_type', options.relationship_type);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/database/relationships${query}`);
  if (!res.ok) throw new Error('Failed to fetch database relationships');
  return res.json();
}

export async function fetchDatabaseDiagram(id: string): Promise<DatabaseDiagramResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/database/diagram`);
  if (!res.ok) throw new Error('Failed to fetch database ER diagram');
  return res.json();
}

// =============================================================================
// PHASE 8: UNIFIED PROJECT KNOWLEDGE GRAPH CLIENT
// =============================================================================

export async function buildKnowledgeGraph(id: string): Promise<KnowledgeBuildResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/knowledge/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to build unified project knowledge graph');
  return res.json();
}

export async function fetchKnowledgeGraph(
  id: string,
  options?: {
    node_types?: string[];
    search?: string;
    focus_id?: string;
    depth?: number;
    limit?: number;
    offset?: number;
  }
): Promise<KnowledgeGraphResponse> {
  const params = new URLSearchParams();
  if (options?.node_types && options.node_types.length > 0) {
    params.set('node_types', options.node_types.join(','));
  }
  if (options?.search) {
    params.set('search', options.search);
  }
  if (options?.focus_id) {
    params.set('focus_id', options.focus_id);
  }
  if (options?.depth !== undefined) {
    params.set('depth', String(options.depth));
  }
  if (options?.limit !== undefined) {
    params.set('limit', String(options.limit));
  }
  if (options?.offset !== undefined) {
    params.set('offset', String(options.offset));
  }

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${id}/knowledge/graph${query}`);
  if (!res.ok) throw new Error('Failed to fetch project knowledge graph');
  return res.json();
}

export async function fetchKnowledgeEntityDetail(
  id: string,
  entityId: string
): Promise<KnowledgeEntityDetailResponse> {
  const res = await fetch(`${API_V1}/projects/${id}/knowledge/entity/${encodeURIComponent(entityId)}`);
  if (!res.ok) throw new Error('Failed to fetch entity knowledge detail');
  return res.json();
}





// =============================================================================
// PHASE 9: AI DOCUMENTATION GENERATION CLIENT
// =============================================================================

export async function generateDocumentation(
  projectId: string,
  payload?: DocumentGeneratePayload
): Promise<DocumentGenerateResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const err: any = new Error(
      errorData.detail?.message ||
        errorData.error?.message ||
        errorData.detail ||
        'Failed to generate documentation'
    );
    err.status = res.status;
    err.data = errorData.detail || errorData.error || errorData;
    throw err;
  }
  return res.json();
}

export async function fetchProjectDocuments(
  projectId: string,
  options?: { document_type?: string; search?: string }
): Promise<DocumentItem[]> {
  const params = new URLSearchParams();
  if (options?.document_type) params.set('document_type', options.document_type);
  if (options?.search) params.set('search', options.search);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation${query}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchProjectDocument(
  projectId: string,
  documentId: string
): Promise<DocumentItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation/${documentId}`);
  if (!res.ok) throw new Error('Failed to fetch document detail');
  return res.json();
}

export async function regenerateProjectDocument(
  projectId: string,
  documentId: string
): Promise<DocumentItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation/${documentId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const err: any = new Error(
      errorData.detail?.message ||
        errorData.error?.message ||
        errorData.detail ||
        'Failed to regenerate document'
    );
    err.status = res.status;
    err.data = errorData.detail || errorData.error || errorData;
    throw err;
  }
  return res.json();
}

export async function fetchDocuments(projectId: string): Promise<DocumentItem[]> {
  // Primary endpoint with fallback to legacy repositories endpoint
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation`);
  if (res.ok) return res.json();
  const legacyRes = await fetch(`${API_V1}/repositories/${projectId}/documents`);
  if (!legacyRes.ok) return [];
  return legacyRes.json();
}

export async function generateDiagrams(
  projectId: string,
  payload?: DiagramGeneratePayload
): Promise<DiagramGenerateResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/diagrams/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message || err?.detail || 'Failed to generate architecture diagrams');
  }
  return res.json();
}

export async function fetchProjectDiagrams(
  projectId: string,
  diagramType?: string
): Promise<DiagramItem[]> {
  const query = diagramType ? `?diagram_type=${encodeURIComponent(diagramType)}` : '';
  const res = await fetch(`${API_V1}/projects/${projectId}/diagrams${query}`);
  if (res.ok) return res.json();
  const legacyRes = await fetch(`${API_V1}/repositories/${projectId}/diagrams`);
  if (legacyRes.ok) return legacyRes.json();
  return [];
}

export async function fetchProjectDiagram(
  projectId: string,
  diagramId: string
): Promise<DiagramItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/diagrams/${diagramId}`);
  if (!res.ok) throw new Error('Failed to fetch diagram detail');
  return res.json();
}

export async function regenerateProjectDiagram(
  projectId: string,
  diagramId: string
): Promise<DiagramItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/diagrams/${diagramId}/regenerate`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message || err?.detail || 'Failed to regenerate diagram');
  }
  return res.json();
}

export const fetchDiagrams = fetchProjectDiagrams;

// =============================================================================
// PHASE 11: AUTOMATIC SEQUENCE DIAGRAM GENERATION CLIENT
// =============================================================================

export async function generateSequences(
  projectId: string,
  payload?: SequenceGeneratePayload
): Promise<SequenceGenerateResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/sequences/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message || err?.detail || 'Failed to generate sequence diagrams');
  }
  return res.json();
}

export async function fetchProjectSequences(
  projectId: string,
  flowCategory?: string
): Promise<SequenceDiagramItem[]> {
  const query = flowCategory ? `?flow_category=${encodeURIComponent(flowCategory)}` : '';
  const res = await fetch(`${API_V1}/projects/${projectId}/sequences${query}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchProjectSequence(
  projectId: string,
  sequenceId: string
): Promise<SequenceDiagramItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/sequences/${sequenceId}`);
  if (!res.ok) throw new Error('Failed to fetch sequence diagram');
  return res.json();
}

export async function regenerateProjectSequence(
  projectId: string,
  sequenceId: string
): Promise<SequenceDiagramItem> {
  const res = await fetch(`${API_V1}/projects/${projectId}/sequences/${sequenceId}/regenerate`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail?.message || err?.detail || 'Failed to regenerate sequence diagram');
  }
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

// ============================================================================
// Phase 12: Repository-Aware AI Assistant
// ============================================================================

export async function sendChatMessage(
  projectId: string,
  content: string
): Promise<ChatMessage> {
  const res = await fetch(`${API_V1}/projects/${projectId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const err: any = new Error(
      errorData.detail?.message ||
        errorData.error?.message ||
        errorData.detail ||
        'Failed to send chat message'
    );
    err.status = res.status;
    err.data = errorData.detail || errorData.error || errorData;
    throw err;
  }
  return res.json();
}

export async function fetchChatHistory(projectId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_V1}/projects/${projectId}/chat/history`);
  if (!res.ok) return [];
  return res.json();
}

export async function clearChatHistory(
  projectId: string
): Promise<ChatHistoryClearResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/chat/history`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message ||
        errorData.detail ||
        'Failed to clear chat history'
    );
  }
  return res.json();
}

// ============================================================================
// Phase 13: Developer Onboarding Guide
// ============================================================================

export async function generateOnboardingGuide(
  projectId: string,
  forceRegenerate: boolean = true
): Promise<OnboardingGuideResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/onboarding/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_regenerate: forceRegenerate }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message ||
        errorData.detail ||
        'Failed to generate onboarding guide'
    );
  }
  return res.json();
}

export async function fetchOnboardingGuide(
  projectId: string
): Promise<OnboardingGuideResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/onboarding`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message ||
        errorData.detail ||
        'Failed to fetch onboarding guide'
    );
  }
  return res.json();
}

// ============================================================================
// Phase 14: Change Detection and Documentation Synchronization
// ============================================================================

export async function checkProjectChanges(
  projectId: string
): Promise<ChangeCheckResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/changes/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message ||
        errorData.detail ||
        'Failed to check for changes'
    );
  }
  return res.json();
}

export async function fetchProjectChanges(
  projectId: string,
  limit: number = 10
): Promise<ChangeReportResponse[]> {
  const res = await fetch(`${API_V1}/projects/${projectId}/changes?limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function updateProjectDocumentation(
  projectId: string,
  payload?: ChangeUpdateRequest
): Promise<ChangeReportResponse> {
  const res = await fetch(`${API_V1}/projects/${projectId}/documentation/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail?.message ||
        errorData.detail ||
        'Failed to synchronize documentation'
    );
  }
  return res.json();
}


