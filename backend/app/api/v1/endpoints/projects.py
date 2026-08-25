from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.app.services.project_service import ProjectService

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
