from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectCloneRequest,
    ProjectResponse,
    ProjectFilesResponse,
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
