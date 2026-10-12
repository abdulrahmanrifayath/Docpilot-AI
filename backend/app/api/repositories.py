import asyncio
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.database.session import get_db, AsyncSessionLocal
from app.models.repository import Repository
from app.schemas.repository import RepositoryResponse, PipelineProgress, RepositoryCreate
from app.services.pipeline_service import pipeline_service

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    """List all analyzed repositories."""
    result = await db.execute(select(Repository).order_by(Repository.created_at.desc()))
    return result.scalars().all()


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Get single repository by ID."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Delete repository and its associated resources."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Clean up files
    try:
        if Path(repo.local_path).exists():
            if Path(repo.local_path).is_file():
                Path(repo.local_path).unlink()
            else:
                shutil.rmtree(repo.local_path, ignore_errors=True)
    except Exception:
        pass

    await db.delete(repo)
    await db.commit()
    return None


@router.post("/upload", response_model=RepositoryResponse)
async def upload_repository_zip(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a ZIP file of a codebase for full analysis."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are currently supported for direct upload")

    repo_id = str(uuid.uuid4())
    repo_name = name or Path(file.filename).stem

    # Save uploaded file
    target_zip = settings.UPLOAD_DIR / f"{repo_id}_{file.filename}"
    with open(target_zip, "wb") as f:
        shutil.copyfileobj(file.file, f)

    repo = Repository(
        id=repo_id,
        name=repo_name,
        source_type="zip",
        local_path=str(target_zip),
        status="pending",
        current_step="Uploaded, queueing analysis pipeline...",
        progress_percent=0,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    # Launch pipeline in background task
    asyncio.create_task(pipeline_service.run_pipeline(repo_id, AsyncSessionLocal))

    return repo


@router.post("/clone", response_model=RepositoryResponse)
async def clone_repository_git(
    payload: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Provide a Git repository URL (GitHub/GitLab) for cloning and analysis."""
    if not payload.source_url:
        raise HTTPException(status_code=400, detail="source_url is required for cloning")

    repo_id = str(uuid.uuid4())
    repo_name = payload.name or payload.source_url.rstrip("/").split("/")[-1].replace(".git", "")

    target_dir = settings.UPLOAD_DIR / f"{repo_id}_{repo_name}"

    repo = Repository(
        id=repo_id,
        name=repo_name,
        source_type="git",
        source_url=payload.source_url,
        local_path=str(target_dir),
        status="pending",
        current_step="Queued for cloning and pipeline analysis...",
        progress_percent=0,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    # Launch pipeline in background task
    asyncio.create_task(pipeline_service.run_pipeline(repo_id, AsyncSessionLocal))

    return repo


@router.get("/{repository_id}/progress", response_model=PipelineProgress)
async def get_pipeline_progress(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Poll the real-time progress of the 11-stage analysis pipeline."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return PipelineProgress(
        repository_id=repo.id,
        status=repo.status,
        current_step=repo.current_step,
        progress_percent=repo.progress_percent,
        error_message=repo.error_message,
    )


@router.post("/{repository_id}/analyze", response_model=RepositoryResponse)
async def trigger_analysis(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Manually re-trigger the analysis pipeline for a repository."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.status = "pending"
    repo.current_step = "Re-starting analysis..."
    repo.progress_percent = 0
    await db.commit()
    await db.refresh(repo)

    asyncio.create_task(pipeline_service.run_pipeline(repository_id, AsyncSessionLocal))

    return repo
