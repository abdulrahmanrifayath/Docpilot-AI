export interface Project {
  id: string;
  name: string;
  description?: string | null;
  source_type: 'zip' | 'github' | 'local';
  source_url?: string | null;
  repository_path?: string | null;
  status: 'pending' | 'analyzing' | 'ready' | 'error';
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  description?: string;
  source_type: 'zip' | 'github' | 'local';
  source_url?: string;
}

export interface DatabaseStatus {
  status: 'connected' | 'error';
  engine: string;
  message?: string | null;
}

export interface AIProviderStatus {
  configured: boolean;
  provider: string;
  model: string;
  embedding_model: string;
  message?: string | null;
}

export interface VectorDBStatus {
  status: 'ready' | 'uninitialized' | 'error';
  provider: string;
  storage_path: string;
  message?: string | null;
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  environment: string;
  version: string;
  timestamp: string;
  database: DatabaseStatus;
  ai_provider: AIProviderStatus;
  vector_db: VectorDBStatus;
}

export interface HealthResponse {
  status: string;
  service: string;
}
