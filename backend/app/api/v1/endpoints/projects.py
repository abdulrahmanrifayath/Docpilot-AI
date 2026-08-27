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
from backend.app.services.project_service import ProjectService
from backend.app.services.repository_service import RepositoryService
from backend.app.services.scan_service import ScanService
from backend.app.services.parse_service import ParseService

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
