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
  description?: string | null;
  source_type: 'zip' | 'github' | 'local';
  source_url?: string | null;
  repository_path?: string | null;
  status: ProjectStatus;
  status_message?: string | null;
  last_analyzed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  description?: string;
  source_type: 'zip' | 'github' | 'local';
  source_url?: string;
}

export interface FileItem {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
  extension?: string | null;
  children?: FileItem[] | null;
}

export interface FileTreeResponse {
  project_id: string;
  repository_path: string;
  total_files: number;
  total_directories: number;
  total_size_bytes: number;
  files: FileItem[];
  language_counts: Record<string, number>;
}

// -------------------------------------------------------------
// Phase 3: Structure & Technology Types
// -------------------------------------------------------------

export interface LanguageStat {
  files: number;
  lines: number;
  percentage: number;
}

export interface FrameworkInfo {
  name: string;
  category: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  indicators: string[];
  version?: string | null;
}

export interface InfrastructureInfo {
  name: string;
  type: string;
  files: string[];
  details?: string | null;
}

export interface TechnologyDetectionResponse {
  project_id: string;
  languages: Record<string, LanguageStat>;
  primary_language?: string | null;
  frameworks: FrameworkInfo[];
  infrastructure: InfrastructureInfo[];
  detected_at: string;
}

export interface StructureItem {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
  lines: number;
  category: string;
  language?: string | null;
  extension?: string | null;
  children?: StructureItem[] | null;
}

export interface ProjectStructureResponse {
  project_id: string;
  repository_path: string;
  total_files: number;
  total_directories: number;
  total_lines: number;
  total_size_bytes: number;
  structure: StructureItem[];
}

export interface FileSummaryInfo {
  path: string;
  name: string;
  lines: number;
  size: number;
  language?: string | null;
  category: string;
}

export interface ProjectStatisticsResponse {
  project_id: string;
  total_files: number;
  total_directories: number;
  total_lines: number;
  total_size_bytes: number;
  languages: Record<string, LanguageStat>;
  categories: Record<string, { files: number; lines: number }>;
  largest_files: FileSummaryInfo[];
}

export interface ScanResponse {
  project_id: string;
  status: string;
  scanned_at: string;
  summary: ProjectStatisticsResponse;
  technologies: TechnologyDetectionResponse;
}

// -------------------------------------------------------------
// Phase 4: Code Entity Types
// -------------------------------------------------------------

export type EntityType =
  | 'MODULE'
  | 'CLASS'
  | 'FUNCTION'
  | 'METHOD'
  | 'INTERFACE'
  | 'COMPONENT';

export interface CodeEntity {
  id: string;
  project_id: string;
  file_path: string;
  name: string;
  entity_type: EntityType;
  start_line: number;
  end_line: number;
  signature?: string | null;
  parent_entity?: string | null;
  docstring?: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface FileEntitiesResponse {
  project_id: string;
  file_path: string;
  total_entities: number;
  entities: CodeEntity[];
  entity_counts: Record<string, number>;
}

export interface ProjectEntitiesResponse {
  project_id: string;
  total_entities: number;
  entities: CodeEntity[];
  entity_counts: Record<string, number>;
}

export interface ParseResponse {
  project_id: string;
  status: string;
  files_parsed: number;
  total_entities: number;
  entities_by_type: Record<string, number>;
  duration_ms: number;
  parsed_at: string;
}

// -------------------------------------------------------------
// Phase 5: Dependency & Relationship Types
// -------------------------------------------------------------

export type RelationshipType =
  | 'IMPORTS'
  | 'CALLS'
  | 'EXTENDS'
  | 'IMPLEMENTS'
  | 'DEPENDS_ON'
  | 'USES';

export type NodeType =
  | 'file'
  | 'module'
  | 'class'
  | 'function'
  | 'service'
  | 'package';

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  file_path?: string | null;
  line_number?: number | null;
  is_internal: boolean;
  position: { x: number; y: number };
  metadata: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  confidence: number;
  is_internal: boolean;
  label?: string | null;
  metadata: Record<string, any>;
}

export interface DependencyItem {
  id: string;
  project_id: string;
  source_id: string;
  source_name: string;
  source_type: string;
  target_id: string;
  target_name: string;
  target_type: string;
  relationship_type: string;
  confidence: number;
  is_internal: boolean;
  file_path?: string | null;
  line_number?: number | null;
  metadata_json: Record<string, any>;
}

export interface DependencyListResponse {
  project_id: string;
  total_dependencies: number;
  dependencies: DependencyItem[];
  counts_by_type: Record<string, number>;
}

export interface DependencyGraphResponse {
  project_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  internal_edges_count: number;
  external_edges_count: number;
}

export interface EntityDependenciesResponse {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  incoming_dependencies: DependencyItem[];
  outgoing_dependencies: DependencyItem[];
  total_dependencies: number;
}

export interface AnalyzeDependenciesResponse {
  project_id: string;
  status: string;
  total_nodes: number;
  total_edges: number;
  internal_edges: number;
  external_edges: number;
  duration_ms: number;
  analyzed_at: string;
}

// -------------------------------------------------------------
// Phase 6: API Discovery Types
// -------------------------------------------------------------

export interface ApiParameter {
  name: string;
  in_location: string;
  type?: string | null;
  required: boolean;
  default?: string | null;
  description?: string | null;
}

export interface ApiRequestSchema {
  parameters: ApiParameter[];
  body_model?: string | null;
  content_type?: string | null;
}

export interface ApiResponseSchema {
  status_code?: number | null;
  response_model?: string | null;
  return_type?: string | null;
  description?: string | null;
}

export interface ApiEndpoint {
  id: string;
  project_id: string;
  method: string;
  path: string;
  handler_name: string;
  file_path: string;
  line_number?: number | null;
  framework: string;
  request_schema?: ApiRequestSchema | null;
  response_schema?: ApiResponseSchema | null;
  authentication_required: boolean;
  tags: string[];
  summary?: string | null;
  docstring?: string | null;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface ApiEndpointListResponse {
  project_id: string;
  total_apis: number;
  apis: ApiEndpoint[];
  methods_count: Record<string, number>;
  frameworks_count: Record<string, number>;
}

export interface ApiAnalyzeResponse {
  project_id: string;
  status: string;
  total_apis: number;
  apis_by_method: Record<string, number>;
  apis_by_framework: Record<string, number>;
  duration_ms: number;
  analyzed_at: string;
}

// -------------------------------------------------------------
// Phase 7: Database Structure & ER Types
// -------------------------------------------------------------

export interface DatabaseField {
  name: string;
  data_type: string;
  primary_key: boolean;
  foreign_key?: string | null;
  nullable: boolean;
  default?: string | null;
  unique: boolean;
  index: boolean;
  description?: string | null;
}

export interface DatabaseRelationship {
  name?: string | null;
  source_model: string;
  source_table: string;
  target_model: string;
  target_table: string;
  relationship_type: string;
  foreign_key?: string | null;
  back_populates?: string | null;
  secondary_table?: string | null;
  confidence: number;
  cardinality_mermaid: string;
  description?: string | null;
  metadata_json: Record<string, any>;
}

export interface DatabaseModel {
  id: string;
  project_id: string;
  model_name: string;
  table_name: string;
  file_path: string;
  line_number?: number | null;
  orm_framework: string;
  docstring?: string | null;
  fields: DatabaseField[];
  relationships: DatabaseRelationship[];
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface DatabaseModelListResponse {
  project_id: string;
  total_models: number;
  models: DatabaseModel[];
  frameworks_count: Record<string, number>;
}

export interface DatabaseRelationshipListResponse {
  project_id: string;
  total_relationships: number;
  relationships: DatabaseRelationship[];
  counts_by_type: Record<string, number>;
}

export interface DatabaseDiagramResponse {
  project_id: string;
  mermaid_code: string;
  total_tables: number;
  total_relationships: number;
  models: DatabaseModel[];
}

export interface DatabaseAnalyzeResponse {
  project_id: string;
  status: string;
  total_models: number;
  total_relationships: number;
  duration_ms: number;
  analyzed_at: string;
}

// -------------------------------------------------------------
// Phase 8: Unified Project Knowledge Graph Types
// -------------------------------------------------------------

export interface KnowledgeNode {
  id: string;
  node_key: string;
  name: string;
  category: string;
  file_path?: string | null;
  line_number?: number | null;
  position: { x: number; y: number };
  metadata: Record<string, any>;
  in_degree: number;
  out_degree: number;
}

export interface KnowledgeEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  confidence: number;
  label?: string | null;
  metadata: Record<string, any>;
}

export interface KnowledgeGraphResponse {
  project_id: string;
  total_nodes: number;
  total_edges: number;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  counts_by_category: Record<string, number>;
  counts_by_relationship: Record<string, number>;
}

export interface KnowledgeEntityDetail {
  node: KnowledgeNode;
  upstream_callers: KnowledgeNode[];
  downstream_dependencies: KnowledgeNode[];
  connected_apis: KnowledgeNode[];
  connected_database_tables: KnowledgeNode[];
  parent_file_or_folder?: KnowledgeNode | null;
}

export interface KnowledgeBuildResponse {
  project_id: string;
  status: string;
  total_nodes: number;
  total_edges: number;
  counts_by_category: Record<string, number>;
  duration_ms: number;
  built_at: string;
}

// -------------------------------------------------------------
// Phase 9: AI Documentation Generation Types
// -------------------------------------------------------------

export type DocumentType =
  | 'PROJECT_OVERVIEW'
  | 'README'
  | 'ARCHITECTURE_OVERVIEW'
  | 'API_DOCUMENTATION'
  | 'DATABASE_DOCUMENTATION'
  | 'FOLDER_DOC'
  | 'FILE_DOC'
  | 'CLASS_DOC'
  | 'FUNCTION_DOC';

export interface Documentation {
  id: string;
  project_id: string;
  document_type: DocumentType | string;
  title: string;
  content: string;
  source_entities: string[];
  model: string;
  version: number;
  metadata_json: Record<string, any>;
  generated_at: string;
  updated_at: string;
}

export interface DocumentationListResponse {
  project_id: string;
  total_documents: number;
  documents: Documentation[];
  counts_by_type: Record<string, number>;
}

export interface GenerateDocRequest {
  document_types?: string[];
  force_regenerate?: boolean;
  provider?: string;
  model?: string;
}

export interface DocStatusResponse {
  llm_configured: boolean;
  provider: string;
  model: string;
  available_doc_types: string[];
  generated_doc_types: string[];
  total_generated: number;
}

export interface DocumentationGenerationResult {
  project_id: string;
  status: string;
  generated_count: number;
  duration_ms: number;
  documents: Documentation[];
}

// -------------------------------------------------------------
// System Status Types
// -------------------------------------------------------------

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
