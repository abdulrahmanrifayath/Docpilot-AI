from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectCloneRequest,
    ProjectResponse,
    ProjectFilesResponse,
    ProjectStructureResponse,
    ProjectTechnologiesResponse,
    ProjectStatisticsResponse,
    ProjectScanResponse,
    CodeEntityResponse,
    ProjectParseResponse,
    DependencyNodeResponse,
    DependencyRelationshipResponse,
    DependencyGraphResponse,
    DependencyAnalysisResponse,
    EntityDependenciesResponse,
    APIEndpointResponse,
    APIEndpointDetailResponse,
    APIAnalysisResponse,
    DatabaseModelResponse,
    DatabaseRelationshipResponse,
    DatabaseAnalysisResponse,
    DatabaseDiagramResponse,
    KnowledgeBuildResponse,
    KnowledgeGraphResponse,
    KnowledgeEntityDetailResponse,
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentGenerateResponse,
    DiagramGenerateRequest,
    DiagramResponse,
    DiagramGenerateResponse,
    SequenceGenerateRequest,
    SequenceDiagramResponse,
    SequenceGenerateResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatHistoryClearResponse,
    OnboardingGenerateRequest,
    OnboardingGuideResponse,
)
from app.ai.llm_client import LLMNotConfiguredError
from app.services.project_service import project_service



router = APIRouter(prefix="/projects", tags=["Projects"])



@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new software project record."""
    project = await project_service.create_project(payload, db)
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """List all registered software projects."""
    projects = await project_service.list_projects(db)
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Retrieve details for a single project by ID."""
    project = await project_service.get_project(project_id, db)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete project record and its isolated filesystem workspace."""
    await project_service.delete_project(project_id, db)
    return None


@router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Upload and securely unpack a project ZIP archive into an isolated directory."""
    file_bytes = await file.read()
    project = await project_service.upload_and_extract_zip(
        project_id=project_id,
        filename=file.filename or "project.zip",
        file_bytes=file_bytes,
        db=db,
    )
    return project


@router.post("/{project_id}/clone", response_model=ProjectResponse)
async def clone_project_git(
    project_id: str,
    payload: ProjectCloneRequest = ProjectCloneRequest(),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Clone a public GitHub repository into an isolated project workspace."""
    project = await project_service.clone_github_repo(
        project_id=project_id,
        source_url=payload.source_url,
        db=db,
    )
    return project


@router.get("/{project_id}/files", response_model=ProjectFilesResponse)
async def list_project_files(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectFilesResponse:
    """List file hierarchy and sizes within the project repository path."""
    files_resp = await project_service.list_project_files(project_id, db)
    return files_resp


@router.post("/{project_id}/scan", response_model=ProjectScanResponse)
async def scan_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectScanResponse:
    """Trigger static file discovery, language analysis, and technology detection without an LLM."""
    result = await project_service.scan_project(project_id, db)
    return result


@router.get("/{project_id}/structure", response_model=ProjectStructureResponse)
async def get_project_structure(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectStructureResponse:
    """Retrieve hierarchical repository tree structure with file categories and estimated line counts."""
    result = await project_service.get_project_structure(project_id, db)
    return result


@router.get("/{project_id}/technologies", response_model=ProjectTechnologiesResponse)
async def get_project_technologies(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectTechnologiesResponse:
    """Retrieve detected programming languages, frameworks, and infrastructure components."""
    result = await project_service.get_project_technologies(project_id, db)
    return result


@router.get("/{project_id}/statistics", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectStatisticsResponse:
    """Retrieve project-level metrics including file counts, lines of code, and language distribution."""
    result = await project_service.get_project_statistics(project_id, db)
    return result


@router.post("/{project_id}/parse", response_model=ProjectParseResponse)
async def parse_project_code(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectParseResponse:
    """Trigger static code parsing engine (Python AST, JS/TS Tree-sitter) without AI."""
    result = await project_service.parse_project_code(project_id, db)
    return result


@router.get("/{project_id}/entities", response_model=List[CodeEntityResponse])
async def list_project_entities(
    project_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT)"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    name: Optional[str] = Query(None, description="Search by entity name"),
    db: AsyncSession = Depends(get_db),
) -> List[CodeEntityResponse]:
    """Retrieve normalized code entities extracted across the project."""
    entities = await project_service.get_project_entities(
        project_id=project_id,
        db=db,
        entity_type=entity_type,
        file_path=file_path,
        name=name,
    )
    return entities


@router.get("/{project_id}/entities/{entity_id}", response_model=CodeEntityResponse)
async def get_project_entity(
    project_id: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> CodeEntityResponse:
    """Retrieve a single code entity by its unique ID."""
    entity = await project_service.get_entity_by_id(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )
    return entity


@router.get("/{project_id}/files/{file_id:path}/entities", response_model=List[CodeEntityResponse])
async def list_file_entities(
    project_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[CodeEntityResponse]:
    """Retrieve normalized code entities for a specific file path or file identifier."""
    entities = await project_service.get_file_entities(
        project_id=project_id,
        file_id=file_id,
        db=db,
    )
    return entities


@router.post("/{project_id}/dependencies/analyze", response_model=DependencyAnalysisResponse)
async def analyze_project_dependencies(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DependencyAnalysisResponse:
    """Analyze static dependencies, imports, class inheritance, calls, and external packages."""
    result = await project_service.analyze_dependencies(project_id, db)
    return result


@router.get("/{project_id}/dependencies", response_model=List[DependencyRelationshipResponse])
async def list_project_dependencies(
    project_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, USES)"),
    source: Optional[str] = Query(None, description="Filter by source node or entity name"),
    target: Optional[str] = Query(None, description="Filter by target node or entity name"),
    is_external: Optional[bool] = Query(None, description="Filter by external or internal dependency"),
    min_confidence: Optional[float] = Query(None, description="Filter by minimum confidence score (0.0 - 1.0)"),
    db: AsyncSession = Depends(get_db),
) -> List[DependencyRelationshipResponse]:
    """Retrieve flat list of detected dependencies and relationships with confidence scores."""
    dependencies = await project_service.get_dependencies(
        project_id=project_id,
        db=db,
        relationship_type=relationship_type,
        source=source,
        target=target,
        is_external=is_external,
        min_confidence=min_confidence,
    )
    return dependencies


@router.get("/{project_id}/dependencies/graph", response_model=DependencyGraphResponse)
async def get_project_dependency_graph(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    """Retrieve complete graph structure with nodes, edges, metadata, and statistics for React Flow."""
    graph = await project_service.get_dependency_graph(project_id, db)
    return graph


@router.get("/{project_id}/dependencies/entity/{entity_id}", response_model=EntityDependenciesResponse)
async def get_entity_dependencies(
    project_id: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> EntityDependenciesResponse:
    """Retrieve inbound and outbound dependencies and neighbor nodes for a specific entity or node."""
    result = await project_service.get_entity_dependencies(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )
    return result


# =============================================================================
# PHASE 6: AUTOMATIC API DISCOVERY
# =============================================================================

@router.post("/{project_id}/apis/analyze", response_model=APIAnalysisResponse)
async def analyze_project_apis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> APIAnalysisResponse:
    """Detect backend API endpoints from supported frameworks (FastAPI, Flask, Express)."""
    result = await project_service.analyze_apis(project_id, db)
    return result


@router.get("/{project_id}/apis", response_model=List[APIEndpointResponse])
async def list_project_apis(
    project_id: str,
    method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, PUT, DELETE, PATCH)"),
    tag: Optional[str] = Query(None, description="Filter by API tag or route group"),
    auth_required: Optional[bool] = Query(None, description="Filter by authentication requirement"),
    search: Optional[str] = Query(None, description="Search path, handler name, or file path"),
    db: AsyncSession = Depends(get_db),
) -> List[APIEndpointResponse]:
    """Retrieve list of discovered API endpoints with request/response schemas and auth indicators."""
    endpoints = await project_service.get_apis(
        project_id=project_id,
        db=db,
        method=method,
        tag=tag,
        auth_required=auth_required,
        search=search,
    )
    return endpoints


@router.get("/{project_id}/apis/{api_id}", response_model=APIEndpointDetailResponse)
async def get_project_api_endpoint(
    project_id: str,
    api_id: str,
    db: AsyncSession = Depends(get_db),
) -> APIEndpointDetailResponse:
    """Retrieve detailed API endpoint specification including parameters, schemas, and related components."""
    endpoint = await project_service.get_api_endpoint(
        project_id=project_id,
        api_id=api_id,
        db=db,
    )
    return endpoint


# =============================================================================
# PHASE 7: DATABASE STRUCTURE ANALYSIS
# =============================================================================

@router.post("/{project_id}/database/analyze", response_model=DatabaseAnalysisResponse)
async def analyze_project_database(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DatabaseAnalysisResponse:
    """Statically analyze database models, fields, and relationships from SQLAlchemy, Django ORM, and SQL schemas."""
    return await project_service.analyze_database(project_id, db)


@router.get("/{project_id}/database/models", response_model=List[DatabaseModelResponse])
async def list_project_database_models(
    project_id: str,
    orm_type: Optional[str] = Query(None, description="Filter by ORM type (SQLAlchemy, Django, SQL)"),
    search: Optional[str] = Query(None, description="Search model name, table name, or file path"),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseModelResponse]:
    """Retrieve list of detected database models with fields, types, and primary/foreign keys."""
    models = await project_service.get_database_models(
        project_id=project_id,
        db=db,
        orm_type=orm_type,
        search=search,
    )
    return [DatabaseModelResponse.model_validate(m) for m in models]


@router.get("/{project_id}/database/relationships", response_model=List[DatabaseRelationshipResponse])
async def list_project_database_relationships(
    project_id: str,
    model_name: Optional[str] = Query(None, description="Filter by source or target model name"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY, FOREIGN_KEY)"),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseRelationshipResponse]:
    """Retrieve list of relationships between database entities."""
    relationships = await project_service.get_database_relationships(
        project_id=project_id,
        db=db,
        model_name=model_name,
        relationship_type=relationship_type,
    )
    return [DatabaseRelationshipResponse.model_validate(r) for r in relationships]


@router.get("/{project_id}/database/diagram", response_model=DatabaseDiagramResponse)
async def get_project_database_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DatabaseDiagramResponse:
    """Generate Mermaid ER diagram syntax for project database models and relationships."""
    return await project_service.get_database_diagram(project_id, db)


# =============================================================================
# PHASE 8: UNIFIED PROJECT KNOWLEDGE GRAPH
# =============================================================================

@router.post("/{project_id}/knowledge/build", response_model=KnowledgeBuildResponse)
async def build_project_knowledge_graph(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBuildResponse:
    """Combine results from scanner, code parser, dependency analyzer, API discovery, and database analyzer into a unified knowledge model."""
    return await project_service.build_knowledge_graph(project_id, db)


@router.get("/{project_id}/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_project_knowledge_graph(
    project_id: str,
    node_types: Optional[str] = Query(None, description="Comma-separated node types (e.g. file,class,api,database,service)"),
    search: Optional[str] = Query(None, description="Filter nodes by name or label"),
    focus_id: Optional[str] = Query(None, description="Focus entity ID or name for neighborhood subgraph traversal"),
    depth: int = Query(2, ge=1, le=5, description="Depth radius around focus entity"),
    limit: int = Query(150, ge=1, le=500, description="Max nodes to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    """Retrieve the unified project knowledge graph with filtering, search, focus mode, and pagination."""
    types_list = [t.strip() for t in node_types.split(",") if t.strip()] if node_types else None
    return await project_service.get_knowledge_graph(
        project_id=project_id,
        db=db,
        node_types=types_list,
        search=search,
        focus_id=focus_id,
        depth=depth,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}/knowledge/entity/{entity_id:path}", response_model=KnowledgeEntityDetailResponse)
async def get_project_knowledge_entity_detail(
    project_id: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntityDetailResponse:
    """Query entity knowledge details: what uses it, what it uses, connected APIs, and connected database models."""
    return await project_service.get_entity_knowledge(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )


# =============================================================================
# PHASE 9: AI DOCUMENTATION GENERATION ENDPOINTS
# =============================================================================

@router.post("/{project_id}/documentation/generate", response_model=DocumentGenerateResponse)
async def generate_project_documentation(
    project_id: str,
    payload: Optional[DocumentGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentGenerateResponse:
    """Generate high-quality AI documentation suite from structured repository analysis."""
    req = payload or DocumentGenerateRequest()
    try:
        return await project_service.generate_documentation(
            project_id=project_id,
            db=db,
            document_types=req.document_types,
            target_path=req.target_path,
            target_entity_id=req.target_entity_id,
            force_regenerate=req.force_regenerate,
        )
    except LLMNotConfiguredError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "CONFIGURATION_REQUIRED",
                "message": str(ex.message),
                "provider": ex.provider,
                "is_configured": False,
            },
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.get("/{project_id}/documentation", response_model=List[DocumentResponse])
async def list_project_documentation(
    project_id: str,
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. README, API_DOCS, DATABASE_DOCS)"),
    search: Optional[str] = Query(None, description="Search documentation title or content"),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """List all generated technical documents for a project."""
    await project_service.get_project(project_id, db)
    return await project_service.get_documents(
        project_id=project_id,
        db=db,
        document_type=document_type,
        search=search,
    )


@router.get("/{project_id}/documentation/{document_id}", response_model=DocumentResponse)
async def get_project_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieve full detail of a specific generated technical document."""
    try:
        return await project_service.get_document_by_id(
            project_id=project_id,
            document_id=document_id,
            db=db,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.post("/{project_id}/documentation/{document_id}/regenerate", response_model=DocumentResponse)
async def regenerate_project_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Regenerate a specific document using updated/fresh repository context, bumping version."""
    try:
        return await project_service.regenerate_document(
            project_id=project_id,
            document_id=document_id,
            db=db,
        )
    except LLMNotConfiguredError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "CONFIGURATION_REQUIRED",
                "message": str(ex.message),
                "provider": ex.provider,
                "is_configured": False,
            },
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


# =============================================================================
# PHASE 10: AUTOMATIC ARCHITECTURE DIAGRAM GENERATION ENDPOINTS
# =============================================================================

@router.post(
    "/{project_id}/diagrams/generate",
    response_model=DiagramGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_diagrams(
    project_id: str,
    payload: Optional[DiagramGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> DiagramGenerateResponse:
    """Generate architecture diagrams automatically from repository analysis."""
    req = payload or DiagramGenerateRequest()
    try:
        return await project_service.generate_diagrams(
            project_id=project_id,
            db=db,
            diagram_types=req.diagram_types,
            include_flow_data=req.include_flow_data,
            use_llm_enhancement=req.use_llm_enhancement,
            force_regenerate=req.force_regenerate,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.get("/{project_id}/diagrams", response_model=List[DiagramResponse])
async def list_project_diagrams(
    project_id: str,
    diagram_type: Optional[str] = Query(None, description="Filter by diagram type (e.g. SYSTEM_ARCHITECTURE, MODULE_ARCHITECTURE, DEPENDENCY_DIAGRAM, API_SERVICE_RELATIONSHIP, DATABASE_ER)"),
    db: AsyncSession = Depends(get_db),
) -> List[DiagramResponse]:
    """List all generated architecture diagrams for a project."""
    await project_service.get_project(project_id, db)
    return await project_service.list_diagrams(
        project_id=project_id,
        db=db,
        diagram_type=diagram_type,
    )


@router.get("/{project_id}/diagrams/{diagram_id}", response_model=DiagramResponse)
async def get_project_diagram(
    project_id: str,
    diagram_id: str,
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Retrieve details and Mermaid code of a specific generated diagram."""
    try:
        return await project_service.get_diagram_by_id(
            project_id=project_id,
            diagram_id=diagram_id,
            db=db,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.post("/{project_id}/diagrams/{diagram_id}/regenerate", response_model=DiagramResponse)
async def regenerate_project_diagram(
    project_id: str,
    diagram_id: str,
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Regenerate a specific diagram, refreshing analysis context and incrementing version."""
    try:
        return await project_service.regenerate_diagram(
            project_id=project_id,
            diagram_id=diagram_id,
            db=db,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


# =============================================================================
# PHASE 11: AUTOMATIC SEQUENCE DIAGRAM GENERATION ENDPOINTS
# =============================================================================

@router.post(
    "/{project_id}/sequences/generate",
    response_model=SequenceGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_sequences(
    project_id: str,
    payload: Optional[SequenceGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> SequenceGenerateResponse:
    """Generate sequence diagrams automatically for key application workflows."""
    req = payload or SequenceGenerateRequest()
    try:
        return await project_service.generate_sequences(
            project_id=project_id,
            db=db,
            flow_categories=req.flow_categories,
            force_regenerate=req.force_regenerate,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.get("/{project_id}/sequences", response_model=List[SequenceDiagramResponse])
async def list_project_sequences(
    project_id: str,
    flow_category: Optional[str] = Query(None, description="Filter by flow category (e.g. AUTHENTICATION, REGISTRATION, ORDER, PAYMENT)"),
    db: AsyncSession = Depends(get_db),
) -> List[SequenceDiagramResponse]:
    """List all generated sequence diagrams for a project."""
    await project_service.get_project(project_id, db)
    return await project_service.list_sequences(
        project_id=project_id,
        db=db,
        flow_category=flow_category,
    )


@router.get("/{project_id}/sequences/{sequence_id}", response_model=SequenceDiagramResponse)
async def get_project_sequence(
    project_id: str,
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Retrieve details and Mermaid sequence code of a specific generated workflow."""
    try:
        return await project_service.get_sequence_by_id(
            project_id=project_id,
            sequence_id=sequence_id,
            db=db,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.post("/{project_id}/sequences/{sequence_id}/regenerate", response_model=SequenceDiagramResponse)
async def regenerate_project_sequence(
    project_id: str,
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Regenerate a specific sequence diagram, refreshing analysis context and incrementing version."""
    try:
        return await project_service.regenerate_sequence(
            project_id=project_id,
            sequence_id=sequence_id,
            db=db,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


# -----------------------------------------------------------------------------
# PHASE 12: REPOSITORY-AWARE AI ASSISTANT ENDPOINTS
# -----------------------------------------------------------------------------

@router.post("/{project_id}/chat", response_model=ChatMessageResponse)
async def send_project_chat_message(
    project_id: str,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Ask a question about an analyzed repository using repository-aware RAG."""
    return await project_service.send_chat_message(
        project_id=project_id,
        content=payload.content,
        db=db,
    )


@router.get("/{project_id}/chat/history", response_model=List[ChatMessageResponse])
async def get_project_chat_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ChatMessageResponse]:
    """Retrieve complete chat history for a project."""
    return await project_service.get_chat_history(
        project_id=project_id,
        db=db,
    )


@router.delete("/{project_id}/chat/history", response_model=ChatHistoryClearResponse)
async def clear_project_chat_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryClearResponse:
    """Clear conversation history for a project."""
    return await project_service.clear_chat_history(
        project_id=project_id,
        db=db,
    )


# -----------------------------------------------------------------------------
# PHASE 13: AUTOMATIC DEVELOPER ONBOARDING GUIDE ENDPOINTS
# -----------------------------------------------------------------------------

@router.post("/{project_id}/onboarding/generate", response_model=OnboardingGuideResponse)
async def generate_project_onboarding_guide(
    project_id: str,
    payload: Optional[OnboardingGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """
    Generate or regenerate a practical developer onboarding guide grounded in
    verified repository configuration files, parsed AST, APIs, and sequence flows.
    """
    force = payload.force_regenerate if payload else True
    return await project_service.generate_onboarding_guide(
        project_id=project_id,
        db=db,
        force_regenerate=force,
    )


@router.get("/{project_id}/onboarding", response_model=OnboardingGuideResponse)
async def get_project_onboarding_guide(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """
    Retrieve the developer onboarding guide for an analyzed repository.
    Automatically generates if not yet created.
    """
    return await project_service.get_onboarding_guide(
        project_id=project_id,
        db=db,
    )







