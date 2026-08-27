import { apiClient } from './client';
import {
  Project,
  ProjectCreateInput,
  FileTreeResponse,
  ScanResponse,
  ProjectStructureResponse,
  TechnologyDetectionResponse,
  ProjectStatisticsResponse,
  ParseResponse,
  ProjectEntitiesResponse,
  CodeEntity,
  FileEntitiesResponse,
  AnalyzeDependenciesResponse,
  DependencyListResponse,
  DependencyGraphResponse,
  EntityDependenciesResponse,
  ApiAnalyzeResponse,
  ApiEndpointListResponse,
  ApiEndpoint,
} from '../types';

export const projectsApi = {
  list: async (skip = 0, limit = 100): Promise<Project[]> => {
    const response = await apiClient.get<Project[]>('/api/v1/projects', {
      params: { skip, limit },
    });
    return response.data;
  },

  getById: async (id: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/api/v1/projects/${id}`);
    return response.data;
  },

  create: async (data: ProjectCreateInput): Promise<Project> => {
    const response = await apiClient.post<Project>('/api/v1/projects', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Project>): Promise<Project> => {
    const response = await apiClient.patch<Project>(`/api/v1/projects/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/projects/${id}`);
  },

  uploadZip: async (
    id: string,
    file: File,
    onUploadProgress?: (progress: number) => void
  ): Promise<Project> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<Project>(
      `/api/v1/projects/${id}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onUploadProgress && progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onUploadProgress(percentCompleted);
          }
        },
      }
    );
    return response.data;
  },

  cloneRepo: async (id: string, url: string): Promise<Project> => {
    const response = await apiClient.post<Project>(`/api/v1/projects/${id}/clone`, {
      url,
    });
    return response.data;
  },

  getFiles: async (id: string): Promise<FileTreeResponse> => {
    const response = await apiClient.get<FileTreeResponse>(`/api/v1/projects/${id}/files`);
    return response.data;
  },

  // Phase 3 Scan & Technology APIs
  scan: async (id: string): Promise<ScanResponse> => {
    const response = await apiClient.post<ScanResponse>(`/api/v1/projects/${id}/scan`);
    return response.data;
  },

  getStructure: async (id: string): Promise<ProjectStructureResponse> => {
    const response = await apiClient.get<ProjectStructureResponse>(`/api/v1/projects/${id}/structure`);
    return response.data;
  },

  getTechnologies: async (id: string): Promise<TechnologyDetectionResponse> => {
    const response = await apiClient.get<TechnologyDetectionResponse>(`/api/v1/projects/${id}/technologies`);
    return response.data;
  },

  getStatistics: async (id: string): Promise<ProjectStatisticsResponse> => {
    const response = await apiClient.get<ProjectStatisticsResponse>(`/api/v1/projects/${id}/statistics`);
    return response.data;
  },

  // Phase 4 Static Code Parsing APIs
  parseCode: async (id: string): Promise<ParseResponse> => {
    const response = await apiClient.post<ParseResponse>(`/api/v1/projects/${id}/parse`);
    return response.data;
  },

  getEntities: async (
    id: string,
    params?: { entity_type?: string; file_path?: string; skip?: number; limit?: number }
  ): Promise<ProjectEntitiesResponse> => {
    const response = await apiClient.get<ProjectEntitiesResponse>(`/api/v1/projects/${id}/entities`, {
      params,
    });
    return response.data;
  },

  getEntityById: async (id: string, entityId: string): Promise<CodeEntity> => {
    const response = await apiClient.get<CodeEntity>(`/api/v1/projects/${id}/entities/${entityId}`);
    return response.data;
  },

  getFileEntities: async (id: string, filePath: string): Promise<FileEntitiesResponse> => {
    const response = await apiClient.get<FileEntitiesResponse>(`/api/v1/projects/${id}/files/${filePath}/entities`);
    return response.data;
  },

  // Phase 5 Dependency and Relationship APIs
  analyzeDependencies: async (id: string): Promise<AnalyzeDependenciesResponse> => {
    const response = await apiClient.post<AnalyzeDependenciesResponse>(`/api/v1/projects/${id}/dependencies/analyze`);
    return response.data;
  },

  getDependencies: async (
    id: string,
    params?: { relationship_type?: string; is_internal?: boolean; skip?: number; limit?: number }
  ): Promise<DependencyListResponse> => {
    const response = await apiClient.get<DependencyListResponse>(`/api/v1/projects/${id}/dependencies`, {
      params,
    });
    return response.data;
  },

  getDependencyGraph: async (id: string, includeExternal = true): Promise<DependencyGraphResponse> => {
    const response = await apiClient.get<DependencyGraphResponse>(`/api/v1/projects/${id}/dependencies/graph`, {
      params: { include_external: includeExternal },
    });
    return response.data;
  },

  getEntityDependencies: async (id: string, entityId: string): Promise<EntityDependenciesResponse> => {
    const response = await apiClient.get<EntityDependenciesResponse>(`/api/v1/projects/${id}/dependencies/entity/${entityId}`);
    return response.data;
  },

  // Phase 6 API Discovery APIs
  analyzeApis: async (id: string): Promise<ApiAnalyzeResponse> => {
    const response = await apiClient.post<ApiAnalyzeResponse>(`/api/v1/projects/${id}/apis/analyze`);
    return response.data;
  },

  getApis: async (
    id: string,
    params?: { method?: string; tag?: string; auth_required?: boolean; skip?: number; limit?: number }
  ): Promise<ApiEndpointListResponse> => {
    const response = await apiClient.get<ApiEndpointListResponse>(`/api/v1/projects/${id}/apis`, {
      params,
    });
    return response.data;
  },

  getApiById: async (id: string, apiId: string): Promise<ApiEndpoint> => {
    const response = await apiClient.get<ApiEndpoint>(`/api/v1/projects/${id}/apis/${apiId}`);
    return response.data;
  },
};
