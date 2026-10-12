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

export interface StructureTree {
  name: string;
  type: 'directory' | 'file';
  path: string;
  purpose?: string;
  size?: number;
  children?: StructureTree[];
}

export interface Repository {
  id: string;
  name: string;
  description?: string;
  source_type: 'zip' | 'git' | 'local';
  source_url?: string;
  status: 'pending' | 'analyzing' | 'completed' | 'failed';
  current_step: string;
  progress_percent: number;
  error_message?: string;
  commit_hash?: string;
  languages: Record<string, LanguageStat>;
  frameworks: string[];
  stats: RepositoryStats;
  structure: {
    root_name?: string;
    tree?: StructureTree;
    folder_purposes?: Record<string, string>;
    total_files?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface PipelineProgress {
  repository_id: string;
  status: 'pending' | 'analyzing' | 'completed' | 'failed';
  current_step: string;
  progress_percent: number;
  error_message?: string;
}

export interface DocumentItem {
  id: string;
  repository_id: string;
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

export interface SyncResult {
  repository_id: string;
  changes_detected: boolean;
  modified_files: string[];
  added_files: string[];
  deleted_files: string[];
  regenerated_docs: string[];
  status: string;
}
