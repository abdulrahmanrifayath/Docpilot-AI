from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    CloneRequest,
    FileTreeResponse,
)
from backend.app.schemas.technology import TechnologyDetectionResponse
from backend.app.schemas.structure import (
    ProjectStructureResponse,
    ProjectStatisticsResponse,
    ScanResponse,
)
from backend.app.schemas.entity import (
    CodeEntityResponse,
    FileEntitiesResponse,
    ProjectEntitiesResponse,
    ParseResponse,
)
from backend.app.schemas.dependency import (
    DependencyListResponse,
    DependencyGraphResponse,
    EntityDependenciesResponse,
    AnalyzeDependenciesResponse,
)
from backend.app.schemas.api_endpoint import (
    ApiEndpointResponse,
    ApiEndpointListResponse,
    ApiAnalyzeResponse,
)
from backend.app.schemas.database_schema import (
    DatabaseModelListResponse,
    DatabaseRelationshipListResponse,
    DatabaseDiagramResponse,
    DatabaseAnalyzeResponse,
)
from backend.app.schemas.knowledge_graph import (
    KnowledgeGraphResponse,
    KnowledgeEntityDetail,
    KnowledgeBuildResponse,
)
from backend.app.schemas.documentation import (
    DocumentationResponse,
    DocumentationListResponse,
    GenerateDocRequest,
    DocStatusResponse,
    DocumentationGenerationResult,
)
from backend.app.services.project_service import ProjectService
from backend.app.services.repository_service import RepositoryService
from backend.app.services.scan_service import ScanService
from backend.app.services.parse_service import ParseService
from backend.app.services.dependency_service import DependencyService
from backend.app.services.api_service import ApiService
from backend.app.services.database_service import DatabaseService
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.documentation_service import DocumentationService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects",
)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[ProjectResponse]:
    return ProjectService.get_all(db, skip=skip, limit=limit)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return ProjectService.create(db, data)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return ProjectService.get_by_id(db, project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    return ProjectService.update(db, project_id, data)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> None:
    ProjectService.delete(db, project_id)


@router.post(
    "/{project_id}/upload",
    response_model=ProjectResponse,
    summary="Upload project ZIP archive",
    description="Uploads and extracts a project ZIP archive into an isolated workspace with Zip-Slip protection.",
)
def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = ProjectService.get_by_id(db, project_id)
    return RepositoryService.extract_zip_archive(project, file, db)


@router.post(
    "/{project_id}/clone",
    response_model=ProjectResponse,
    summary="Clone GitHub repository",
    description="Clones a public GitHub repository into the project workspace safely.",
)
def clone_github_repository(
    project_id: str,
    data: CloneRequest,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = ProjectService.get_by_id(db, project_id)
    return RepositoryService.clone_github_repo(project, data.url, db)


@router.get(
    "/{project_id}/files",
    response_model=FileTreeResponse,
    summary="Get project file tree",
    description="Returns the hierarchical file tree and file summary metrics for the project repository.",
)
def get_project_files(
    project_id: str,
    db: Session = Depends(get_db),
) -> FileTreeResponse:
    project = ProjectService.get_by_id(db, project_id)
    return RepositoryService.get_project_file_tree(project)


# =========================================================================
# Phase 3: Repository Scanner & Technology Detection Endpoints
# =========================================================================

@router.post(
    "/{project_id}/scan",
    response_model=ScanResponse,
    summary="Scan repository structure and technologies",
    description="Analyzes files, counts lines of code, and detects languages, frameworks, and infrastructure.",
)
def scan_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ScanResponse:
    return ScanService.scan_project(project_id, db)


@router.get(
    "/{project_id}/structure",
    response_model=ProjectStructureResponse,
    summary="Get repository file structure and categories",
    description="Returns detailed file tree with line counts, file categories, and language classifications.",
)
def get_project_structure(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectStructureResponse:
    return ScanService.get_structure(project_id, db)


@router.get(
    "/{project_id}/technologies",
    response_model=TechnologyDetectionResponse,
    summary="Get detected technologies, frameworks, and infrastructure",
    description="Returns detected programming languages, web/app frameworks, and infrastructure components.",
)
def get_project_technologies(
    project_id: str,
    db: Session = Depends(get_db),
) -> TechnologyDetectionResponse:
    return ScanService.get_technologies(project_id, db)


@router.get(
    "/{project_id}/statistics",
    response_model=ProjectStatisticsResponse,
    summary="Get repository statistics and code metrics",
    description="Returns total files, lines of code, language breakdown, category distributions, and largest files.",
)
def get_project_statistics(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectStatisticsResponse:
    return ScanService.get_statistics(project_id, db)


# =========================================================================
# Phase 4: Static Code Parsing Engine Endpoints
# =========================================================================

@router.post(
    "/{project_id}/parse",
    response_model=ParseResponse,
    summary="Parse source code into structured code entities",
    description="Runs AST / Tree-sitter parsers on Python, JS, and TS files to extract modules, classes, functions, methods, interfaces, and components.",
)
def parse_project_code(
    project_id: str,
    db: Session = Depends(get_db),
) -> ParseResponse:
    return ParseService.parse_project(project_id, db)


@router.get(
    "/{project_id}/entities",
    response_model=ProjectEntitiesResponse,
    summary="List code entities in project",
    description="Returns code entities in project with optional filtering by entity_type or file_path.",
)
def get_project_entities(
    project_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by type: MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT"),
    file_path: Optional[str] = Query(None, description="Filter by relative file path"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> ProjectEntitiesResponse:
    return ParseService.get_project_entities(
        project_id=project_id,
        db=db,
        entity_type=entity_type,
        file_path=file_path,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{project_id}/entities/{entity_id}",
    response_model=CodeEntityResponse,
    summary="Get code entity details",
    description="Returns detailed metadata, signatures, line ranges, and docstrings for a specific code entity.",
)
def get_entity_by_id(
    project_id: str,
    entity_id: str,
    db: Session = Depends(get_db),
) -> CodeEntityResponse:
    return ParseService.get_entity_by_id(project_id, entity_id, db)


@router.get(
    "/{project_id}/files/{file_path:path}/entities",
    response_model=FileEntitiesResponse,
    summary="Get code entities for a specific file",
    description="Returns all classes, functions, methods, and components declared in the given source file.",
)
def get_file_entities(
    project_id: str,
    file_path: str,
    db: Session = Depends(get_db),
) -> FileEntitiesResponse:
    return ParseService.get_file_entities(project_id, file_path, db)


# =========================================================================
# Phase 5: Dependency and Relationship Analysis Endpoints
# =========================================================================

@router.post(
    "/{project_id}/dependencies/analyze",
    response_model=AnalyzeDependenciesResponse,
    summary="Analyze code dependencies and relationships",
    description="Detects file imports, module dependencies, class inheritance, function calls, and builds the full dependency graph.",
)
def analyze_project_dependencies(
    project_id: str,
    db: Session = Depends(get_db),
) -> AnalyzeDependenciesResponse:
    return DependencyService.analyze_dependencies(project_id, db)


@router.get(
    "/{project_id}/dependencies",
    response_model=DependencyListResponse,
    summary="List project dependencies",
    description="Returns code relationships with optional filtering by relationship_type or internal/external flag.",
)
def get_project_dependencies(
    project_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by: IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, USES"),
    is_internal: Optional[bool] = Query(None, description="Filter by internal/external relationship"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> DependencyListResponse:
    return DependencyService.get_dependencies(
        project_id=project_id,
        db=db,
        relationship_type=relationship_type,
        is_internal=is_internal,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{project_id}/dependencies/graph",
    response_model=DependencyGraphResponse,
    summary="Get dependency graph for visualization",
    description="Returns graph nodes and edges formatted for React Flow with layout positioning.",
)
def get_dependency_graph(
    project_id: str,
    include_external: bool = Query(True, description="Whether to include third-party package dependencies"),
    db: Session = Depends(get_db),
) -> DependencyGraphResponse:
    return DependencyService.get_dependency_graph(
        project_id=project_id,
        db=db,
        include_external=include_external,
    )


@router.get(
    "/{project_id}/dependencies/entity/{entity_id}",
    response_model=EntityDependenciesResponse,
    summary="Get dependencies for a specific entity",
    description="Returns incoming and outgoing dependencies for a specific class, function, or file.",
)
def get_entity_dependencies(
    project_id: str,
    entity_id: str,
    db: Session = Depends(get_db),
) -> EntityDependenciesResponse:
    return DependencyService.get_entity_dependencies(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )


# =========================================================================
# Phase 6: Automatic API Discovery Endpoints
# =========================================================================

@router.post(
    "/{project_id}/apis/analyze",
    response_model=ApiAnalyzeResponse,
    summary="Discover and analyze backend API endpoints",
    description="Detects routes, methods, handlers, request/response models, auth requirements, and tags from FastAPI, Flask, and Express codebases.",
)
def analyze_project_apis(
    project_id: str,
    db: Session = Depends(get_db),
) -> ApiAnalyzeResponse:
    return ApiService.analyze_apis(project_id, db)


@router.get(
    "/{project_id}/apis",
    response_model=ApiEndpointListResponse,
    summary="List detected API endpoints",
    description="Returns API endpoints with optional filtering by HTTP method, tag, or authentication requirement.",
)
def get_project_apis(
    project_id: str,
    method: Optional[str] = Query(None, description="Filter by HTTP method: GET, POST, PUT, DELETE, PATCH"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    auth_required: Optional[bool] = Query(None, description="Filter by authentication requirement"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> ApiEndpointListResponse:
    return ApiService.get_apis(
        project_id=project_id,
        db=db,
        method=method,
        tag=tag,
        auth_required=auth_required,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{project_id}/apis/{api_id}",
    response_model=ApiEndpointResponse,
    summary="Get API endpoint details",
    description="Returns detailed parameter schemas, response models, auth rules, and source location for an individual API route.",
)
def get_api_by_id(
    project_id: str,
    api_id: str,
    db: Session = Depends(get_db),
) -> ApiEndpointResponse:
    return ApiService.get_api_by_id(
        project_id=project_id,
        api_id=api_id,
        db=db,
    )


# =========================================================================
# Phase 7: Database Structure Analysis Endpoints
# =========================================================================

@router.post(
    "/{project_id}/database/analyze",
    response_model=DatabaseAnalyzeResponse,
    summary="Analyze database schema and ORM models",
    description="Detects tables, models, columns, primary/foreign keys, and relationships from SQLAlchemy, Django, and raw SQL schemas.",
)
def analyze_project_database(
    project_id: str,
    db: Session = Depends(get_db),
) -> DatabaseAnalyzeResponse:
    return DatabaseService.analyze_database(project_id, db)


@router.get(
    "/{project_id}/database/models",
    response_model=DatabaseModelListResponse,
    summary="List database models and table schemas",
    description="Returns all detected database models, columns, data types, constraints, and relationships.",
)
def get_database_models(
    project_id: str,
    db: Session = Depends(get_db),
) -> DatabaseModelListResponse:
    return DatabaseService.get_models(project_id, db)


@router.get(
    "/{project_id}/database/relationships",
    response_model=DatabaseRelationshipListResponse,
    summary="List database relationships",
    description="Returns foreign keys, one-to-one, one-to-many, and many-to-many relationships.",
)
def get_database_relationships(
    project_id: str,
    db: Session = Depends(get_db),
) -> DatabaseRelationshipListResponse:
    return DatabaseService.get_relationships(project_id, db)


@router.get(
    "/{project_id}/database/diagram",
    response_model=DatabaseDiagramResponse,
    summary="Get Mermaid ER diagram for database schema",
    description="Generates client-renderable Mermaid ER diagram syntax representing database tables and entity relationships.",
)
def get_database_diagram(
    project_id: str,
    db: Session = Depends(get_db),
) -> DatabaseDiagramResponse:
    return DatabaseService.get_diagram(project_id, db)


# =========================================================================
# Phase 8: Unified Project Knowledge Graph Endpoints
# =========================================================================

@router.post(
    "/{project_id}/knowledge/build",
    response_model=KnowledgeBuildResponse,
    summary="Build unified project knowledge graph",
    description="Aggregates and links files, code entities, API endpoints, dependencies, and database models into an interconnected graph.",
)
def build_project_knowledge_graph(
    project_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeBuildResponse:
    return KnowledgeService.build_knowledge_graph(project_id, db)


@router.get(
    "/{project_id}/knowledge/graph",
    response_model=KnowledgeGraphResponse,
    summary="Get unified knowledge graph",
    description="Returns knowledge graph nodes and edges with support for category filtering, search queries, depth limits, and focus mode.",
)
def get_project_knowledge_graph(
    project_id: str,
    categories: Optional[str] = Query(None, description="Comma-separated category filters (e.g. API,DATABASE_TABLE,CLASS)"),
    focus_node_id: Optional[str] = Query(None, description="Focus on a specific center node and its neighbors"),
    depth: int = Query(2, ge=1, le=5, description="Search depth for focus node exploration"),
    q: Optional[str] = Query(None, description="Search query string"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> KnowledgeGraphResponse:
    return KnowledgeService.get_knowledge_graph(
        project_id=project_id,
        categories=categories,
        focus_node_id=focus_node_id,
        depth=depth,
        search_query=q,
        limit=limit,
        db=db,
    )


@router.get(
    "/{project_id}/knowledge/entity/{entity_id}",
    response_model=KnowledgeEntityDetail,
    summary="Get knowledge entity details and multi-hop impact",
    description="Returns detailed upstream callers, downstream dependencies, connected APIs, and connected database tables for an entity.",
)
def get_knowledge_entity(
    project_id: str,
    entity_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeEntityDetail:
    return KnowledgeService.get_entity_knowledge(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )


# =========================================================================
# Phase 9: AI Documentation Generation Engine Endpoints
# =========================================================================

@router.get(
    "/{project_id}/documentation/status",
    response_model=DocStatusResponse,
    summary="Get LLM configuration and documentation generation status",
    description="Checks whether the LLM provider/key is configured and returns available and generated document types.",
)
def get_documentation_status(
    project_id: str,
    db: Session = Depends(get_db),
) -> DocStatusResponse:
    return DocumentationService.get_llm_status(project_id=project_id, db=db)


@router.post(
    "/{project_id}/documentation/generate",
    response_model=DocumentationGenerationResult,
    summary="Generate AI-powered project documentation",
    description="Generates technical documentation (Project Overview, README, Architecture, APIs, Database, Folders, Files, Classes, Functions) using structured analysis.",
)
async def generate_project_documentation(
    project_id: str,
    data: Optional[GenerateDocRequest] = None,
    db: Session = Depends(get_db),
) -> DocumentationGenerationResult:
    doc_types = data.document_types if data else None
    force_regen = data.force_regenerate if data else False
    provider = data.provider if data else None
    model = data.model if data else None

    return await DocumentationService.generate_documentation(
        project_id=project_id,
        db=db,
        document_types=doc_types,
        force_regenerate=force_regen,
        provider=provider,
        model=model,
    )


@router.get(
    "/{project_id}/documentation",
    response_model=DocumentationListResponse,
    summary="List generated documentation documents",
    description="Returns all generated documentation files for the project with optional document_type and text query filtering.",
)
def list_project_documentation(
    project_id: str,
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. PROJECT_OVERVIEW, README, API_DOCUMENTATION)"),
    q: Optional[str] = Query(None, description="Search query string across titles and markdown content"),
    db: Session = Depends(get_db),
) -> DocumentationListResponse:
    return DocumentationService.get_project_documentation(
        project_id=project_id,
        db=db,
        document_type=document_type,
        search_query=q,
    )


@router.get(
    "/{project_id}/documentation/{document_id}",
    response_model=DocumentationResponse,
    summary="Get documentation document by ID",
    description="Returns markdown content, referenced source entities, and version metadata for a single generated document.",
)
def get_documentation_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentationResponse:
    return DocumentationService.get_document_by_id(
        project_id=project_id,
        document_id=document_id,
        db=db,
    )


@router.post(
    "/{project_id}/documentation/{document_id}/regenerate",
    response_model=DocumentationResponse,
    summary="Regenerate a specific documentation document",
    description="Regenerates markdown content using latest repository facts and increments document version.",
)
async def regenerate_documentation_document(
    project_id: str,
    document_id: str,
    provider: Optional[str] = Query(None, description="Optional provider override (e.g. mock, openai)"),
    model: Optional[str] = Query(None, description="Optional model override"),
    db: Session = Depends(get_db),
) -> DocumentationResponse:
    return await DocumentationService.regenerate_document(
        project_id=project_id,
        document_id=document_id,
        provider=provider,
        model=model,
        db=db,
    )

