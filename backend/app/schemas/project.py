from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, AliasChoices, computed_field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project display name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional project description")
    source_type: str = Field("zip", description="Source type: 'zip', 'git', or 'local'")
    source_url: Optional[str] = Field(None, max_length=500, description="GitHub repository URL if source_type is 'git'")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        valid_types = {"zip", "git", "local"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid source_type '{v}'. Must be one of: {', '.join(valid_types)}")
        return v.lower()


class ProjectCloneRequest(BaseModel):
    source_url: Optional[str] = Field(None, description="Public GitHub repository URL (e.g. https://github.com/owner/repo)")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    repository_path: str
    status: str
    error_message: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    languages: Dict[str, Any] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    structure: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime



class ProjectFileNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    children: Optional[List["ProjectFileNode"]] = None


class ProjectFilesResponse(BaseModel):
    project_id: str
    total_files: int
    files: List[ProjectFileNode]


class SystemStatusResponse(BaseModel):
    status: str
    application: Dict[str, Any]
    database: Dict[str, Any]
    ai_provider: Dict[str, Any]
    vector_database: Dict[str, Any]


class ProjectStructureNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    extension: Optional[str] = None
    file_size: Optional[int] = None
    estimated_line_count: Optional[int] = None
    file_category: Optional[str] = None
    language: Optional[str] = None
    children: Optional[List["ProjectStructureNode"]] = None


class ProjectStructureResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    tree: ProjectStructureNode


class ProjectTechnologiesResponse(BaseModel):
    project_id: str
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)


class ProjectStatisticsResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    total_lines: int
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    categories: Dict[str, int] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)


class ProjectScanResponse(BaseModel):
    project_id: str
    status: str
    total_files: int
    total_directories: int
    total_lines: int
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)
    scanned_at: datetime




class CodeEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_path: str
    name: str
    entity_type: str  # MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT
    start_line: int
    end_line: int
    signature: Optional[str] = None
    parent_entity: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))



class ProjectParseResponse(BaseModel):
    project_id: str
    status: str
    total_files_parsed: int
    total_entities_extracted: int
    entity_breakdown: Dict[str, int] = Field(default_factory=dict)
    parsed_at: datetime


class DependencyNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    node_type: str  # file, module, class, function, service, external
    file_path: Optional[str] = None
    entity_id: Optional[str] = None
    is_external: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))


class DependencyRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source: str
    target: str
    source_type: str = "unknown"
    target_type: str = "unknown"
    relationship_type: str  # IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, USES
    confidence: float = 1.0
    is_external: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))


class DependencyGraphResponse(BaseModel):
    project_id: str
    nodes: List[DependencyNodeResponse] = Field(default_factory=list)
    edges: List[DependencyRelationshipResponse] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class DependencyAnalysisResponse(BaseModel):
    project_id: str
    status: str
    total_nodes: int
    total_edges: int
    internal_dependencies: int
    external_dependencies: int
    breakdown: Dict[str, int] = Field(default_factory=dict)
    analyzed_at: datetime


class EntityDependenciesResponse(BaseModel):
    project_id: str
    entity_id: str
    entity_name: str
    node: Optional[DependencyNodeResponse] = None
    incoming: List[DependencyRelationshipResponse] = Field(default_factory=list)
    outgoing: List[DependencyRelationshipResponse] = Field(default_factory=list)
    neighbors: List[DependencyNodeResponse] = Field(default_factory=list)


class APIEndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    method: str
    path: str
    handler_name: str
    file_path: str
    request_schema: Dict[str, Any] = Field(default_factory=dict)
    response_schema: Dict[str, Any] = Field(default_factory=dict)
    authentication_required: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None


class APIEndpointDetailResponse(APIEndpointResponse):
    related_components: List[Dict[str, Any]] = Field(default_factory=list)


class APIAnalysisResponse(BaseModel):
    project_id: str
    status: str
    total_endpoints: int
    authenticated_endpoints: int
    public_endpoints: int
    method_breakdown: Dict[str, int] = Field(default_factory=dict)
    framework_breakdown: Dict[str, int] = Field(default_factory=dict)
    endpoints: List[APIEndpointResponse] = Field(default_factory=list)
    analyzed_at: datetime


class DatabaseFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None
    is_nullable: bool = True
    default_value: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))


class DatabaseRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    source_model: str
    target_model: str
    relationship_type: str  # ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY, FOREIGN_KEY
    foreign_key_field: Optional[str] = None
    back_populates: Optional[str] = None
    secondary_table: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))


class DatabaseModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    name: str
    table_name: str
    file_path: str
    orm_type: str = "SQLAlchemy"
    start_line: int = 1
    fields: List[DatabaseFieldResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None


class DatabaseAnalysisResponse(BaseModel):
    project_id: str
    status: str
    total_models: int
    total_fields: int
    total_relationships: int
    orm_breakdown: Dict[str, int] = Field(default_factory=dict)
    models: List[DatabaseModelResponse] = Field(default_factory=list)
    relationships: List[DatabaseRelationshipResponse] = Field(default_factory=list)
    analyzed_at: datetime


class DatabaseDiagramResponse(BaseModel):
    project_id: str
    mermaid_code: str
    total_models: int
    total_relationships: int


# =============================================================================
# PHASE 8: UNIFIED PROJECT KNOWLEDGE GRAPH SCHEMAS
# =============================================================================

class KnowledgeNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    name: str
    label: str
    node_type: str  # folder, file, module, class, function, api, database, service, external
    file_path: Optional[str] = None
    entity_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None


class KnowledgeEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    source: str = Field(validation_alias=AliasChoices("source_id", "source"))
    target: str = Field(validation_alias=AliasChoices("target_id", "target"))
    source_name: str
    target_name: str
    source_type: str
    target_type: str
    relationship_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))

    @computed_field
    @property
    def source_id(self) -> str:
        return self.source

    @computed_field
    @property
    def target_id(self) -> str:
        return self.target



class KnowledgeGraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int] = Field(default_factory=dict)
    relationship_types: Dict[str, int] = Field(default_factory=dict)


class KnowledgeGraphResponse(BaseModel):
    project_id: str
    nodes: List[KnowledgeNodeResponse] = Field(default_factory=list)
    edges: List[KnowledgeEdgeResponse] = Field(default_factory=list)
    stats: KnowledgeGraphStats
    limit: int = 150
    offset: int = 0
    has_more: bool = False
    focus_id: Optional[str] = None
    depth: Optional[int] = None


class KnowledgeBuildResponse(BaseModel):
    project_id: str
    status: str
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int] = Field(default_factory=dict)
    relationship_types: Dict[str, int] = Field(default_factory=dict)
    built_at: datetime


class KnowledgeEntityDetailResponse(BaseModel):
    entity: KnowledgeNodeResponse
    incoming_edges: List[KnowledgeEdgeResponse] = Field(default_factory=list)
    outgoing_edges: List[KnowledgeEdgeResponse] = Field(default_factory=list)
    connected_apis: List[KnowledgeNodeResponse] = Field(default_factory=list)
    connected_database_models: List[KnowledgeNodeResponse] = Field(default_factory=list)
    dependencies: List[KnowledgeNodeResponse] = Field(default_factory=list)
    dependents: List[KnowledgeNodeResponse] = Field(default_factory=list)
    neighborhood_nodes: List[KnowledgeNodeResponse] = Field(default_factory=list)
    neighborhood_edges: List[KnowledgeEdgeResponse] = Field(default_factory=list)


# =============================================================================
# PHASE 9: AI DOCUMENTATION GENERATION SCHEMAS
# =============================================================================

class DocumentGenerateRequest(BaseModel):
    document_types: Optional[List[str]] = Field(
        None,
        description="List of document types to generate: PROJECT_OVERVIEW, README, FOLDER_DOCS, FILE_DOCS, CLASS_DOCS, FUNCTION_DOCS, API_DOCS, DATABASE_DOCS, ARCHITECTURE_OVERVIEW",
    )
    target_path: Optional[str] = Field(None, description="Optional target file or folder path for granular doc")
    target_entity_id: Optional[str] = Field(None, description="Optional target entity ID (class, function, API)")
    force_regenerate: bool = Field(False, description="Whether to overwrite existing documents or bump versions")


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    document_type: str = Field(validation_alias=AliasChoices("document_type", "doc_type"))
    title: str
    content: str
    target_path: Optional[str] = None
    target_entity_id: Optional[str] = None
    source_entities: List[str] = Field(default_factory=list)
    model: Optional[str] = None
    version: int = 1
    generated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentGenerateResponse(BaseModel):
    status: str
    project_id: str
    total_generated: int
    documents: List[DocumentResponse] = Field(default_factory=list)
    message: Optional[str] = None


# =============================================================================
# PHASE 10: AUTOMATIC ARCHITECTURE DIAGRAM GENERATION SCHEMAS
# =============================================================================

class DiagramGenerateRequest(BaseModel):
    diagram_types: Optional[List[str]] = Field(
        None,
        description="List of diagram types to generate: SYSTEM_ARCHITECTURE, MODULE_ARCHITECTURE, DEPENDENCY_DIAGRAM, API_SERVICE_RELATIONSHIP, DATABASE_ER",
    )
    include_flow_data: bool = Field(True, description="Whether to compute React Flow node/edge graph data")
    use_llm_enhancement: bool = Field(False, description="Whether to optionally enhance diagram titles and descriptions via LLM")
    force_regenerate: bool = Field(False, description="Whether to regenerate existing diagrams and bump version")


class DiagramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str = Field(validation_alias=AliasChoices("project_id", "repository_id"))
    diagram_type: str
    title: str
    description: Optional[str] = None
    mermaid_code: str
    flow_data: Optional[Dict[str, Any]] = None
    source_entities: List[str] = Field(default_factory=list)
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DiagramGenerateResponse(BaseModel):
    status: str
    project_id: str
    total_generated: int
    diagrams: List[DiagramResponse] = Field(default_factory=list)
    message: Optional[str] = None


# =============================================================================
# PHASE 11: AUTOMATIC SEQUENCE DIAGRAM GENERATION SCHEMAS
# =============================================================================

class SequenceStep(BaseModel):
    step_number: int
    source: str
    target: str
    action: str
    return_action: Optional[str] = None
    confidence: float = Field(0.90, ge=0.0, le=1.0)
    step_type: str = Field("INTERACTION", description="USER_INTERACTION, HTTP_REQUEST, FUNCTION_CALL, DATABASE_QUERY, RETURN")


class SequenceDiagramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str
    name: str
    flow_key: str
    description: Optional[str] = None
    trigger_endpoint: Optional[str] = None
    trigger_method: Optional[str] = None
    flow_category: str
    mermaid_code: str
    steps: List[SequenceStep] = Field(default_factory=list)
    involved_components: List[str] = Field(default_factory=list)
    overall_confidence: float = 0.85
    execution_type: str = "Static analysis-based interaction flow"
    is_guaranteed: bool = False
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SequenceGenerateRequest(BaseModel):
    flow_categories: Optional[List[str]] = Field(
        None,
        description="Filter categories: AUTHENTICATION, REGISTRATION, ORDER, PAYMENT, DATA_MUTATION, GENERAL_FLOW",
    )
    force_regenerate: bool = Field(False, description="Whether to overwrite existing sequence diagrams and increment version")


class SequenceGenerateResponse(BaseModel):
    status: str
    project_id: str
    total_generated: int
    sequences: List[SequenceDiagramResponse] = Field(default_factory=list)
    message: Optional[str] = None


# =============================================================================
# PHASE 12: REPOSITORY-AWARE AI ASSISTANT SCHEMAS
# =============================================================================

class CitationItem(BaseModel):
    file: str
    lines: str
    title: str
    type: str = "code"
    relevance: Optional[float] = None


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="User question or prompt about the repository")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    project_id: str = Field(..., validation_alias=AliasChoices("project_id", "repository_id"))
    role: str = "assistant"
    content: str
    sources: List[CitationItem] = Field(default_factory=list)
    confidence: Optional[str] = None
    intent: Optional[str] = None
    relevant_components: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ChatHistoryClearResponse(BaseModel):
    status: str = "cleared"
    project_id: str
    deleted_count: int = 0







