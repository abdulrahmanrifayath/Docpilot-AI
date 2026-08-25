import { apiClient } from './client';
import { HealthResponse, SystemStatus } from '../types';

export const systemApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  getStatus: async (): Promise<SystemStatus> => {
    const response = await apiClient.get<SystemStatus>('/api/v1/system/status');
    return response.data;
  },
};
