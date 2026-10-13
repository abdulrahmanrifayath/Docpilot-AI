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
from app.models.project import (
    Project,
    CodeEntity,
    DependencyNode,
    DependencyRelationship,
    APIEndpoint,
    DatabaseModel,
    DatabaseField,
    DatabaseRelationship,
    Diagram,
    utc_now,
)
from app.parsers.code_extractor import code_parsing_engine
from app.services.dependency_analyzer import dependency_analyzer
from app.services.api_discovery import AutomaticAPIDiscoveryService
from app.services.database_analyzer import database_structure_analyzer
from app.services.knowledge_graph_service import knowledge_graph_service
from app.schemas.project import (
    ProjectCreate,
    ProjectFileNode,
    ProjectFilesResponse,
    ProjectStructureResponse,
    ProjectTechnologiesResponse,
    ProjectStatisticsResponse,
    ProjectScanResponse,
    ProjectParseResponse,
    DependencyNodeResponse,
    DependencyRelationshipResponse,
    DependencyGraphResponse,
    DependencyAnalysisResponse,
    EntityDependenciesResponse,
    APIEndpointResponse,
    APIEndpointDetailResponse,
    APIAnalysisResponse,
    DatabaseFieldResponse,
    DatabaseRelationshipResponse,
    DatabaseModelResponse,
    DatabaseAnalysisResponse,
    DatabaseDiagramResponse,
    KnowledgeBuildResponse,
    KnowledgeGraphResponse,
    KnowledgeEntityDetailResponse,
    DocumentResponse,
    DocumentGenerateResponse,
)
from app.services.documentation_service import documentation_service
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


    async def analyze_dependencies(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> DependencyAnalysisResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if not base_path or not base_path.exists() or not base_path.is_dir():
            raise ValidationException(
                message="Project repository directory does not exist or has not been uploaded yet.",
                details={"repository_path": project.repository_path if project else None},
            )

        # 1. Ensure code entities are extracted first
        res_ents = await db.execute(select(CodeEntity).where(CodeEntity.project_id == project_id))
        code_entities = list(res_ents.scalars().all())
        if not code_entities:
            await self.parse_project_code(project_id, db)
            res_ents = await db.execute(select(CodeEntity).where(CodeEntity.project_id == project_id))
            code_entities = list(res_ents.scalars().all())

        # 2. Run StaticDependencyAnalyzer
        nodes, relationships = dependency_analyzer.analyze_project(
            project_id=project_id,
            repository_path=base_path,
            code_entities=code_entities,
        )

        # 3. Clear existing dependency records for this project
        await db.execute(delete(DependencyRelationship).where(DependencyRelationship.project_id == project_id))
        await db.execute(delete(DependencyNode).where(DependencyNode.project_id == project_id))

        # 4. Save new nodes & relationships
        if nodes:
            db.add_all(nodes)
        if relationships:
            db.add_all(relationships)

        await db.commit()

        # 5. Compile breakdown stats
        breakdown: Dict[str, int] = {
            "IMPORTS": 0,
            "CALLS": 0,
            "EXTENDS": 0,
            "IMPLEMENTS": 0,
            "DEPENDS_ON": 0,
            "USES": 0,
        }
        internal_count = 0
        external_count = 0
        for r in relationships:
            breakdown[r.relationship_type] = breakdown.get(r.relationship_type, 0) + 1
            if r.is_external:
                external_count += 1
            else:
                internal_count += 1

        logger.info(
            f"Dependency analysis complete for project {project_id}: "
            f"{len(nodes)} nodes, {len(relationships)} edges ({internal_count} internal, {external_count} external)"
        )

        return DependencyAnalysisResponse(
            project_id=project.id,
            status="ANALYZED",
            total_nodes=len(nodes),
            total_edges=len(relationships),
            internal_dependencies=internal_count,
            external_dependencies=external_count,
            breakdown=breakdown,
            analyzed_at=utc_now(),
        )

    async def get_dependencies(
        self,
        project_id: str,
        db: AsyncSession,
        relationship_type: Optional[str] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
        is_external: Optional[bool] = None,
        min_confidence: Optional[float] = None,
    ) -> List[DependencyRelationship]:
        await self.get_project(project_id, db)
        query = select(DependencyRelationship).where(DependencyRelationship.project_id == project_id)

        if relationship_type:
            query = query.where(DependencyRelationship.relationship_type == relationship_type.upper())
        if source:
            query = query.where(DependencyRelationship.source.ilike(f"%{source}%"))
        if target:
            query = query.where(DependencyRelationship.target.ilike(f"%{target}%"))
        if is_external is not None:
            query = query.where(DependencyRelationship.is_external == is_external)
        if min_confidence is not None:
            query = query.where(DependencyRelationship.confidence >= min_confidence)

        query = query.order_by(DependencyRelationship.confidence.desc(), DependencyRelationship.source.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_dependency_graph(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> DependencyGraphResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None

        # Fetch existing nodes and relationships
        nodes_res = await db.execute(select(DependencyNode).where(DependencyNode.project_id == project_id))
        nodes = list(nodes_res.scalars().all())

        edges_res = await db.execute(select(DependencyRelationship).where(DependencyRelationship.project_id == project_id))
        edges = list(edges_res.scalars().all())

        # If empty and project files exist, run analysis automatically
        if (not nodes or not edges) and base_path and base_path.exists():
            await self.analyze_dependencies(project_id, db)
            nodes_res = await db.execute(select(DependencyNode).where(DependencyNode.project_id == project_id))
            nodes = list(nodes_res.scalars().all())
            edges_res = await db.execute(select(DependencyRelationship).where(DependencyRelationship.project_id == project_id))
            edges = list(edges_res.scalars().all())

        node_types: Dict[str, int] = {}
        for n in nodes:
            node_types[n.node_type] = node_types.get(n.node_type, 0) + 1

        rel_types: Dict[str, int] = {}
        for e in edges:
            rel_types[e.relationship_type] = rel_types.get(e.relationship_type, 0) + 1

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": node_types,
            "relationship_types": rel_types,
        }

        return DependencyGraphResponse(
            project_id=project.id,
            nodes=[DependencyNodeResponse.model_validate(n) for n in nodes],
            edges=[DependencyRelationshipResponse.model_validate(e) for e in edges],
            stats=stats,
        )

    async def get_entity_dependencies(
        self,
        project_id: str,
        entity_id: str,
        db: AsyncSession,
    ) -> EntityDependenciesResponse:
        await self.get_project(project_id, db)

        # 1. Find matching node
        node_query = select(DependencyNode).where(
            DependencyNode.project_id == project_id,
            (DependencyNode.id == entity_id) |
            (DependencyNode.name == entity_id) |
            (DependencyNode.entity_id == entity_id)
        )
        node_res = await db.execute(node_query)
        target_node = node_res.scalar_one_or_none()

        entity_name = target_node.name if target_node else entity_id

        # 2. Find incoming edges (edges where target == entity_name or target == entity_id)
        incoming_query = select(DependencyRelationship).where(
            DependencyRelationship.project_id == project_id,
            (DependencyRelationship.target == entity_name) |
            (DependencyRelationship.target == entity_id)
        )
        inc_res = await db.execute(incoming_query)
        incoming_edges = list(inc_res.scalars().all())

        # 3. Find outgoing edges (edges where source == entity_name or source == entity_id)
        outgoing_query = select(DependencyRelationship).where(
            DependencyRelationship.project_id == project_id,
            (DependencyRelationship.source == entity_name) |
            (DependencyRelationship.source == entity_id)
        )
        out_res = await db.execute(outgoing_query)
        outgoing_edges = list(out_res.scalars().all())

        # 4. Find neighbor nodes
        neighbor_names = set()
        for e in incoming_edges:
            neighbor_names.add(e.source)
        for e in outgoing_edges:
            neighbor_names.add(e.target)

        neighbors: List[DependencyNode] = []
        if neighbor_names:
            neighbors_res = await db.execute(
                select(DependencyNode).where(
                    DependencyNode.project_id == project_id,
                    (DependencyNode.name.in_(neighbor_names) | DependencyNode.id.in_(neighbor_names))
                )
            )
            neighbors = list(neighbors_res.scalars().all())

        return EntityDependenciesResponse(
            project_id=project_id,
            entity_id=entity_id,
            entity_name=entity_name,
            node=DependencyNodeResponse.model_validate(target_node) if target_node else None,
            incoming=[DependencyRelationshipResponse.model_validate(e) for e in incoming_edges],
            outgoing=[DependencyRelationshipResponse.model_validate(e) for e in outgoing_edges],
            neighbors=[DependencyNodeResponse.model_validate(n) for n in neighbors],
        )

    # =========================================================================
    # PHASE 6: AUTOMATIC API DISCOVERY
    # =========================================================================

    async def analyze_apis(self, project_id: str, db: AsyncSession) -> APIAnalysisResponse:
        project = await self.get_project(project_id, db)
        base_path = Path(project.repository_path) if project.repository_path else None
        if not base_path or not base_path.exists() or not base_path.is_dir():
            raise ValidationException(
                message="Project repository directory does not exist or has not been uploaded yet.",
                details={"repository_path": project.repository_path if project else None},
            )

        discoverer = AutomaticAPIDiscoveryService()
        discovered_eps = discoverer.discover_apis(str(base_path))

        # Clear existing api_endpoints for this project
        await db.execute(delete(APIEndpoint).where(APIEndpoint.project_id == project_id))

        method_breakdown: Dict[str, int] = {}
        framework_breakdown: Dict[str, int] = {}
        auth_count = 0
        public_count = 0

        created_endpoints: List[APIEndpoint] = []
        for ep in discovered_eps:
            ep_id = str(uuid.uuid4())
            method = ep["method"].upper()
            method_breakdown[method] = method_breakdown.get(method, 0) + 1

            fw = ep.get("metadata", {}).get("framework", "FastAPI")
            framework_breakdown[fw] = framework_breakdown.get(fw, 0) + 1

            is_auth = bool(ep.get("authentication_required", False))
            if is_auth:
                auth_count += 1
            else:
                public_count += 1

            endpoint_obj = APIEndpoint(
                id=ep_id,
                project_id=project_id,
                method=method,
                path=ep["path"],
                handler_name=ep["handler_name"],
                file_path=ep["file_path"],
                request_schema=ep.get("request_schema", {}),
                response_schema=ep.get("response_schema", {}),
                authentication_required=is_auth,
                tags=ep.get("tags", []),
                metadata_json=ep.get("metadata", {}),
            )
            db.add(endpoint_obj)
            created_endpoints.append(endpoint_obj)

        project.last_analyzed_at = utc_now()
        await db.commit()

        logger.info(
            f"API Discovery for project {project_id}: found {len(created_endpoints)} endpoints "
            f"({auth_count} authenticated, {public_count} public)"
        )

        return APIAnalysisResponse(
            project_id=project_id,
            status="ANALYZED",
            total_endpoints=len(created_endpoints),
            authenticated_endpoints=auth_count,
            public_endpoints=public_count,
            method_breakdown=method_breakdown,
            framework_breakdown=framework_breakdown,
            endpoints=[APIEndpointResponse.model_validate(ep) for ep in created_endpoints],
            analyzed_at=utc_now(),
        )

    async def get_apis(
        self,
        project_id: str,
        db: AsyncSession,
        method: Optional[str] = None,
        tag: Optional[str] = None,
        auth_required: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[APIEndpoint]:
        await self.get_project(project_id, db)
        query = select(APIEndpoint).where(APIEndpoint.project_id == project_id)

        if method:
            query = query.where(APIEndpoint.method == method.upper())
        if auth_required is not None:
            query = query.where(APIEndpoint.authentication_required == auth_required)
        if search:
            query = query.where(
                (APIEndpoint.path.ilike(f"%{search}%")) |
                (APIEndpoint.handler_name.ilike(f"%{search}%")) |
                (APIEndpoint.file_path.ilike(f"%{search}%"))
            )

        query = query.order_by(APIEndpoint.path.asc(), APIEndpoint.method.asc())
        result = await db.execute(query)
        endpoints = list(result.scalars().all())

        if tag:
            tag_lower = tag.lower()
            endpoints = [
                ep for ep in endpoints
                if any(t.lower() == tag_lower for t in (ep.tags or []))
            ]

        return endpoints

    async def get_api_endpoint(
        self,
        project_id: str,
        api_id: str,
        db: AsyncSession,
    ) -> APIEndpointDetailResponse:
        await self.get_project(project_id, db)

        # Look up by id or handler_name
        query = select(APIEndpoint).where(
            APIEndpoint.project_id == project_id,
            (APIEndpoint.id == api_id) | (APIEndpoint.handler_name == api_id)
        )
        res = await db.execute(query)
        endpoint = res.scalars().first()
        if not endpoint:
            raise EntityNotFoundException("APIEndpoint", api_id)

        # Cross-reference related components (services, models, entities)
        related_components: List[Dict[str, Any]] = []
        meta = endpoint.metadata_json or {}
        raw_components = meta.get("related_components", [])

        # Check CodeEntity and DependencyNode matches
        candidate_names = set(raw_components)
        candidate_names.add(endpoint.handler_name)
        if endpoint.request_schema and endpoint.request_schema.get("body_model"):
            candidate_names.add(endpoint.request_schema["body_model"])
        if endpoint.response_schema and endpoint.response_schema.get("model"):
            candidate_names.add(endpoint.response_schema["model"])

        if candidate_names:
            node_res = await db.execute(
                select(DependencyNode).where(
                    DependencyNode.project_id == project_id,
                    DependencyNode.name.in_(candidate_names)
                )
            )
            for node in node_res.scalars().all():
                related_components.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "file_path": node.file_path,
                    "is_external": node.is_external,
                })

            entity_res = await db.execute(
                select(CodeEntity).where(
                    CodeEntity.project_id == project_id,
                    CodeEntity.name.in_(candidate_names)
                )
            )
            seen_names = {rc["name"] for rc in related_components}
            for ent in entity_res.scalars().all():
                if ent.name not in seen_names:
                    related_components.append({
                        "id": ent.id,
                        "name": ent.name,
                        "type": ent.entity_type.lower(),
                        "file_path": ent.file_path,
                        "is_external": False,
                    })

        return APIEndpointDetailResponse(
            id=endpoint.id,
            project_id=endpoint.project_id,
            method=endpoint.method,
            path=endpoint.path,
            handler_name=endpoint.handler_name,
            file_path=endpoint.file_path,
            request_schema=endpoint.request_schema or {},
            response_schema=endpoint.response_schema or {},
            authentication_required=endpoint.authentication_required,
            tags=endpoint.tags or [],
            metadata=endpoint.metadata_json or {},
            created_at=endpoint.created_at,
            related_components=related_components,
        )

    async def analyze_database(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> DatabaseAnalysisResponse:
        await self.get_project(project_id, db)
        project_dir = settings.PROJECTS_DIR / project_id

        # 1. Run static database structure analysis (no SQL execution)
        analysis = database_structure_analyzer.analyze_repository(str(project_dir))

        # 2. Clear previous database models & relationships for this project
        await db.execute(delete(DatabaseRelationship).where(DatabaseRelationship.project_id == project_id))
        await db.execute(delete(DatabaseModel).where(DatabaseModel.project_id == project_id))
        await db.flush()

        # 3. Insert models & fields
        stored_models: List[DatabaseModel] = []
        for m_data in analysis["models"]:
            model_id = str(uuid.uuid4())
            db_model = DatabaseModel(
                id=model_id,
                project_id=project_id,
                name=m_data["name"],
                table_name=m_data["table_name"],
                file_path=m_data["file_path"],
                orm_type=m_data.get("orm_type", "SQLAlchemy"),
                start_line=m_data.get("start_line", 1),
                metadata_json=m_data.get("metadata", {}),
            )
            for f_data in m_data.get("fields", []):
                field_id = str(uuid.uuid4())
                db_field = DatabaseField(
                    id=field_id,
                    model_id=model_id,
                    name=f_data["name"],
                    data_type=f_data.get("data_type", "String"),
                    is_primary_key=f_data.get("is_primary_key", False),
                    is_foreign_key=f_data.get("is_foreign_key", False),
                    foreign_key_target=f_data.get("foreign_key_target"),
                    is_nullable=f_data.get("is_nullable", True),
                    default_value=f_data.get("default_value"),
                    metadata_json=f_data.get("metadata", {}),
                )
                db_model.fields.append(db_field)

            db.add(db_model)
            stored_models.append(db_model)

        # 4. Insert relationships
        stored_relationships: List[DatabaseRelationship] = []
        for r_data in analysis["relationships"]:
            rel_id = str(uuid.uuid4())
            db_rel = DatabaseRelationship(
                id=rel_id,
                project_id=project_id,
                source_model=r_data["source_model"],
                target_model=r_data["target_model"],
                relationship_type=r_data["relationship_type"],
                foreign_key_field=r_data.get("foreign_key_field"),
                back_populates=r_data.get("back_populates"),
                secondary_table=r_data.get("secondary_table"),
                description=r_data.get("description"),
                metadata_json=r_data.get("metadata", {}),
            )
            db.add(db_rel)
            stored_relationships.append(db_rel)

        # 5. Generate and store Mermaid ER diagram in Diagram table
        mermaid_code = database_structure_analyzer.generate_mermaid_er(
            analysis["models"],
            analysis["relationships"],
        )

        # Upsert ER diagram in diagrams table
        diag_query = select(Diagram).where(
            Diagram.project_id == project_id,
            Diagram.diagram_type == "er"
        )
        diag_res = await db.execute(diag_query)
        diagram_rec = diag_res.scalars().first()
        if diagram_rec:
            diagram_rec.mermaid_code = mermaid_code
            diagram_rec.title = "Database Entity Relationship Diagram"
            diagram_rec.updated_at = utc_now()
        else:
            new_diag = Diagram(
                id=str(uuid.uuid4()),
                project_id=project_id,
                diagram_type="er",
                title="Database Entity Relationship Diagram",
                mermaid_code=mermaid_code,
            )
            db.add(new_diag)

        await db.commit()

        # Re-fetch models with fields
        query_models = select(DatabaseModel).where(DatabaseModel.project_id == project_id).order_by(DatabaseModel.name.asc())
        m_result = await db.execute(query_models)
        final_models = list(m_result.scalars().all())

        query_rels = select(DatabaseRelationship).where(DatabaseRelationship.project_id == project_id).order_by(DatabaseRelationship.source_model.asc())
        r_result = await db.execute(query_rels)
        final_rels = list(r_result.scalars().all())

        total_fields = sum(len(m.fields) for m in final_models)

        logger.info(
            f"Database analysis for project {project_id}: found {len(final_models)} models, "
            f"{total_fields} fields, {len(final_rels)} relationships"
        )

        return DatabaseAnalysisResponse(
            project_id=project_id,
            status="ANALYZED",
            total_models=len(final_models),
            total_fields=total_fields,
            total_relationships=len(final_rels),
            orm_breakdown=analysis.get("orm_breakdown", {}),
            models=[DatabaseModelResponse.model_validate(m) for m in final_models],
            relationships=[DatabaseRelationshipResponse.model_validate(r) for r in final_rels],
            analyzed_at=utc_now(),
        )

    async def get_database_models(
        self,
        project_id: str,
        db: AsyncSession,
        orm_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[DatabaseModel]:
        await self.get_project(project_id, db)
        query = select(DatabaseModel).where(DatabaseModel.project_id == project_id)

        if orm_type:
            query = query.where(DatabaseModel.orm_type.ilike(f"%{orm_type}%"))
        if search:
            query = query.where(
                (DatabaseModel.name.ilike(f"%{search}%")) |
                (DatabaseModel.table_name.ilike(f"%{search}%")) |
                (DatabaseModel.file_path.ilike(f"%{search}%"))
            )

        query = query.order_by(DatabaseModel.name.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_database_relationships(
        self,
        project_id: str,
        db: AsyncSession,
        model_name: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> List[DatabaseRelationship]:
        await self.get_project(project_id, db)
        query = select(DatabaseRelationship).where(DatabaseRelationship.project_id == project_id)

        if model_name:
            query = query.where(
                (DatabaseRelationship.source_model == model_name) |
                (DatabaseRelationship.target_model == model_name)
            )
        if relationship_type:
            query = query.where(DatabaseRelationship.relationship_type == relationship_type.upper())

        query = query.order_by(DatabaseRelationship.source_model.asc(), DatabaseRelationship.target_model.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_database_diagram(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> DatabaseDiagramResponse:
        await self.get_project(project_id, db)

        # Check existing stored models & relationships
        query_models = select(DatabaseModel).where(DatabaseModel.project_id == project_id).order_by(DatabaseModel.name.asc())
        m_result = await db.execute(query_models)
        models = list(m_result.scalars().all())

        query_rels = select(DatabaseRelationship).where(DatabaseRelationship.project_id == project_id).order_by(DatabaseRelationship.source_model.asc())
        r_result = await db.execute(query_rels)
        relationships = list(r_result.scalars().all())

        if models:
            models_dict = [
                {
                    "name": m.name,
                    "table_name": m.table_name,
                    "fields": [
                        {
                            "name": f.name,
                            "data_type": f.data_type,
                            "is_primary_key": f.is_primary_key,
                            "is_foreign_key": f.is_foreign_key,
                        }
                        for f in m.fields
                    ],
                }
                for m in models
            ]
            rels_dict = [
                {
                    "source_model": r.source_model,
                    "target_model": r.target_model,
                    "relationship_type": r.relationship_type,
                    "description": r.description,
                    "back_populates": r.back_populates,
                }
                for r in relationships
            ]
            mermaid_code = database_structure_analyzer.generate_mermaid_er(models_dict, rels_dict)
            total_m = len(models)
            total_r = len(relationships)
        else:
            # Fallback: check if an ER Diagram exists in diagrams table
            diag_query = select(Diagram).where(Diagram.project_id == project_id, Diagram.diagram_type == "er")
            diag_res = await db.execute(diag_query)
            stored_diag = diag_res.scalars().first()
            if stored_diag and stored_diag.mermaid_code:
                mermaid_code = stored_diag.mermaid_code
                total_m = len(models)
                total_r = len(relationships)
            else:
                # If neither exists, generate from project files on the fly
                project_dir = settings.PROJECTS_DIR / project_id
                analysis = database_structure_analyzer.analyze_repository(str(project_dir))
                mermaid_code = database_structure_analyzer.generate_mermaid_er(
                    analysis["models"],
                    analysis["relationships"],
                )
                total_m = len(analysis["models"])
                total_r = len(analysis["relationships"])

        return DatabaseDiagramResponse(
            project_id=project_id,
            mermaid_code=mermaid_code,
            total_models=total_m,
            total_relationships=total_r,
        )

    # =========================================================================
    # PHASE 8: UNIFIED PROJECT KNOWLEDGE GRAPH
    # =========================================================================

    async def build_knowledge_graph(
        self,
        project_id: str,
        db: AsyncSession,
    ) -> KnowledgeBuildResponse:
        return await knowledge_graph_service.build_knowledge_graph(project_id, db)

    async def get_knowledge_graph(
        self,
        project_id: str,
        db: AsyncSession,
        node_types: Optional[List[str]] = None,
        search: Optional[str] = None,
        focus_id: Optional[str] = None,
        depth: int = 2,
        limit: int = 150,
        offset: int = 0,
    ) -> KnowledgeGraphResponse:
        return await knowledge_graph_service.get_knowledge_graph(
            project_id=project_id,
            db=db,
            node_types=node_types,
            search=search,
            focus_id=focus_id,
            depth=depth,
            limit=limit,
            offset=offset,
        )

    async def get_entity_knowledge(
        self,
        project_id: str,
        entity_id: str,
        db: AsyncSession,
    ) -> KnowledgeEntityDetailResponse:
        return await knowledge_graph_service.get_entity_knowledge(
            project_id=project_id,
            entity_id=entity_id,
            db=db,
        )

    # -------------------------------------------------------------------------
    # Phase 9: AI Documentation Generation Engine
    # -------------------------------------------------------------------------
    async def generate_documentation(
        self,
        project_id: str,
        db: AsyncSession,
        document_types: Optional[List[str]] = None,
        target_path: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> DocumentGenerateResponse:
        return await documentation_service.generate_documentation(
            project_id=project_id,
            db=db,
            document_types=document_types,
            target_path=target_path,
            target_entity_id=target_entity_id,
            force_regenerate=force_regenerate,
        )

    async def get_documents(
        self,
        project_id: str,
        db: AsyncSession,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[DocumentResponse]:
        return await documentation_service.get_documents(
            project_id=project_id,
            db=db,
            document_type=document_type,
            search=search,
        )

    async def get_document_by_id(
        self,
        project_id: str,
        document_id: str,
        db: AsyncSession,
    ) -> DocumentResponse:
        return await documentation_service.get_document_by_id(
            project_id=project_id,
            document_id=document_id,
            db=db,
        )

    async def regenerate_document(
        self,
        project_id: str,
        document_id: str,
        db: AsyncSession,
    ) -> DocumentResponse:
        return await documentation_service.regenerate_document(
            project_id=project_id,
            document_id=document_id,
            db=db,
        )


project_service = ProjectService()



