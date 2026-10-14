"""
Script to add current_user authorization to all project subresource endpoints in backend/app/api/v1/projects.py
"""

with open('backend/app/api/v1/projects.py', 'r', encoding='utf-8') as f:
    content = f.read().replace('\r\n', '\n')

replacements = [
    # 1. upload_project_zip
    (
        '''@router.post("/{project_id}/upload", response_model=ProjectResponse)
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
    )''',
        '''@router.post("/{project_id}/upload", response_model=ProjectResponse)
async def upload_project_zip(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Upload and securely unpack a project ZIP archive into an isolated directory."""
    file_bytes = await file.read()
    project = await project_service.upload_and_extract_zip(
        project_id=project_id,
        filename=file.filename or "project.zip",
        file_bytes=file_bytes,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 2. clone_project_git
    (
        '''@router.post("/{project_id}/clone", response_model=ProjectResponse)
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
        branch=payload.branch,
    )''',
        '''@router.post("/{project_id}/clone", response_model=ProjectResponse)
async def clone_project_git(
    project_id: str,
    payload: ProjectCloneRequest = ProjectCloneRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Clone a public GitHub repository into an isolated project workspace."""
    project = await project_service.clone_github_repo(
        project_id=project_id,
        source_url=payload.source_url,
        db=db,
        branch=payload.branch,
        user_id=current_user.id,
    )'''
    ),

    # 3. list_project_files
    (
        '''@router.get("/{project_id}/files", response_model=ProjectFilesResponse)
async def list_project_files(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectFilesResponse:
    """List file hierarchy and sizes within the project repository path."""
    files_resp = await project_service.list_project_files(project_id, db)''',
        '''@router.get("/{project_id}/files", response_model=ProjectFilesResponse)
async def list_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectFilesResponse:
    """List file hierarchy and sizes within the project repository path."""
    files_resp = await project_service.list_project_files(project_id, db, user_id=current_user.id)'''
    ),

    # 4. scan_project
    (
        '''@router.post("/{project_id}/scan", response_model=ProjectScanResponse)
async def scan_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectScanResponse:
    """Trigger static file discovery, language analysis, and technology detection without an LLM."""
    result = await project_service.scan_project(project_id, db)''',
        '''@router.post("/{project_id}/scan", response_model=ProjectScanResponse)
async def scan_project(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectScanResponse:
    """Trigger static file discovery, language analysis, and technology detection without an LLM."""
    result = await project_service.scan_project(project_id, db, user_id=current_user.id)'''
    ),

    # 5. get_project_structure
    (
        '''@router.get("/{project_id}/structure", response_model=ProjectStructureResponse)
async def get_project_structure(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectStructureResponse:
    """Retrieve hierarchical repository tree structure with file categories and estimated line counts."""
    result = await project_service.get_project_structure(project_id, db)''',
        '''@router.get("/{project_id}/structure", response_model=ProjectStructureResponse)
async def get_project_structure(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectStructureResponse:
    """Retrieve hierarchical repository tree structure with file categories and estimated line counts."""
    result = await project_service.get_project_structure(project_id, db, user_id=current_user.id)'''
    ),

    # 6. get_project_technologies
    (
        '''@router.get("/{project_id}/technologies", response_model=ProjectTechnologiesResponse)
async def get_project_technologies(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectTechnologiesResponse:
    """Retrieve detected programming languages, frameworks, and infrastructure components."""
    result = await project_service.get_project_technologies(project_id, db)''',
        '''@router.get("/{project_id}/technologies", response_model=ProjectTechnologiesResponse)
async def get_project_technologies(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectTechnologiesResponse:
    """Retrieve detected programming languages, frameworks, and infrastructure components."""
    result = await project_service.get_project_technologies(project_id, db, user_id=current_user.id)'''
    ),

    # 7. get_project_statistics
    (
        '''@router.get("/{project_id}/statistics", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectStatisticsResponse:
    """Retrieve project-level metrics including file counts, lines of code, and language distribution."""
    result = await project_service.get_project_statistics(project_id, db)''',
        '''@router.get("/{project_id}/statistics", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectStatisticsResponse:
    """Retrieve project-level metrics including file counts, lines of code, and language distribution."""
    result = await project_service.get_project_statistics(project_id, db, user_id=current_user.id)'''
    ),

    # 8. parse_project_code
    (
        '''@router.post("/{project_id}/parse", response_model=ProjectParseResponse)
async def parse_project_code(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProjectParseResponse:
    """Trigger static code parsing engine (Python AST, JS/TS Tree-sitter) without AI."""
    result = await project_service.parse_project_code(project_id, db)''',
        '''@router.post("/{project_id}/parse", response_model=ProjectParseResponse)
async def parse_project_code(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ProjectParseResponse:
    """Trigger static code parsing engine (Python AST, JS/TS Tree-sitter) without AI."""
    result = await project_service.parse_project_code(project_id, db, user_id=current_user.id)'''
    ),

    # 9. list_project_entities
    (
        '''@router.get("/{project_id}/entities", response_model=List[CodeEntityResponse])
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
    )''',
        '''@router.get("/{project_id}/entities", response_model=List[CodeEntityResponse])
async def list_project_entities(
    project_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT)"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    name: Optional[str] = Query(None, description="Search by entity name"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[CodeEntityResponse]:
    """Retrieve normalized code entities extracted across the project."""
    entities = await project_service.get_project_entities(
        project_id=project_id,
        db=db,
        entity_type=entity_type,
        file_path=file_path,
        name=name,
        user_id=current_user.id,
    )'''
    ),

    # 10. get_project_entity
    (
        '''@router.get("/{project_id}/entities/{entity_id}", response_model=CodeEntityResponse)
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
    )''',
        '''@router.get("/{project_id}/entities/{entity_id}", response_model=CodeEntityResponse)
async def get_project_entity(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> CodeEntityResponse:
    """Retrieve a single code entity by its unique ID."""
    entity = await project_service.get_entity_by_id(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 11. list_file_entities
    (
        '''@router.get("/{project_id}/files/{file_id:path}/entities", response_model=List[CodeEntityResponse])
async def list_file_entities(
    project_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[CodeEntityResponse]:
    """Retrieve all parsed code entities defined inside a specific file."""
    entities = await project_service.get_file_entities(
        project_id=project_id,
        file_id=file_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/files/{file_id:path}/entities", response_model=List[CodeEntityResponse])
async def list_file_entities(
    project_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[CodeEntityResponse]:
    """Retrieve all parsed code entities defined inside a specific file."""
    entities = await project_service.get_file_entities(
        project_id=project_id,
        file_id=file_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 12. analyze_project_dependencies
    (
        '''@router.post("/{project_id}/dependencies/analyze", response_model=DependencyAnalysisResponse)
async def analyze_project_dependencies(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DependencyAnalysisResponse:
    """Run full static dependency resolution (imports, packages, entity links) without AI."""
    result = await project_service.analyze_dependencies(project_id, db)''',
        '''@router.post("/{project_id}/dependencies/analyze", response_model=DependencyAnalysisResponse)
async def analyze_project_dependencies(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DependencyAnalysisResponse:
    """Run full static dependency resolution (imports, packages, entity links) without AI."""
    result = await project_service.analyze_dependencies(project_id, db, user_id=current_user.id)'''
    ),

    # 13. list_project_dependencies
    (
        '''@router.get("/{project_id}/dependencies", response_model=List[DependencyRelationshipResponse])
async def list_project_dependencies(
    project_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (IMPORTS, CALLS, INHERITS, USES)"),
    source: Optional[str] = Query(None, description="Filter by source node name"),
    target: Optional[str] = Query(None, description="Filter by target node name"),
    is_external: Optional[bool] = Query(None, description="Filter external dependencies"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold (0.0 - 1.0)"),
    db: AsyncSession = Depends(get_db),
) -> List[DependencyRelationshipResponse]:
    """Retrieve resolved dependency relationships between files and code entities."""
    dependencies = await project_service.get_dependencies(
        project_id=project_id,
        db=db,
        relationship_type=relationship_type,
        source=source,
        target=target,
        is_external=is_external,
        min_confidence=min_confidence,
    )''',
        '''@router.get("/{project_id}/dependencies", response_model=List[DependencyRelationshipResponse])
async def list_project_dependencies(
    project_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (IMPORTS, CALLS, INHERITS, USES)"),
    source: Optional[str] = Query(None, description="Filter by source node name"),
    target: Optional[str] = Query(None, description="Filter by target node name"),
    is_external: Optional[bool] = Query(None, description="Filter external dependencies"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence threshold (0.0 - 1.0)"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[DependencyRelationshipResponse]:
    """Retrieve resolved dependency relationships between files and code entities."""
    dependencies = await project_service.get_dependencies(
        project_id=project_id,
        db=db,
        relationship_type=relationship_type,
        source=source,
        target=target,
        is_external=is_external,
        min_confidence=min_confidence,
        user_id=current_user.id,
    )'''
    ),

    # 14. get_project_dependency_graph
    (
        '''@router.get("/{project_id}/dependencies/graph", response_model=DependencyGraphResponse)
async def get_project_dependency_graph(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    """Retrieve full dependency graph payload (nodes and links) structured for frontend visualization."""
    graph = await project_service.get_dependency_graph(project_id, db)''',
        '''@router.get("/{project_id}/dependencies/graph", response_model=DependencyGraphResponse)
async def get_project_dependency_graph(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    """Retrieve full dependency graph payload (nodes and links) structured for frontend visualization."""
    graph = await project_service.get_dependency_graph(project_id, db, user_id=current_user.id)'''
    ),

    # 15. get_entity_dependencies
    (
        '''@router.get("/{project_id}/dependencies/entity/{entity_id}", response_model=EntityDependenciesResponse)
async def get_entity_dependencies(
    project_id: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> EntityDependenciesResponse:
    """Retrieve callers, callees, imports, and downstream dependencies for a specific code entity."""
    result = await project_service.get_entity_dependencies(project_id, entity_id, db)''',
        '''@router.get("/{project_id}/dependencies/entity/{entity_id}", response_model=EntityDependenciesResponse)
async def get_entity_dependencies(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> EntityDependenciesResponse:
    """Retrieve callers, callees, imports, and downstream dependencies for a specific code entity."""
    result = await project_service.get_entity_dependencies(project_id, entity_id, db, user_id=current_user.id)'''
    ),

    # 16. analyze_project_apis
    (
        '''@router.post("/{project_id}/apis/analyze", response_model=APIAnalysisResponse)
async def analyze_project_apis(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> APIAnalysisResponse:
    """Run static API detection across FastAPI, Flask, Express, Django without AI."""
    result = await project_service.analyze_apis(project_id, db)''',
        '''@router.post("/{project_id}/apis/analyze", response_model=APIAnalysisResponse)
async def analyze_project_apis(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> APIAnalysisResponse:
    """Run static API detection across FastAPI, Flask, Express, Django without AI."""
    result = await project_service.analyze_apis(project_id, db, user_id=current_user.id)'''
    ),

    # 17. list_project_apis
    (
        '''@router.get("/{project_id}/apis", response_model=List[APIEndpointResponse])
async def list_project_apis(
    project_id: str,
    method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, PUT, DELETE, PATCH)"),
    tag: Optional[str] = Query(None, description="Filter by tag or category"),
    auth_required: Optional[bool] = Query(None, description="Filter by authentication requirement"),
    search: Optional[str] = Query(None, description="Search path or handler name"),
    db: AsyncSession = Depends(get_db),
) -> List[APIEndpointResponse]:
    """Retrieve detected API endpoints with schemas and handler mappings."""
    endpoints = await project_service.get_apis(
        project_id=project_id,
        db=db,
        method=method,
        tag=tag,
        auth_required=auth_required,
        search=search,
    )''',
        '''@router.get("/{project_id}/apis", response_model=List[APIEndpointResponse])
async def list_project_apis(
    project_id: str,
    method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, PUT, DELETE, PATCH)"),
    tag: Optional[str] = Query(None, description="Filter by tag or category"),
    auth_required: Optional[bool] = Query(None, description="Filter by authentication requirement"),
    search: Optional[str] = Query(None, description="Search path or handler name"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[APIEndpointResponse]:
    """Retrieve detected API endpoints with schemas and handler mappings."""
    endpoints = await project_service.get_apis(
        project_id=project_id,
        db=db,
        method=method,
        tag=tag,
        auth_required=auth_required,
        search=search,
        user_id=current_user.id,
    )'''
    ),

    # 18. get_project_api_endpoint
    (
        '''@router.get("/{project_id}/apis/{api_id}", response_model=APIEndpointDetailResponse)
async def get_project_api_endpoint(
    project_id: str,
    api_id: str,
    db: AsyncSession = Depends(get_db),
) -> APIEndpointDetailResponse:
    """Retrieve full details of an endpoint including parameters, responses, and implementation snippet."""
    endpoint = await project_service.get_api_endpoint(
        project_id=project_id,
        api_id=api_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/apis/{api_id}", response_model=APIEndpointDetailResponse)
async def get_project_api_endpoint(
    project_id: str,
    api_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> APIEndpointDetailResponse:
    """Retrieve full details of an endpoint including parameters, responses, and implementation snippet."""
    endpoint = await project_service.get_api_endpoint(
        project_id=project_id,
        api_id=api_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 19. analyze_project_database
    (
        '''@router.post("/{project_id}/database/analyze", response_model=DatabaseAnalysisResponse)
async def analyze_project_database(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DatabaseAnalysisResponse:
    """Run static database model and schema relationship discovery without executing queries or migrations."""
    return await project_service.analyze_database(project_id, db)''',
        '''@router.post("/{project_id}/database/analyze", response_model=DatabaseAnalysisResponse)
async def analyze_project_database(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DatabaseAnalysisResponse:
    """Run static database model and schema relationship discovery without executing queries or migrations."""
    return await project_service.analyze_database(project_id, db, user_id=current_user.id)'''
    ),

    # 20. list_project_database_models
    (
        '''@router.get("/{project_id}/database/models", response_model=List[DatabaseModelResponse])
async def list_project_database_models(
    project_id: str,
    orm_type: Optional[str] = Query(None, description="Filter by ORM type (SQLAlchemy, Prisma, Django ORM, Raw SQL)"),
    search: Optional[str] = Query(None, description="Search by model or table name"),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseModelResponse]:
    """Retrieve detected database entities, fields, column constraints, and primary keys."""
    models = await project_service.get_database_models(
        project_id=project_id,
        db=db,
        orm_type=orm_type,
        search=search,
    )''',
        '''@router.get("/{project_id}/database/models", response_model=List[DatabaseModelResponse])
async def list_project_database_models(
    project_id: str,
    orm_type: Optional[str] = Query(None, description="Filter by ORM type (SQLAlchemy, Prisma, Django ORM, Raw SQL)"),
    search: Optional[str] = Query(None, description="Search by model or table name"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseModelResponse]:
    """Retrieve detected database entities, fields, column constraints, and primary keys."""
    models = await project_service.get_database_models(
        project_id=project_id,
        db=db,
        orm_type=orm_type,
        search=search,
        user_id=current_user.id,
    )'''
    ),

    # 21. list_project_database_relationships
    (
        '''@router.get("/{project_id}/database/relationships", response_model=List[DatabaseRelationshipResponse])
async def list_project_database_relationships(
    project_id: str,
    model_name: Optional[str] = Query(None, description="Filter relationships connected to a specific model"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (ONE_TO_MANY, MANY_TO_ONE, MANY_TO_MANY, ONE_TO_ONE)"),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseRelationshipResponse]:
    """Retrieve extracted foreign keys, ORM relationships, and cardinalities between database models."""
    relationships = await project_service.get_database_relationships(
        project_id=project_id,
        db=db,
        model_name=model_name,
        relationship_type=relationship_type,
    )''',
        '''@router.get("/{project_id}/database/relationships", response_model=List[DatabaseRelationshipResponse])
async def list_project_database_relationships(
    project_id: str,
    model_name: Optional[str] = Query(None, description="Filter relationships connected to a specific model"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (ONE_TO_MANY, MANY_TO_ONE, MANY_TO_MANY, ONE_TO_ONE)"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseRelationshipResponse]:
    """Retrieve extracted foreign keys, ORM relationships, and cardinalities between database models."""
    relationships = await project_service.get_database_relationships(
        project_id=project_id,
        db=db,
        model_name=model_name,
        relationship_type=relationship_type,
        user_id=current_user.id,
    )'''
    ),

    # 22. get_project_database_diagram
    (
        '''@router.get("/{project_id}/database/diagram", response_model=DatabaseDiagramResponse)
async def get_project_database_diagram(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DatabaseDiagramResponse:
    """Generate and return an automatic Mermaid ER diagram representing all discovered database models and relationships."""
    return await project_service.get_database_diagram(project_id, db)''',
        '''@router.get("/{project_id}/database/diagram", response_model=DatabaseDiagramResponse)
async def get_project_database_diagram(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DatabaseDiagramResponse:
    """Generate and return an automatic Mermaid ER diagram representing all discovered database models and relationships."""
    return await project_service.get_database_diagram(project_id, db, user_id=current_user.id)'''
    ),

    # 23. build_project_knowledge_graph
    (
        '''@router.post("/{project_id}/knowledge/build", response_model=KnowledgeBuildResponse)
async def build_project_knowledge_graph(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBuildResponse:
    """Construct or rebuild unified cross-domain project knowledge graph linking files, entities, APIs, and models."""
    return await project_service.build_knowledge_graph(project_id, db)''',
        '''@router.post("/{project_id}/knowledge/build", response_model=KnowledgeBuildResponse)
async def build_project_knowledge_graph(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBuildResponse:
    """Construct or rebuild unified cross-domain project knowledge graph linking files, entities, APIs, and models."""
    return await project_service.build_knowledge_graph(project_id, db, user_id=current_user.id)'''
    ),

    # 24. get_project_knowledge_graph
    (
        '''@router.get("/{project_id}/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_project_knowledge_graph(
    project_id: str,
    node_types: Optional[str] = Query(None, description="Comma-separated node types to include (FILE, CLASS, FUNCTION, API, DATABASE_MODEL, MODULE, COMPONENT)"),
    search: Optional[str] = Query(None, description="Search term for node names"),
    focus_id: Optional[str] = Query(None, description="Focus on subgraph around a specific node ID"),
    depth: int = Query(2, ge=1, le=5, description="Search depth when focusing on a specific node"),
    limit: int = Query(150, ge=1, le=500, description="Maximum number of nodes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    """Query knowledge graph with multi-type filtering, text search, neighborhood extraction, and pagination."""
    parsed_types = [t.strip().upper() for t in node_types.split(",") if t.strip()] if node_types else None
    return await project_service.get_knowledge_graph(
        project_id=project_id,
        db=db,
        node_types=parsed_types,
        search=search,
        focus_id=focus_id,
        depth=depth,
        limit=limit,
        offset=offset,
    )''',
        '''@router.get("/{project_id}/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_project_knowledge_graph(
    project_id: str,
    node_types: Optional[str] = Query(None, description="Comma-separated node types to include (FILE, CLASS, FUNCTION, API, DATABASE_MODEL, MODULE, COMPONENT)"),
    search: Optional[str] = Query(None, description="Search term for node names"),
    focus_id: Optional[str] = Query(None, description="Focus on subgraph around a specific node ID"),
    depth: int = Query(2, ge=1, le=5, description="Search depth when focusing on a specific node"),
    limit: int = Query(150, ge=1, le=500, description="Maximum number of nodes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    """Query knowledge graph with multi-type filtering, text search, neighborhood extraction, and pagination."""
    parsed_types = [t.strip().upper() for t in node_types.split(",") if t.strip()] if node_types else None
    return await project_service.get_knowledge_graph(
        project_id=project_id,
        db=db,
        node_types=parsed_types,
        search=search,
        focus_id=focus_id,
        depth=depth,
        limit=limit,
        offset=offset,
        user_id=current_user.id,
    )'''
    ),

    # 25. get_project_knowledge_entity_detail
    (
        '''@router.get("/{project_id}/knowledge/entity/{entity_id:path}", response_model=KnowledgeEntityDetailResponse)
async def get_project_knowledge_entity_detail(
    project_id: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntityDetailResponse:
    """Inspect a single knowledge node in detail with all incoming/outgoing cross-layer edges and related concepts."""
    return await project_service.get_entity_knowledge(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/knowledge/entity/{entity_id:path}", response_model=KnowledgeEntityDetailResponse)
async def get_project_knowledge_entity_detail(
    project_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEntityDetailResponse:
    """Inspect a single knowledge node in detail with all incoming/outgoing cross-layer edges and related concepts."""
    return await project_service.get_entity_knowledge(
        project_id=project_id,
        entity_id=entity_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 26. generate_project_documentation
    (
        '''@router.post("/{project_id}/documentation/generate", response_model=DocumentGenerateResponse)
async def generate_project_documentation(
    project_id: str,
    payload: DocumentGenerateRequest = DocumentGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> DocumentGenerateResponse:
    """
    Generate or regenerate structured technical documentation chapters using repository metadata and LLM.
    Supports granular target paths and selective chapter generation.
    """
    try:
        return await project_service.generate_documentation(
            project_id=project_id,
            db=db,
            document_types=payload.document_types,
            target_path=payload.target_path,
            target_entity_id=payload.target_entity_id,
            force_regenerate=payload.force_regenerate,
        )''',
        '''@router.post("/{project_id}/documentation/generate", response_model=DocumentGenerateResponse)
async def generate_project_documentation(
    project_id: str,
    payload: DocumentGenerateRequest = DocumentGenerateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DocumentGenerateResponse:
    """
    Generate or regenerate structured technical documentation chapters using repository metadata and LLM.
    Supports granular target paths and selective chapter generation.
    """
    try:
        return await project_service.generate_documentation(
            project_id=project_id,
            db=db,
            document_types=payload.document_types,
            target_path=payload.target_path,
            target_entity_id=payload.target_entity_id,
            force_regenerate=payload.force_regenerate,
            user_id=current_user.id,
        )'''
    ),

    # 27. list_project_documentation
    (
        '''@router.get("/{project_id}/documentation", response_model=List[DocumentResponse])
async def list_project_documentation(
    project_id: str,
    document_type: Optional[str] = Query(None, description="Filter by doc type: README, ARCHITECTURE, API, DATABASE, ONBOARDING, MODULE"),
    search: Optional[str] = Query(None, description="Search term in title or content"),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """List all generated documentation chapters for a project with optional type filtering and search."""
    await project_service.get_project(project_id, db)
    return await project_service.get_documents(
        project_id=project_id,
        db=db,
        document_type=document_type,
        search=search,
    )''',
        '''@router.get("/{project_id}/documentation", response_model=List[DocumentResponse])
async def list_project_documentation(
    project_id: str,
    document_type: Optional[str] = Query(None, description="Filter by doc type: README, ARCHITECTURE, API, DATABASE, ONBOARDING, MODULE"),
    search: Optional[str] = Query(None, description="Search term in title or content"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """List all generated documentation chapters for a project with optional type filtering and search."""
    await project_service.get_project(project_id, db, user_id=current_user.id)
    return await project_service.get_documents(
        project_id=project_id,
        db=db,
        document_type=document_type,
        search=search,
        user_id=current_user.id,
    )'''
    ),

    # 28. get_project_document
    (
        '''@router.get("/{project_id}/documentation/{document_id}", response_model=DocumentResponse)
async def get_project_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieve full content and metadata for a single generated documentation chapter."""
    return await project_service.get_document_by_id(
        project_id=project_id,
        document_id=document_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/documentation/{document_id}", response_model=DocumentResponse)
async def get_project_document(
    project_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieve full content and metadata for a single generated documentation chapter."""
    return await project_service.get_document_by_id(
        project_id=project_id,
        document_id=document_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 29. regenerate_project_document
    (
        '''@router.post("/{project_id}/documentation/{document_id}/regenerate", response_model=DocumentResponse)
async def regenerate_project_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Regenerate a specific existing documentation chapter using fresh context."""
    try:
        return await project_service.regenerate_document(
            project_id=project_id,
            document_id=document_id,
            db=db,
        )''',
        '''@router.post("/{project_id}/documentation/{document_id}/regenerate", response_model=DocumentResponse)
async def regenerate_project_document(
    project_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Regenerate a specific existing documentation chapter using fresh context."""
    try:
        return await project_service.regenerate_document(
            project_id=project_id,
            document_id=document_id,
            db=db,
            user_id=current_user.id,
        )'''
    ),

    # 30. generate_project_diagrams
    (
        '''@router.post(
    "/{project_id}/diagrams/generate",
    response_model=DiagramGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_diagrams(
    project_id: str,
    payload: DiagramGenerateRequest = DiagramGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> DiagramGenerateResponse:
    """
    Generate Mermaid architectural diagrams from deterministic static analysis.
    Supports system overview, container, component, dependency, and data flow diagrams.
    """
    return await project_service.generate_diagrams(
        project_id=project_id,
        db=db,
        diagram_types=payload.diagram_types,
        include_flow_data=payload.include_flow_data,
        use_llm_enhancement=payload.use_llm_enhancement,
        force_regenerate=payload.force_regenerate,
    )''',
        '''@router.post(
    "/{project_id}/diagrams/generate",
    response_model=DiagramGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_diagrams(
    project_id: str,
    payload: DiagramGenerateRequest = DiagramGenerateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DiagramGenerateResponse:
    """
    Generate Mermaid architectural diagrams from deterministic static analysis.
    Supports system overview, container, component, dependency, and data flow diagrams.
    """
    return await project_service.generate_diagrams(
        project_id=project_id,
        db=db,
        diagram_types=payload.diagram_types,
        include_flow_data=payload.include_flow_data,
        use_llm_enhancement=payload.use_llm_enhancement,
        force_regenerate=payload.force_regenerate,
        user_id=current_user.id,
    )'''
    ),

    # 31. list_project_diagrams
    (
        '''@router.get("/{project_id}/diagrams", response_model=List[DiagramResponse])
async def list_project_diagrams(
    project_id: str,
    diagram_type: Optional[str] = Query(None, description="Filter by diagram type"),
    db: AsyncSession = Depends(get_db),
) -> List[DiagramResponse]:
    """List all generated architecture diagrams for a project."""
    await project_service.get_project(project_id, db)
    return await project_service.list_diagrams(
        project_id=project_id,
        db=db,
        diagram_type=diagram_type,
    )''',
        '''@router.get("/{project_id}/diagrams", response_model=List[DiagramResponse])
async def list_project_diagrams(
    project_id: str,
    diagram_type: Optional[str] = Query(None, description="Filter by diagram type"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[DiagramResponse]:
    """List all generated architecture diagrams for a project."""
    await project_service.get_project(project_id, db, user_id=current_user.id)
    return await project_service.list_diagrams(
        project_id=project_id,
        db=db,
        diagram_type=diagram_type,
        user_id=current_user.id,
    )'''
    ),

    # 32. get_project_diagram
    (
        '''@router.get("/{project_id}/diagrams/{diagram_id}", response_model=DiagramResponse)
async def get_project_diagram(
    project_id: str,
    diagram_id: str,
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Retrieve full details of a specific diagram including Mermaid syntax and node counts."""
    return await project_service.get_diagram_by_id(
        project_id=project_id,
        diagram_id=diagram_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/diagrams/{diagram_id}", response_model=DiagramResponse)
async def get_project_diagram(
    project_id: str,
    diagram_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Retrieve full details of a specific diagram including Mermaid syntax and node counts."""
    return await project_service.get_diagram_by_id(
        project_id=project_id,
        diagram_id=diagram_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 33. regenerate_project_diagram
    (
        '''@router.post("/{project_id}/diagrams/{diagram_id}/regenerate", response_model=DiagramResponse)
async def regenerate_project_diagram(
    project_id: str,
    diagram_id: str,
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Regenerate a specific architecture diagram."""
    return await project_service.regenerate_diagram(
        project_id=project_id,
        diagram_id=diagram_id,
        db=db,
    )''',
        '''@router.post("/{project_id}/diagrams/{diagram_id}/regenerate", response_model=DiagramResponse)
async def regenerate_project_diagram(
    project_id: str,
    diagram_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> DiagramResponse:
    """Regenerate a specific architecture diagram."""
    return await project_service.regenerate_diagram(
        project_id=project_id,
        diagram_id=diagram_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 34. generate_project_sequences
    (
        '''@router.post(
    "/{project_id}/sequences/generate",
    response_model=SequenceGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_sequences(
    project_id: str,
    payload: SequenceGenerateRequest = SequenceGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> SequenceGenerateResponse:
    """
    Generate Mermaid sequence diagrams representing dynamic execution flows.
    Infers lifelines, messages, parameters, returns, and async dispatches.
    """
    return await project_service.generate_sequences(
        project_id=project_id,
        db=db,
        flow_categories=payload.flow_categories,
        force_regenerate=payload.force_regenerate,
    )''',
        '''@router.post(
    "/{project_id}/sequences/generate",
    response_model=SequenceGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_sequences(
    project_id: str,
    payload: SequenceGenerateRequest = SequenceGenerateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> SequenceGenerateResponse:
    """
    Generate Mermaid sequence diagrams representing dynamic execution flows.
    Infers lifelines, messages, parameters, returns, and async dispatches.
    """
    return await project_service.generate_sequences(
        project_id=project_id,
        db=db,
        flow_categories=payload.flow_categories,
        force_regenerate=payload.force_regenerate,
        user_id=current_user.id,
    )'''
    ),

    # 35. list_project_sequences
    (
        '''@router.get("/{project_id}/sequences", response_model=List[SequenceDiagramResponse])
async def list_project_sequences(
    project_id: str,
    flow_category: Optional[str] = Query(None, description="Filter by flow category: api_request, auth, data_pipeline, lifecycle, general"),
    db: AsyncSession = Depends(get_db),
) -> List[SequenceDiagramResponse]:
    """List all generated sequence diagrams for a project."""
    await project_service.get_project(project_id, db)
    return await project_service.list_sequences(
        project_id=project_id,
        db=db,
        flow_category=flow_category,
    )''',
        '''@router.get("/{project_id}/sequences", response_model=List[SequenceDiagramResponse])
async def list_project_sequences(
    project_id: str,
    flow_category: Optional[str] = Query(None, description="Filter by flow category: api_request, auth, data_pipeline, lifecycle, general"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[SequenceDiagramResponse]:
    """List all generated sequence diagrams for a project."""
    await project_service.get_project(project_id, db, user_id=current_user.id)
    return await project_service.list_sequences(
        project_id=project_id,
        db=db,
        flow_category=flow_category,
        user_id=current_user.id,
    )'''
    ),

    # 36. get_project_sequence
    (
        '''@router.get("/{project_id}/sequences/{sequence_id}", response_model=SequenceDiagramResponse)
async def get_project_sequence(
    project_id: str,
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Retrieve full details of a specific sequence diagram including Mermaid sequence syntax."""
    return await project_service.get_sequence_by_id(
        project_id=project_id,
        sequence_id=sequence_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/sequences/{sequence_id}", response_model=SequenceDiagramResponse)
async def get_project_sequence(
    project_id: str,
    sequence_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Retrieve full details of a specific sequence diagram including Mermaid sequence syntax."""
    return await project_service.get_sequence_by_id(
        project_id=project_id,
        sequence_id=sequence_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 37. regenerate_project_sequence
    (
        '''@router.post("/{project_id}/sequences/{sequence_id}/regenerate", response_model=SequenceDiagramResponse)
async def regenerate_project_sequence(
    project_id: str,
    sequence_id: str,
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Regenerate a specific sequence diagram."""
    return await project_service.regenerate_sequence(
        project_id=project_id,
        sequence_id=sequence_id,
        db=db,
    )''',
        '''@router.post("/{project_id}/sequences/{sequence_id}/regenerate", response_model=SequenceDiagramResponse)
async def regenerate_project_sequence(
    project_id: str,
    sequence_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> SequenceDiagramResponse:
    """Regenerate a specific sequence diagram."""
    return await project_service.regenerate_sequence(
        project_id=project_id,
        sequence_id=sequence_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 38. send_project_chat_message
    (
        '''@router.post("/{project_id}/chat", response_model=ChatMessageResponse)
async def send_project_chat_message(
    project_id: str,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Send a message to the Repository-Aware AI Assistant.
    Retrieves context using multi-source RAG and generates code-grounded explanations.
    """
    return await project_service.send_chat_message(
        project_id=project_id,
        content=payload.message,
        db=db,
    )''',
        '''@router.post("/{project_id}/chat", response_model=ChatMessageResponse)
async def send_project_chat_message(
    project_id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """
    Send a message to the Repository-Aware AI Assistant.
    Retrieves context using multi-source RAG and generates code-grounded explanations.
    """
    return await project_service.send_chat_message(
        project_id=project_id,
        content=payload.message,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 39. get_project_chat_history
    (
        '''@router.get("/{project_id}/chat/history", response_model=List[ChatMessageResponse])
async def get_project_chat_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ChatMessageResponse]:
    """Retrieve complete chronological chat session history for a project."""
    return await project_service.get_chat_history(project_id, db)''',
        '''@router.get("/{project_id}/chat/history", response_model=List[ChatMessageResponse])
async def get_project_chat_history(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[ChatMessageResponse]:
    """Retrieve complete chronological chat session history for a project."""
    return await project_service.get_chat_history(project_id, db, user_id=current_user.id)'''
    ),

    # 40. clear_project_chat_history
    (
        '''@router.delete("/{project_id}/chat/history", response_model=ChatHistoryClearResponse)
async def clear_project_chat_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryClearResponse:
    """Clear conversation history for a project repository."""
    return await project_service.clear_chat_history(project_id, db)''',
        '''@router.delete("/{project_id}/chat/history", response_model=ChatHistoryClearResponse)
async def clear_project_chat_history(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryClearResponse:
    """Clear conversation history for a project repository."""
    return await project_service.clear_chat_history(project_id, db, user_id=current_user.id)'''
    ),

    # 41. generate_project_onboarding_guide
    (
        '''@router.post("/{project_id}/onboarding/generate", response_model=OnboardingGuideResponse)
async def generate_project_onboarding_guide(
    project_id: str,
    payload: OnboardingGenerateRequest = OnboardingGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """
    Generate or regenerate a tailored developer onboarding guide.
    Synthesizes tech stack, setup instructions, architecture tour, entry points, and common tasks.
    """
    return await project_service.generate_onboarding_guide(
        project_id=project_id,
        db=db,
        force_regenerate=payload.force_regenerate,
    )''',
        '''@router.post("/{project_id}/onboarding/generate", response_model=OnboardingGuideResponse)
async def generate_project_onboarding_guide(
    project_id: str,
    payload: OnboardingGenerateRequest = OnboardingGenerateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """
    Generate or regenerate a tailored developer onboarding guide.
    Synthesizes tech stack, setup instructions, architecture tour, entry points, and common tasks.
    """
    return await project_service.generate_onboarding_guide(
        project_id=project_id,
        db=db,
        force_regenerate=payload.force_regenerate,
        user_id=current_user.id,
    )'''
    ),

    # 42. get_project_onboarding_guide
    (
        '''@router.get("/{project_id}/onboarding", response_model=OnboardingGuideResponse)
async def get_project_onboarding_guide(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """Retrieve existing developer onboarding guide or auto-generate on first request."""
    return await project_service.get_onboarding_guide(
        project_id=project_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/onboarding", response_model=OnboardingGuideResponse)
async def get_project_onboarding_guide(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> OnboardingGuideResponse:
    """Retrieve existing developer onboarding guide or auto-generate on first request."""
    return await project_service.get_onboarding_guide(
        project_id=project_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 43. check_project_changes
    (
        '''@router.post("/{project_id}/changes/check", response_model=ChangeCheckResponse)
async def check_project_changes(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ChangeCheckResponse:
    """
    Check repository for unanalyzed Git commits or filesystem hash changes.
    Returns status: UNCHANGED, COMMITS_DETECTED, FILES_CHANGED, or UNTRACKED.
    """
    return await project_service.check_changes(project_id, db)''',
        '''@router.post("/{project_id}/changes/check", response_model=ChangeCheckResponse)
async def check_project_changes(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ChangeCheckResponse:
    """
    Check repository for unanalyzed Git commits or filesystem hash changes.
    Returns status: UNCHANGED, COMMITS_DETECTED, FILES_CHANGED, or UNTRACKED.
    """
    return await project_service.check_changes(project_id, db, user_id=current_user.id)'''
    ),

    # 44. list_project_changes
    (
        '''@router.get("/{project_id}/changes", response_model=List[ChangeReportResponse])
async def list_project_changes(
    project_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max history reports to return"),
    db: AsyncSession = Depends(get_db),
) -> List[ChangeReportResponse]:
    """Retrieve historical synchronization change reports and diff impact assessments."""
    return await project_service.get_change_history(project_id, db, limit=limit)''',
        '''@router.get("/{project_id}/changes", response_model=List[ChangeReportResponse])
async def list_project_changes(
    project_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max history reports to return"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[ChangeReportResponse]:
    """Retrieve historical synchronization change reports and diff impact assessments."""
    return await project_service.get_change_history(project_id, db, limit=limit, user_id=current_user.id)'''
    ),

    # 45. update_project_documentation
    (
        '''@router.post("/{project_id}/documentation/update", response_model=ChangeReportResponse)
async def update_project_documentation(
    project_id: str,
    payload: ChangeUpdateRequest = ChangeUpdateRequest(),
    db: AsyncSession = Depends(get_db),
) -> ChangeReportResponse:
    """
    Synchronize documentation by re-analyzing only modified files, updating affected
    entities, dependency relations, and regenerating impacted documentation chapters.
    """
    return await project_service.update_documentation_and_sync(
        project_id=project_id,
        db=db,
        force_all=payload.force_all,
        document_types=payload.document_types,
        regenerate_diagrams=payload.regenerate_diagrams,
    )''',
        '''@router.post("/{project_id}/documentation/update", response_model=ChangeReportResponse)
async def update_project_documentation(
    project_id: str,
    payload: ChangeUpdateRequest = ChangeUpdateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> ChangeReportResponse:
    """
    Synchronize documentation by re-analyzing only modified files, updating affected
    entities, dependency relations, and regenerating impacted documentation chapters.
    """
    return await project_service.update_documentation_and_sync(
        project_id=project_id,
        db=db,
        force_all=payload.force_all,
        document_types=payload.document_types,
        regenerate_diagrams=payload.regenerate_diagrams,
        user_id=current_user.id,
    )'''
    ),

    # 46. get_project_github_status
    (
        '''@router.get("/{project_id}/github/status", response_model=GitHubStatusResponse)
async def get_project_github_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> GitHubStatusResponse:
    """
    Retrieve live GitHub tracking status: current commit, latest remote commit,
    commits behind count, and synchronization indicator.
    """
    return await project_service.get_github_status(project_id, db)''',
        '''@router.get("/{project_id}/github/status", response_model=GitHubStatusResponse)
async def get_project_github_status(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> GitHubStatusResponse:
    """
    Retrieve live GitHub tracking status: current commit, latest remote commit,
    commits behind count, and synchronization indicator.
    """
    return await project_service.get_github_status(project_id, db, user_id=current_user.id)'''
    ),

    # 47. refresh_project_github
    (
        '''@router.post("/{project_id}/github/refresh", response_model=GitHubRefreshResponse)
async def refresh_project_github(
    project_id: str,
    payload: GitHubRefreshRequest = GitHubRefreshRequest(),
    db: AsyncSession = Depends(get_db),
) -> GitHubRefreshResponse:
    """
    Fetch and pull latest remote Git changes, execute incremental analysis on modified files,
    and update affected documentation and architecture diagrams.
    """
    return await project_service.refresh_github_repo(
        project_id=project_id,
        db=db,
        branch=payload.branch,
        force_sync=payload.force_sync,
    )''',
        '''@router.post("/{project_id}/github/refresh", response_model=GitHubRefreshResponse)
async def refresh_project_github(
    project_id: str,
    payload: GitHubRefreshRequest = GitHubRefreshRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> GitHubRefreshResponse:
    """
    Fetch and pull latest remote Git changes, execute incremental analysis on modified files,
    and update affected documentation and architecture diagrams.
    """
    return await project_service.refresh_github_repo(
        project_id=project_id,
        db=db,
        branch=payload.branch,
        force_sync=payload.force_sync,
        user_id=current_user.id,
    )'''
    ),

    # 48. generate_project_technical_report
    (
        '''@router.post("/{project_id}/reports/generate", response_model=TechnicalReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_project_technical_report(
    project_id: str,
    payload: ReportGenerateRequest = ReportGenerateRequest(),
    db: AsyncSession = Depends(get_db),
) -> TechnicalReportResponse:
    """
    Generate a comprehensive 12-section technical report synthesizing detected
    metadata, architectures, schemas, risks, and deployment recommendations.
    """
    return await project_service.generate_project_report(
        project_id=project_id,
        payload=payload,
        db=db,
    )''',
        '''@router.post("/{project_id}/reports/generate", response_model=TechnicalReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_project_technical_report(
    project_id: str,
    payload: ReportGenerateRequest = ReportGenerateRequest(),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> TechnicalReportResponse:
    """
    Generate a comprehensive 12-section technical report synthesizing detected
    metadata, architectures, schemas, risks, and deployment recommendations.
    """
    return await project_service.generate_project_report(
        project_id=project_id,
        payload=payload,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 49. list_project_technical_reports
    (
        '''@router.get("/{project_id}/reports", response_model=List[TechnicalReportResponse])
async def list_project_technical_reports(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[TechnicalReportResponse]:
    """List all previously generated comprehensive technical reports for a project."""
    return await project_service.list_project_reports(
        project_id=project_id,
        db=db,
    )''',
        '''@router.get("/{project_id}/reports", response_model=List[TechnicalReportResponse])
async def list_project_technical_reports(
    project_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
) -> List[TechnicalReportResponse]:
    """List all previously generated comprehensive technical reports for a project."""
    return await project_service.list_project_reports(
        project_id=project_id,
        db=db,
        user_id=current_user.id,
    )'''
    ),

    # 50. export_project_technical_report
    (
        '''@router.get("/{project_id}/reports/{report_id}/export")
async def export_project_technical_report(
    project_id: str,
    report_id: str,
    format: str = Query("markdown", description="Export format: markdown, html, pdf"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a technical report in Markdown, HTML, or publication-ready PDF format.
    Streams attachment with Content-Disposition header.
    """
    file_bytes, media_type, filename = await project_service.export_project_report(
        project_id=project_id,
        report_id=report_id,
        format_type=format,
        db=db,
    )''',
        '''@router.get("/{project_id}/reports/{report_id}/export")
async def export_project_technical_report(
    project_id: str,
    report_id: str,
    format: str = Query("markdown", description="Export format: markdown, html, pdf"),
    current_user: User = Depends(get_current_user_or_default),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a technical report in Markdown, HTML, or publication-ready PDF format.
    Streams attachment with Content-Disposition header.
    """
    file_bytes, media_type, filename = await project_service.export_project_report(
        project_id=project_id,
        report_id=report_id,
        format_type=format,
        db=db,
        user_id=current_user.id,
    )'''
    ),
]

for idx, (old, new) in enumerate(replacements):
    old_c = old.replace('\r\n', '\n')
    new_c = new.replace('\r\n', '\n')
    if old_c not in content:
        print(f"FAILED TO MATCH: {old[:40]}...")
    else:
        content = content.replace(old_c, new_c, 1)

with open('backend/app/api/v1/projects.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated backend/app/api/v1/projects.py successfully!")
