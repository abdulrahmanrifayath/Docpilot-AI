import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from git import Repo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    SecurityException,
    StorageException,
    GitCloneException,
)
from app.core.logging import logger
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectFileNode, ProjectFilesResponse


class ProjectService:
    async def create_project(self, payload: ProjectCreate, db: AsyncSession) -> Project:
        project_id = str(uuid.uuid4())
        project_dir = settings.PROJECTS_DIR / project_id

        project = Project(
            id=project_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            source_type=payload.source_type,
            source_url=payload.source_url.strip() if payload.source_url else None,
            repository_path=str(project_dir),
            status="CREATED",
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)
        logger.info(f"Created project '{project.name}' (ID: {project.id}) with status '{project.status}'")
        return project

    async def get_project(self, project_id: str, db: AsyncSession) -> Project:
        project = await db.get(Project, project_id)
        if not project:
            raise EntityNotFoundException("Project", project_id)
        return project

    async def list_projects(self, db: AsyncSession) -> List[Project]:
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    async def delete_project(self, project_id: str, db: AsyncSession) -> None:
        project = await self.get_project(project_id, db)

        # Clean up project filesystem workspace
        project_dir = Path(project.repository_path) if project.repository_path else settings.PROJECTS_DIR / project_id
        try:
            if project_dir.exists():
                shutil.rmtree(project_dir, ignore_errors=True)
                logger.info(f"Deleted filesystem directory for project {project_id}")
        except Exception as e:
            logger.warning(f"Error removing project files for {project_id}: {str(e)}")

        await db.delete(project)
        await db.commit()
        logger.info(f"Deleted project record {project_id}")

    async def upload_and_extract_zip(
        self,
        project_id: str,
        filename: str,
        file_bytes: bytes,
        db: AsyncSession,
    ) -> Project:
        project = await self.get_project(project_id, db)

        # 1. Validate file extension
        if not filename.lower().endswith(".zip"):
            raise ValidationException(
                message=f"Invalid file '{filename}'. Only ZIP archives (.zip) are accepted.",
                details={"filename": filename},
            )

        # 2. Validate ZIP magic bytes (PK\x03\x04 or PK\x05\x06)
        if len(file_bytes) < 4 or not file_bytes.startswith(b"PK"):
            raise ValidationException(
                message="File content is not a valid ZIP archive.",
                details={"filename": filename},
            )

        # 3. Enforce maximum file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValidationException(
                message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                details={"file_size_mb": round(len(file_bytes) / (1024 * 1024), 2), "max_size_mb": settings.MAX_UPLOAD_SIZE_MB},
            )

        project.status = "UPLOADING"
        await db.commit()

        target_dir = settings.PROJECTS_DIR / project_id / "source"
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        temp_zip_path = settings.UPLOAD_DIR / f"{project_id}_{filename}"

        try:
            temp_zip_path.write_bytes(file_bytes)

            with zipfile.ZipFile(temp_zip_path, "r") as zf:
                # 4. Prevent Zip-Slip / Path Traversal vulnerability
                abs_target_dir = os.path.abspath(target_dir)

                for member in zf.infolist():
                    # Resolve destination path
                    member_target = os.path.abspath(os.path.join(target_dir, member.filename))

                    # Verify that member_target stays within target_dir
                    if not member_target.startswith(abs_target_dir + os.sep) and member_target != abs_target_dir:
                        raise SecurityException(
                            message=f"Path traversal / zip-slip attack detected in archive member: '{member.filename}'",
                            details={"illegal_path": member.filename},
                        )

                    # Check if file is within an ignored directory (e.g. node_modules, .git)
                    path_parts = Path(member.filename).parts
                    if any(part in settings.IGNORED_DIRECTORIES for part in path_parts):
                        continue

                    # Extract safely
                    zf.extract(member, target_dir)

            # Check if there is a single top-level directory inside extraction
            extracted_items = [p for p in target_dir.iterdir() if p.name not in settings.IGNORED_DIRECTORIES]
            effective_path = target_dir
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                effective_path = extracted_items[0]

            project.repository_path = str(effective_path)
            project.source_type = "zip"
            project.status = "READY"
            project.error_message = None
            await db.commit()
            await db.refresh(project)

            logger.info(f"Successfully extracted ZIP for project {project_id} into {effective_path}")
            return project

        except (SecurityException, ValidationException):
            project.status = "FAILED"
            await db.commit()
            raise
        except Exception as e:
            project.status = "FAILED"
            project.error_message = str(e)
            await db.commit()
            logger.exception(f"Failed to process ZIP upload for project {project_id}: {str(e)}")
            raise StorageException(message=f"Failed to extract ZIP archive: {str(e)}")
        finally:
            if temp_zip_path.exists():
                temp_zip_path.unlink()

    async def clone_github_repo(
        self,
        project_id: str,
        source_url: Optional[str],
        db: AsyncSession,
    ) -> Project:
        project = await self.get_project(project_id, db)
        url_to_clone = (source_url or project.source_url or "").strip()

        # 1. Validate GitHub URL format
        if not url_to_clone:
            raise ValidationException(message="A GitHub repository URL is required for cloning.")

        github_pattern = re.compile(
            r"^https?://(www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$"
        )
        if not github_pattern.match(url_to_clone):
            raise ValidationException(
                message=f"Invalid GitHub repository URL: '{url_to_clone}'. Format must be https://github.com/owner/repository",
                details={"provided_url": url_to_clone},
            )

        project.status = "CLONING"
        project.source_url = url_to_clone
        project.source_type = "git"
        await db.commit()

        target_dir = settings.PROJECTS_DIR / project_id / "source"
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Cloning GitHub repository {url_to_clone} to {target_dir}")
            # Shallow clone depth=1 for fast and safe checkout without executing any code
            Repo.clone_from(url_to_clone, str(target_dir), depth=1)

            project.repository_path = str(target_dir)
            project.status = "READY"
            project.error_message = None
            await db.commit()
            await db.refresh(project)

            logger.info(f"Successfully cloned GitHub repo for project {project_id}")
            return project

        except Exception as e:
            project.status = "FAILED"
            project.error_message = str(e)
            await db.commit()
            logger.exception(f"Git clone failed for project {project_id}: {str(e)}")
            raise GitCloneException(
                message=f"Failed to clone repository from '{url_to_clone}': {str(e)}",
                details={"url": url_to_clone},
            )

    async def list_project_files(self, project_id: str, db: AsyncSession) -> ProjectFilesResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path)

        if not base_path.exists() or not base_path.is_dir():
            return ProjectFilesResponse(project_id=project_id, total_files=0, files=[])

        total_files = 0

        def build_tree(current_dir: Path) -> List[ProjectFileNode]:
            nonlocal total_files
            nodes: List[ProjectFileNode] = []

            try:
                for entry in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    # Skip ignored directories
                    if entry.name in settings.IGNORED_DIRECTORIES or entry.name.startswith("."):
                        continue

                    rel_path = entry.relative_to(base_path).as_posix()

                    if entry.is_dir():
                        children = build_tree(entry)
                        nodes.append(
                            ProjectFileNode(
                                name=entry.name,
                                path=rel_path,
                                type="directory",
                                children=children,
                            )
                        )
                    elif entry.is_file():
                        total_files += 1
                        nodes.append(
                            ProjectFileNode(
                                name=entry.name,
                                path=rel_path,
                                type="file",
                                size=entry.stat().st_size,
                            )
                        )
            except PermissionError:
                pass

            return nodes

        file_tree = build_tree(base_path)
        return ProjectFilesResponse(
            project_id=project_id,
            total_files=total_files,
            files=file_tree,
        )


project_service = ProjectService()
