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

export type CodeEntityType = 'MODULE' | 'CLASS' | 'FUNCTION' | 'METHOD' | 'INTERFACE' | 'COMPONENT';

export interface CodeEntity {
  id: string;
  project_id: string;
  file_path: string;
  name: string;
  entity_type: CodeEntityType;
  start_line: number;
  end_line: number;
  signature?: string;
  parent_entity?: string;
  metadata: Record<string, any>;
}

export interface ProjectParseResponse {
  project_id: string;
  status: string;
  total_files_parsed: number;
  total_entities_extracted: number;
  entity_breakdown: Record<string, number>;
  parsed_at: string;
}

export type DependencyRelationshipType =
  | 'IMPORTS'
  | 'CALLS'
  | 'EXTENDS'
  | 'IMPLEMENTS'
  | 'DEPENDS_ON'
  | 'USES';

export type DependencyNodeType =
  | 'file'
  | 'module'
  | 'class'
  | 'function'
  | 'service'
  | 'component'
  | 'interface'
  | 'external';

export interface DependencyNode {
  id: string;
  project_id: string;
  name: string;
  node_type: DependencyNodeType;
  file_path?: string;
  entity_id?: string;
  is_external: boolean;
  metadata: Record<string, any>;
}

export interface DependencyRelationship {
  id: string;
  project_id: string;
  source: string;
  target: string;
  source_type: string;
  target_type: string;
  relationship_type: DependencyRelationshipType;
  confidence: number;
  is_external: boolean;
  metadata: Record<string, any>;
}

export interface DependencyGraphResponse {
  project_id: string;
  nodes: DependencyNode[];
  edges: DependencyRelationship[];
  stats: {
    total_nodes: number;
    total_edges: number;
    node_types: Record<string, number>;
    relationship_types: Record<string, number>;
  };
}

export interface DependencyAnalysisResponse {
  project_id: string;
  status: string;
  total_nodes: number;
  total_edges: number;
  internal_dependencies: number;
  external_dependencies: number;
  breakdown: Record<string, number>;
  analyzed_at: string;
}

export interface EntityDependenciesResponse {
  project_id: string;
  entity_id: string;
  entity_name: string;
  node?: DependencyNode;
  incoming: DependencyRelationship[];
  outgoing: DependencyRelationship[];
  neighbors: DependencyNode[];
}

export interface APIEndpoint {
  id: string;
  project_id: string;
  method: string;
  path: string;
  handler_name: string;
  file_path: string;
  request_schema: {
    body_model?: string | null;
    body_type?: string | null;
    parameters?: Array<{
      name: string;
      type: string;
      in: 'path' | 'query' | 'body' | 'header';
      required: boolean;
      default?: any;
    }>;
  };
  response_schema: {
    model?: string;
    status_code?: number;
    return_type?: string | null;
  };
  authentication_required: boolean;
  tags: string[];
  metadata: {
    start_line?: number;
    end_line?: number;
    framework?: string;
    docstring?: string | null;
    purpose?: string;
    dependencies?: string[];
    middlewares?: string[];
    router_variable?: string | null;
    related_components?: Array<string | { id?: string; name: string; type?: string; file_path?: string }>;
  };
  created_at?: string;
}

export interface APIEndpointDetail extends APIEndpoint {
  related_components: Array<{
    id: string;
    name: string;
    type: string;
    file_path?: string;
    is_external?: boolean;
  }>;
}

export interface APIAnalysisResponse {
  project_id: string;
  status: string;
  total_endpoints: number;
  authenticated_endpoints: number;
  public_endpoints: number;
  method_breakdown: Record<string, number>;
  framework_breakdown: Record<string, number>;
  endpoints: APIEndpoint[];
  analyzed_at: string;
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

