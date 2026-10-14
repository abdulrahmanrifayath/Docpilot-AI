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
  last_commit_sha?: string;
  sync_status?: 'SYNCED' | 'OUT_OF_SYNC' | 'SYNCING' | 'FAILED' | string;
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

// =============================================================================
// PHASE 7: DATABASE STRUCTURE ANALYSIS TYPES
// =============================================================================

export type DatabaseRelationshipType =
  | 'ONE_TO_ONE'
  | 'ONE_TO_MANY'
  | 'MANY_TO_MANY'
  | 'FOREIGN_KEY';

export interface DatabaseField {
  id: string;
  name: string;
  data_type: string;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  foreign_key_target?: string | null;
  is_nullable: boolean;
  default_value?: string | null;
  metadata?: Record<string, any>;
}

export interface DatabaseRelationship {
  id: string;
  project_id: string;
  source_model: string;
  target_model: string;
  relationship_type: DatabaseRelationshipType | string;
  foreign_key_field?: string | null;
  back_populates?: string | null;
  secondary_table?: string | null;
  description?: string | null;
  metadata?: Record<string, any>;
}

export interface DatabaseModel {
  id: string;
  project_id: string;
  name: string;
  table_name: string;
  file_path: string;
  orm_type: string;
  start_line: number;
  fields: DatabaseField[];
  metadata?: Record<string, any>;
  created_at?: string;
}

export interface DatabaseAnalysisResponse {
  project_id: string;
  status: string;
  total_models: number;
  total_fields: number;
  total_relationships: number;
  orm_breakdown: Record<string, number>;
  models: DatabaseModel[];
  relationships: DatabaseRelationship[];
  analyzed_at: string;
}

export interface DatabaseDiagramResponse {
  project_id: string;
  mermaid_code: string;
  total_models: number;
  total_relationships: number;
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

export type DocumentationType =
  | 'PROJECT_OVERVIEW'
  | 'README'
  | 'ARCHITECTURE_OVERVIEW'
  | 'API_DOCS'
  | 'DATABASE_DOCS'
  | 'FOLDER_DOCS'
  | 'FILE_DOCS'
  | 'CLASS_DOCS'
  | 'FUNCTION_DOCS'
  | string;

export interface DocumentItem {
  id: string;
  project_id: string;
  repository_id?: string;
  document_type: DocumentationType;
  doc_type?: string;
  title: string;
  content: string;
  target_path?: string | null;
  target_entity_id?: string | null;
  source_entities?: string[];
  model?: string | null;
  version?: number;
  generated_at?: string;
  metadata_json?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export type ArchitectureDiagramType =
  | 'SYSTEM_ARCHITECTURE'
  | 'MODULE_ARCHITECTURE'
  | 'DEPENDENCY_DIAGRAM'
  | 'API_SERVICE_RELATIONSHIP'
  | 'DATABASE_ER'
  | 'architecture'
  | 'sequence'
  | 'er'
  | 'dependency'
  | 'react_flow'
  | string;

export interface DiagramItem {
  id: string;
  project_id: string;
  repository_id?: string;
  diagram_type: ArchitectureDiagramType;
  title: string;
  description?: string;
  mermaid_code: string;
  flow_data?: {
    nodes: any[];
    edges: any[];
  } | null;
  source_entities?: string[];
  version: number;
  metadata?: Record<string, any>;
  metadata_json?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface DiagramGeneratePayload {
  diagram_types?: string[];
  include_flow_data?: boolean;
  use_llm_enhancement?: boolean;
  force_regenerate?: boolean;
}

export interface DiagramGenerateResponse {
  status: string;
  project_id: string;
  total_generated: number;
  diagrams: DiagramItem[];
  message?: string;
}

export interface Citation {
  file: string;
  lines: string;
  title: string;
  type: string;
  relevance?: number;
}

export type ChatCitation = Citation;

export interface ChatMessage {
  id: string;
  repository_id?: string;
  project_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Citation[];
  confidence?: string | null;
  intent?: string | null;
  relevant_components?: string[];
  metadata_json?: Record<string, any>;
  created_at?: string;
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

// =============================================================================
// PHASE 8: UNIFIED PROJECT KNOWLEDGE GRAPH TYPES
// =============================================================================

export type KnowledgeNodeType =
  | 'folder'
  | 'file'
  | 'module'
  | 'class'
  | 'function'
  | 'method'
  | 'interface'
  | 'component'
  | 'service'
  | 'api'
  | 'database'
  | 'dependency'
  | string;

export interface KnowledgeNode {
  id: string;
  project_id: string;
  name: string;
  label: string;
  node_type: KnowledgeNodeType;
  file_path?: string | null;
  entity_id?: string | null;
  metadata?: Record<string, any>;
  created_at?: string;
}

export interface KnowledgeEdge {
  id: string;
  project_id: string;
  source: string;
  target: string;
  source_id?: string;
  target_id?: string;
  source_name: string;
  target_name: string;
  source_type: string;
  target_type: string;
  relationship_type: string;
  confidence: number;
  metadata?: Record<string, any>;
}

export interface KnowledgeGraphStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
}

export interface KnowledgeGraphResponse {
  project_id: string;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  stats: KnowledgeGraphStats;
  limit: number;
  offset: number;
  has_more: boolean;
  focus_id?: string | null;
  depth?: number | null;
}

export interface KnowledgeBuildResponse {
  project_id: string;
  status: string;
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  built_at: string;
}

export interface KnowledgeEntityDetailResponse {
  entity: KnowledgeNode;
  incoming_edges: KnowledgeEdge[];
  outgoing_edges: KnowledgeEdge[];
  connected_apis: KnowledgeNode[];
  connected_database_models: KnowledgeNode[];
  dependencies: KnowledgeNode[];
  dependents: KnowledgeNode[];
  neighborhood_nodes: KnowledgeNode[];
  neighborhood_edges: KnowledgeEdge[];
}

// =============================================================================
// PHASE 9: AI DOCUMENTATION GENERATION TYPES
// =============================================================================

export interface DocumentGeneratePayload {
  document_types?: string[];
  target_path?: string;
  target_entity_id?: string;
  force_regenerate?: boolean;
}

export interface DocumentGenerateResponse {
  status: string;
  project_id: string;
  total_generated: number;
  documents: DocumentItem[];
  message?: string;
}

// =============================================================================
// PHASE 11: AUTOMATIC SEQUENCE DIAGRAM GENERATION TYPES
// =============================================================================

export type SequenceFlowCategory =
  | 'AUTHENTICATION'
  | 'REGISTRATION'
  | 'ORDER'
  | 'PAYMENT'
  | 'DATA_MUTATION'
  | 'GENERAL_FLOW'
  | string;

export interface SequenceStep {
  step_number: number;
  source: string;
  target: string;
  action: string;
  return_action?: string | null;
  confidence: number;
  step_type: 'USER_INTERACTION' | 'HTTP_REQUEST' | 'FUNCTION_CALL' | 'DATABASE_QUERY' | 'RETURN' | string;
}

export interface SequenceDiagramItem {
  id: string;
  project_id: string;
  name: string;
  flow_key: string;
  description?: string | null;
  trigger_endpoint?: string | null;
  trigger_method?: string | null;
  flow_category: SequenceFlowCategory;
  mermaid_code: string;
  steps: SequenceStep[];
  involved_components: string[];
  overall_confidence: number;
  execution_type: string;
  is_guaranteed: boolean;
  version: number;
  metadata?: Record<string, any>;
  metadata_json?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface SequenceGeneratePayload {
  flow_categories?: string[];
  force_regenerate?: boolean;
}

export interface SequenceGenerateResponse {
  status: string;
  project_id: string;
  total_generated: number;
  sequences: SequenceDiagramItem[];
  message?: string;
}

// ============================================================================
// Phase 12: Repository-Aware AI Assistant Types
// ============================================================================

export interface ChatHistoryClearResponse {
  status: string;
  project_id: string;
  deleted_count: number;
  message: string;
}

// ============================================================================
// Phase 13: Developer Onboarding Guide Types
// ============================================================================

export interface DetectedCommandItem {
  command: string;
  source_file: string;
  description?: string;
  verified: boolean;
  category?: string;
}

export interface OnboardingSection {
  key: string;
  title: string;
  content: string;
  status: 'DETECTED' | 'PARTIAL' | 'NOT_DETECTED' | string;
  detected_commands: DetectedCommandItem[];
  is_missing: boolean;
  order: number;
}

export interface OnboardingGenerateRequest {
  force_regenerate?: boolean;
}

export interface OnboardingGuideResponse {
  id: string;
  project_id: string;
  title: string;
  markdown_content: string;
  sections: OnboardingSection[];
  detected_tools: string[];
  missing_sections: string[];
  version: number;
  generated_at?: string;
}

// ============================================================================
// Phase 14: Change Detection and Documentation Synchronization Types
// ============================================================================

export interface ChangeCheckResponse {
  project_id: string;
  has_changes: boolean;
  previous_commit_sha?: string | null;
  current_commit_sha?: string | null;
  files_added: string[];
  files_modified: string[];
  files_deleted: string[];
  total_files_changed: number;
  affected_entities: string[];
  affected_apis: string[];
  affected_db_models: string[];
  affected_documents: string[];
  affected_diagrams: string[];
  summary: string;
}

export interface DocumentVersionItem {
  id: string;
  document_id: string;
  version: number;
  document_type: string;
  title: string;
  target_path?: string | null;
  commit_sha?: string | null;
  archived_at?: string;
}

export interface UpdatedDocumentItem {
  document_id: string;
  title: string;
  document_type: string;
  target_path?: string | null;
  version: number;
  previous_version?: number | null;
}

export interface UpdatedDiagramItem {
  diagram_id: string;
  title: string;
  diagram_type: string;
  version: number;
}

export interface ChangeReportResponse {
  id: string;
  project_id: string;
  status: 'SYNCED' | 'NO_CHANGES' | 'FAILED' | string;
  previous_commit_sha?: string | null;
  current_commit_sha?: string | null;
  files_changed: {
    added: string[];
    modified: string[];
    deleted: string[];
  };
  total_files_changed: number;
  entities_affected: string[];
  apis_affected: string[];
  db_models_affected: string[];
  documentation_updated: UpdatedDocumentItem[];
  diagrams_updated: UpdatedDiagramItem[];
  created_at?: string;
  message: string;
  error_message?: string | null;
}

export interface ChangeUpdateRequest {
  force_all?: boolean;
  document_types?: string[];
  regenerate_diagrams?: boolean;
}





