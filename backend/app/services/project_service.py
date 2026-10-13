import base64
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote
from git import Repo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    SecurityException,
    StorageException,
    GitCloneException,
)
from app.core.logging import logger
from app.models.project import Project, CodeEntity, utc_now
from app.parsers.code_extractor import code_parsing_engine
from app.schemas.project import (
    ProjectCreate,
    ProjectFileNode,
    ProjectFilesResponse,
    ProjectStructureResponse,
    ProjectTechnologiesResponse,
    ProjectStatisticsResponse,
    ProjectScanResponse,
    ProjectParseResponse,
)
from app.services.repository_scanner import repository_scanner




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

            # Run initial scan for language & technology discovery
            try:
                scan_data = repository_scanner.scan_repository(effective_path)
                project.languages = scan_data["languages"]
                project.frameworks = scan_data["frameworks"]
                project.infrastructure = scan_data["infrastructure"]
                project.stats = {
                    "total_files": scan_data["total_files"],
                    "total_directories": scan_data["total_directories"],
                    "total_lines": scan_data["total_lines"],
                    "categories": scan_data["categories"],
                }
                project.structure = scan_data["tree"]
                project.last_analyzed_at = utc_now()
            except Exception as scan_err:
                logger.warning(f"Initial scan warning for {project_id}: {scan_err}")

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

            # Run initial scan for language & technology discovery
            try:
                scan_data = repository_scanner.scan_repository(target_dir)
                project.languages = scan_data["languages"]
                project.frameworks = scan_data["frameworks"]
                project.infrastructure = scan_data["infrastructure"]
                project.stats = {
                    "total_files": scan_data["total_files"],
                    "total_directories": scan_data["total_directories"],
                    "total_lines": scan_data["total_lines"],
                    "categories": scan_data["categories"],
                }
                project.structure = scan_data["tree"]
                project.last_analyzed_at = utc_now()
            except Exception as scan_err:
                logger.warning(f"Initial scan warning for {project_id}: {scan_err}")

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

    async def scan_project(self, project_id: str, db: AsyncSession) -> ProjectScanResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path)
        if not base_path.exists() or not base_path.is_dir():
            raise ValidationException(
                message="Project repository directory does not exist or has not been uploaded yet.",
                details={"repository_path": project.repository_path},
            )

        project.status = "ANALYZING"
        await db.commit()

        try:
            scan_data = repository_scanner.scan_repository(base_path)
            project.status = "ANALYZED"
            project.languages = scan_data["languages"]
            project.frameworks = scan_data["frameworks"]
            project.infrastructure = scan_data["infrastructure"]
            project.stats = {
                "total_files": scan_data["total_files"],
                "total_directories": scan_data["total_directories"],
                "total_lines": scan_data["total_lines"],
                "categories": scan_data["categories"],
            }
            project.structure = scan_data["tree"]
            project.last_analyzed_at = utc_now()
            project.error_message = None
            await db.commit()
            await db.refresh(project)

            logger.info(f"Scan complete for project {project_id}: {scan_data['total_files']} files, {scan_data['total_lines']} lines")
            return ProjectScanResponse(
                project_id=project.id,
                status=project.status,
                total_files=scan_data["total_files"],
                total_directories=scan_data["total_directories"],
                total_lines=scan_data["total_lines"],
                languages=scan_data["languages"],
                frameworks=scan_data["frameworks"],
                infrastructure=scan_data["infrastructure"],
                scanned_at=project.last_analyzed_at or utc_now(),
            )
        except Exception as e:
            project.status = "FAILED"
            project.error_message = f"Scan failed: {str(e)}"
            await db.commit()
            logger.exception(f"Error scanning project {project_id}: {str(e)}")
            raise StorageException(message=f"Failed to scan repository: {str(e)}")

    async def get_project_structure(self, project_id: str, db: AsyncSession) -> ProjectStructureResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if (not project.structure or not project.structure.get("children")) and base_path and base_path.exists():
            await self.scan_project(project_id, db)
            project = await self.get_project(project_id, db)

        tree_data = project.structure or {
            "name": project.name,
            "path": ".",
            "type": "directory",
            "children": [],
        }
        total_files = project.stats.get("total_files", 0) if project.stats else 0
        total_dirs = project.stats.get("total_directories", 0) if project.stats else 0

        return ProjectStructureResponse(
            project_id=project.id,
            total_files=total_files,
            total_directories=total_dirs,
            tree=tree_data,
        )

    async def get_project_technologies(self, project_id: str, db: AsyncSession) -> ProjectTechnologiesResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if not project.languages and base_path and base_path.exists():
            await self.scan_project(project_id, db)
            project = await self.get_project(project_id, db)

        return ProjectTechnologiesResponse(
            project_id=project.id,
            languages=project.languages or {},
            frameworks=project.frameworks or [],
            infrastructure=project.infrastructure or [],
        )

    async def get_project_statistics(self, project_id: str, db: AsyncSession) -> ProjectStatisticsResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if not project.stats and base_path and base_path.exists():
            await self.scan_project(project_id, db)
            project = await self.get_project(project_id, db)

        stats = project.stats or {}
        return ProjectStatisticsResponse(
            project_id=project.id,
            total_files=stats.get("total_files", 0),
            total_directories=stats.get("total_directories", 0),
            total_lines=stats.get("total_lines", 0),
            languages=project.languages or {},
            categories=stats.get("categories", {}),
            frameworks=project.frameworks or [],
            infrastructure=project.infrastructure or [],
        )

    async def parse_project_code(self, project_id: str, db: AsyncSession) -> ProjectParseResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if not base_path or not base_path.exists() or not base_path.is_dir():
            raise ValidationException(
                message="Project repository directory does not exist or has not been uploaded yet.",
                details={"repository_path": project.repository_path if project else None},
            )

        project.status = "PARSING"
        await db.commit()

        try:
            # 1. Clear any existing CodeEntity records for this project
            await db.execute(delete(CodeEntity).where(CodeEntity.project_id == project_id))

            # 2. Walk directory and parse all supported files (.py, .js, .jsx, .ts, .tsx, etc.)
            parsed_files_count = 0
            code_entities: List[CodeEntity] = []
            breakdown: Dict[str, int] = {
                "MODULE": 0,
                "CLASS": 0,
                "FUNCTION": 0,
                "METHOD": 0,
                "INTERFACE": 0,
                "COMPONENT": 0,
            }

            for root, dirs, files in os.walk(base_path):
                # Filter out ignored directories in-place
                dirs[:] = [
                    d for d in dirs
                    if d not in settings.IGNORED_DIRECTORIES and not d.startswith(".")
                ]

                for file_name in sorted(files):
                    file_path = Path(root) / file_name
                    if not code_parsing_engine.is_supported_file(str(file_path)):
                        continue

                    # Skip ignored or oversized files
                    try:
                        max_file_size = getattr(settings, "MAX_FILE_SIZE_BYTES", 2 * 1024 * 1024)
                        if file_path.stat().st_size > max_file_size:
                            continue
                    except OSError:
                        continue


                    rel_path = file_path.relative_to(base_path).as_posix()

                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        extracted = code_parsing_engine.parse_file(rel_path, content)
                        parsed_files_count += 1

                        for item in extracted:
                            entity_id = str(uuid.uuid4())
                            entity = CodeEntity(
                                id=entity_id,
                                project_id=project_id,
                                file_path=rel_path,
                                name=item.name,
                                entity_type=item.entity_type,
                                start_line=item.start_line,
                                end_line=item.end_line,
                                signature=item.signature,
                                parent_entity=item.parent_entity,
                                metadata_json=item.metadata or {},
                            )
                            code_entities.append(entity)
                            breakdown[item.entity_type] = breakdown.get(item.entity_type, 0) + 1
                    except Exception as fe:
                        logger.warning(f"Error parsing file {rel_path} in project {project_id}: {fe}")

            if code_entities:
                db.add_all(code_entities)

            project.status = "PARSED"
            project.error_message = None
            await db.commit()
            await db.refresh(project)

            logger.info(
                f"Parsed {parsed_files_count} files for project {project_id}, "
                f"extracted {len(code_entities)} entities: {breakdown}"
            )

            return ProjectParseResponse(
                project_id=project.id,
                status=project.status,
                total_files_parsed=parsed_files_count,
                total_entities_extracted=len(code_entities),
                entity_breakdown=breakdown,
                parsed_at=utc_now(),
            )
        except Exception as e:
            project.status = "FAILED"
            project.error_message = f"Code parsing failed: {str(e)}"
            await db.commit()
            logger.exception(f"Code parsing failed for project {project_id}: {str(e)}")
            raise StorageException(message=f"Failed to parse source code: {str(e)}")

    async def get_project_entities(
        self,
        project_id: str,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[CodeEntity]:
        await self.get_project(project_id, db)
        query = select(CodeEntity).where(CodeEntity.project_id == project_id)

        if entity_type:
            query = query.where(CodeEntity.entity_type == entity_type.upper())
        if file_path:
            norm_path = file_path.replace("\\", "/").strip("/")
            query = query.where(
                (CodeEntity.file_path == norm_path) |
                (CodeEntity.file_path == file_path) |
                CodeEntity.file_path.endswith("/" + norm_path)
            )
        if name:
            query = query.where(CodeEntity.name.ilike(f"%{name}%"))

        query = query.order_by(CodeEntity.file_path.asc(), CodeEntity.start_line.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_entity_by_id(
        self,
        project_id: str,
        entity_id: str,
        db: AsyncSession,
    ) -> CodeEntity:
        await self.get_project(project_id, db)
        query = select(CodeEntity).where(
            CodeEntity.project_id == project_id,
            CodeEntity.id == entity_id,
        )
        result = await db.execute(query)
        entity = result.scalar_one_or_none()
        if not entity:
            raise EntityNotFoundException("CodeEntity", entity_id)
        return entity

    async def get_file_entities(
        self,
        project_id: str,
        file_id: str,
        db: AsyncSession,
    ) -> List[CodeEntity]:
        await self.get_project(project_id, db)

        # Decode file_id (supports raw path, URL-encoded path, or Base64-encoded path)
        candidates = [file_id]
        try:
            unquoted = unquote(file_id)
            if unquoted not in candidates:
                candidates.append(unquoted)
        except Exception:
            pass

        try:
            padded = file_id + "=" * (-len(file_id) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            if decoded and decoded not in candidates:
                candidates.append(decoded)
        except Exception:
            pass

        norm_candidates = set()
        for c in candidates:
            c_norm = c.replace("\\", "/").strip("/")
            norm_candidates.add(c_norm)
            norm_candidates.add(Path(c).name)

        query = select(CodeEntity).where(CodeEntity.project_id == project_id)
        result = await db.execute(query)
        all_entities = list(result.scalars().all())

        matched = [
            e for e in all_entities
            if e.file_path in norm_candidates
            or any(e.file_path.endswith("/" + c) or e.file_path == c for c in norm_candidates)
            or any(Path(e.file_path).name == c for c in norm_candidates)
        ]
        matched.sort(key=lambda e: (e.file_path, e.start_line))
        return matched


project_service = ProjectService()

