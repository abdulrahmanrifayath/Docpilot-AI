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
)
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



