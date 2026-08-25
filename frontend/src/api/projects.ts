import { apiClient } from './client';
import { Project, ProjectCreateInput } from '../types';

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
};
