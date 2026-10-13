export type ProjectStatus =
  | 'CREATED'
  | 'UPLOADING'
  | 'CLONING'
  | 'READY'
  | 'ANALYZING'
  | 'ANALYZED'
  | 'FAILED';

export interface Project {
  id: string;
  name: string;
  description?: string;
  source_type: 'zip' | 'git' | 'local';
  source_url?: string;
  repository_path: string;
  status: ProjectStatus;
  error_message?: string;
  last_analyzed_at?: string;
  languages?: Record<string, { files: number; lines: number; percent?: number }>;
  frameworks?: string[];
  infrastructure?: string[];
  stats?: Record<string, any>;
  structure?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ProjectStructureNode {
  name: string;
  path: string;
  type: 'directory' | 'file';
  extension?: string;
  file_size?: number;
  estimated_line_count?: number;
  file_category?: string;
  language?: string;
  children?: ProjectStructureNode[];
}

export interface ProjectStructureResponse {
  project_id: string;
  total_files: number;
  total_directories: number;
  tree: ProjectStructureNode;
}

export interface ProjectTechnologiesResponse {
  project_id: string;
  languages: Record<string, { files: number; lines: number; percent?: number }>;
  frameworks: string[];
  infrastructure: string[];
}

export interface ProjectStatisticsResponse {
  project_id: string;
  total_files: number;
  total_directories: number;
  total_lines: number;
  languages: Record<string, { files: number; lines: number; percent?: number }>;
  categories: Record<string, number>;
  frameworks: string[];
  infrastructure: string[];
}

export interface ProjectScanResponse {
  project_id: string;
  status: ProjectStatus;
  total_files: number;
  total_directories: number;
  total_lines: number;
  languages: Record<string, { files: number; lines: number; percent?: number }>;
  frameworks: string[];
  infrastructure: string[];
  scanned_at: string;
}


export interface ProjectCreatePayload {
  name: string;
  description?: string;
  source_type: 'zip' | 'git' | 'local';
  source_url?: string;
}

export interface ProjectFileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: ProjectFileNode[];
}

export interface ProjectFilesResponse {
  project_id: string;
  total_files: number;
  files: ProjectFileNode[];
}

export interface SystemStatus {
  status: 'operational' | 'degraded';
  application: {
    status: string;
    name: string;
    version: string;
    environment: string;
  };
  database: {
    status: string;
    type: string;
    error?: string;
  };
  ai_provider: {
    provider: string;
    model: string;
    is_configured: boolean;
  };
  vector_database: {
    type: string;
    status: string;
  };
}

export interface LanguageStat {
  files: number;
  lines: number;
  percent: number;
}

export interface RepositoryStats {
  files: number;
  lines: number;
  classes: number;
  functions: number;
  apis: number;
  models: number;
}

export interface DocumentItem {
  id: string;
  repository_id: string;
  project_id?: string;
  doc_type: 'readme' | 'api' | 'architecture' | 'onboarding' | 'report';
  title: string;
  content: string;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DiagramItem {
  id: string;
  repository_id: string;
  project_id?: string;
  diagram_type: 'architecture' | 'sequence' | 'er' | 'dependency' | 'react_flow';
  title: string;
  mermaid_code?: string;
  flow_data?: {
    nodes: any[];
    edges: any[];
  };
  created_at: string;
}

export interface Citation {
  file: string;
  lines: string;
  title: string;
  type: string;
  relevance?: number;
}

export interface ChatMessage {
  id: string;
  repository_id: string;
  project_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: Citation[];
  created_at: string;
}

export interface ProviderSettings {
  llm_provider: string;
  llm_model: string;
  llm_base_url?: string;
  is_configured: boolean;
  available_providers: string[];
  github_token_configured: boolean;
}

export type Repository = Project;

export interface PipelineProgress {
  repository_id: string;
  status: string;
  current_step?: string;
  progress_percent?: number;
  error_message?: string;
}

