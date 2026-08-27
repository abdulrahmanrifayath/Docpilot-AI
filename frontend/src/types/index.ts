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
