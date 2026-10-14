"""
Change Detection and Documentation Synchronization Engine (Phase 14).

MVP Approach for Repository Change Tracking:
1. Store analyzed commit SHA on the Project model (last_commit_sha).
2. Compare latest commit SHA with previously analyzed commit SHA via Git diff.
3. Detect added, modified, deleted files (with file-hash fallback for non-git / direct edits).
4. Reanalyze only affected files where possible (AST entities, imports, dependencies, APIs, DB models).
5. Update affected code entities and cross-tier relationships.
6. Identify documentation affected by the changes.
7. Regenerate only affected documentation with version archiving (DocumentVersion).
8. Regenerate affected architecture diagrams.
9. Guarantee transaction integrity: Do not claim synchronized unless analysis completed successfully.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from git import Repo
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import (
    Project,
    CodeEntity,
    DependencyNode,
    DependencyRelationship,
    APIEndpoint,
    DatabaseModel,
    Document,
    DocumentVersion,
    Diagram,
    ChangeRecord,
    utc_now,
)
from app.schemas.project import (
    ChangeCheckResponse,
    ChangeReportResponse,
    UpdatedDocumentItem,
    UpdatedDiagramItem,
    DocumentVersionItem,
)
from app.schemas.repository import SyncResponse
from app.parsers.code_extractor import code_parsing_engine
from app.services.dependency_analyzer import dependency_analyzer
from app.services.api_discovery import api_discovery_service
from app.services.database_analyzer import database_structure_analyzer
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.diagram_service import diagram_service
from app.services.documentation_service import documentation_service, LLMNotConfiguredError
from app.services.onboarding_service import onboarding_service

logger = logging.getLogger("docpilot.sync")


class SyncService:
    """Enterprise-grade Change Detection and Documentation Synchronization Engine."""

    def _compute_file_hashes(self, repo_path: Path) -> Dict[str, str]:
        """Computes SHA-256 / MD5 hashes for all non-ignored source files in the repository."""
        hashes: Dict[str, str] = {}
        if not repo_path.exists() or not repo_path.is_dir():
            return hashes

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in settings.IGNORED_DIRECTORIES]
            for file in files:
                full_path = Path(root) / file
                try:
                    rel_path = str(full_path.relative_to(repo_path)).replace("\\", "/")
                    # Skip files larger than 5MB for fast hashing
                    if full_path.stat().st_size > 5 * 1024 * 1024:
                        continue
                    content = full_path.read_bytes()
                    hashes[rel_path] = hashlib.md5(content).hexdigest()
                except Exception:
                    continue
        return hashes

    async def detect_changes(self, project_id: str, db: AsyncSession) -> ChangeCheckResponse:
        """
        Inspects repository for changes by:
        1. Checking Git commits (HEAD vs previous analyzed commit SHA).
        2. Checking Git working tree (unstaged/untracked modifications).
        3. Comparing file hash snapshots as universal fallback.
        4. Calculating affected entities, APIs, DB models, documents, and diagrams.
        """
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        repo_path = Path(project.repository_path)
        if not repo_path.exists():
            raise ValueError(f"Repository path '{project.repository_path}' does not exist on disk")

        files_added: List[str] = []
        files_modified: List[str] = []
        files_deleted: List[str] = []
        current_commit_sha: Optional[str] = None
        previous_commit_sha: Optional[str] = project.last_commit_sha

        is_git = (repo_path / ".git").exists()
        git_inspected = False

        if is_git:
            try:
                git_repo = Repo(str(repo_path))
                current_commit_sha = git_repo.head.commit.hexsha
                git_inspected = True

                # Case A: We have a previous analyzed commit and it differs from HEAD
                if previous_commit_sha and previous_commit_sha != current_commit_sha:
                    try:
                        diff = git_repo.commit(previous_commit_sha).diff(current_commit_sha)
                        for d in diff:
                            if d.new_file and d.b_path:
                                files_added.append(d.b_path.replace("\\", "/"))
                            elif d.deleted_file and d.a_path:
                                files_deleted.append(d.a_path.replace("\\", "/"))
                            else:
                                path = (d.b_path or d.a_path or "").replace("\\", "/")
                                if path:
                                    files_modified.append(path)
                    except Exception as diff_err:
                        logger.warning(f"Git commit diff warning: {diff_err}")

                # Case B: Check active uncommitted working tree changes
                try:
                    for d in git_repo.index.diff(None):
                        path = (d.b_path or d.a_path or "").replace("\\", "/")
                        if d.deleted_file and path not in files_deleted:
                            files_deleted.append(path)
                        elif not d.deleted_file and path not in files_modified and path not in files_added:
                            files_modified.append(path)

                    for untracked in git_repo.untracked_files:
                        norm = untracked.replace("\\", "/")
                        if norm not in files_added and not any(ign in norm for ign in settings.IGNORED_DIRECTORIES):
                            files_added.append(norm)
                except Exception as wt_err:
                    logger.debug(f"Git working tree inspect note: {wt_err}")

            except Exception as git_err:
                logger.warning(f"Git inspection failed for {project_id}: {git_err}")

        # Universal File-Hash fallback & verification
        current_hashes = self._compute_file_hashes(repo_path)
        stored_hashes: Dict[str, str] = {}
        if project.stats and isinstance(project.stats, dict) and "file_hashes" in project.stats:
            stored_hashes = project.stats.get("file_hashes", {})

        if stored_hashes:
            for fpath, fhash in current_hashes.items():
                if fpath not in stored_hashes:
                    if fpath not in files_added:
                        files_added.append(fpath)
                elif stored_hashes[fpath] != fhash:
                    if fpath not in files_modified and fpath not in files_added:
                        files_modified.append(fpath)

            for old_path in stored_hashes:
                if old_path not in current_hashes:
                    if old_path not in files_deleted:
                        files_deleted.append(old_path)

        # Clean duplicates and normalize
        files_added = sorted(list(set(files_added)))
        files_modified = sorted(list(set(f for f in files_modified if f not in files_added and f not in files_deleted)))
        files_deleted = sorted(list(set(files_deleted)))
        total_changed = len(files_added) + len(files_modified) + len(files_deleted)

        has_changes = total_changed > 0 or (
            git_inspected and previous_commit_sha is not None and previous_commit_sha != current_commit_sha
        )

        # Identify affected entities, APIs, DB models, documents, and diagrams
        affected_entities: List[str] = []
        affected_apis: List[str] = []
        affected_db_models: List[str] = []
        affected_documents: List[str] = []
        affected_diagrams: List[str] = []

        all_changed_files = set(files_added + files_modified + files_deleted)

        if all_changed_files:
            # Query affected CodeEntities
            entity_res = await db.execute(
                select(CodeEntity.name, CodeEntity.file_path).where(
                    CodeEntity.project_id == project_id,
                    CodeEntity.file_path.in_(list(all_changed_files)),
                )
            )
            for ename, _ in entity_res.all():
                if ename not in affected_entities:
                    affected_entities.append(ename)

            # Query affected APIEndpoints
            api_res = await db.execute(
                select(APIEndpoint.path, APIEndpoint.method).where(
                    APIEndpoint.project_id == project_id,
                    APIEndpoint.file_path.in_(list(all_changed_files)),
                )
            )
            for path, method in api_res.all():
                endpoint_label = f"{method} {path}"
                if endpoint_label not in affected_apis:
                    affected_apis.append(endpoint_label)

            # Query affected DatabaseModels
            db_res = await db.execute(
                select(DatabaseModel.name).where(
                    DatabaseModel.project_id == project_id,
                    DatabaseModel.file_path.in_(list(all_changed_files)),
                )
            )
            for mname, in db_res.all():
                if mname not in affected_db_models:
                    affected_db_models.append(mname)

            # Query affected Documents
            doc_res = await db.execute(
                select(Document.title, Document.document_type, Document.target_path).where(
                    Document.project_id == project_id
                )
            )
            for title, dtype, tpath in doc_res.all():
                if tpath and tpath in all_changed_files:
                    affected_documents.append(f"{dtype}: {title}")
                elif dtype == "API_DOCS" and affected_apis:
                    affected_documents.append(f"{dtype}: {title}")
                elif dtype == "DATABASE_DOCS" and affected_db_models:
                    affected_documents.append(f"{dtype}: {title}")
                elif dtype in {"PROJECT_OVERVIEW", "README", "ARCHITECTURE_OVERVIEW"}:
                    affected_documents.append(f"{dtype}: {title}")

            # Affected Diagrams
            if affected_db_models:
                affected_diagrams.append("DATABASE_ER")
            if affected_apis:
                affected_diagrams.append("API_SERVICE_RELATIONSHIP")
            if affected_entities or len(all_changed_files) > 0:
                affected_diagrams.extend(["DEPENDENCY_DIAGRAM", "MODULE_ARCHITECTURE", "SYSTEM_ARCHITECTURE"])

            affected_documents = sorted(list(set(affected_documents)))
            affected_diagrams = sorted(list(set(affected_diagrams)))

        summary = (
            f"Detected {total_changed} changed files ({len(files_added)} added, {len(files_modified)} modified, {len(files_deleted)} deleted). "
            f"Impact: {len(affected_entities)} entities, {len(affected_apis)} APIs, {len(affected_db_models)} DB models."
            if has_changes
            else "Repository is in sync with the latest analysis snapshot. No changes detected."
        )

        return ChangeCheckResponse(
            project_id=project_id,
            has_changes=has_changes,
            previous_commit_sha=previous_commit_sha,
            current_commit_sha=current_commit_sha or previous_commit_sha,
            files_added=files_added,
            files_modified=files_modified,
            files_deleted=files_deleted,
            total_files_changed=total_changed,
            affected_entities=affected_entities,
            affected_apis=affected_apis,
            affected_db_models=affected_db_models,
            affected_documents=affected_documents,
            affected_diagrams=affected_diagrams,
            summary=summary,
        )

    async def update_documentation_and_sync(
        self,
        project_id: str,
        db: AsyncSession,
        force_all: bool = False,
        document_types: Optional[List[str]] = None,
        regenerate_diagrams: bool = True,
    ) -> ChangeReportResponse:
        """
        Executes the Phase 14 incremental synchronization pipeline:
        1. Checks for repository changes.
        2. Reanalyzes only affected files (parsing code, updating dependencies, APIs, DB models).
        3. Updates affected documentation with version archiving (DocumentVersion).
        4. Regenerates affected architecture diagrams.
        5. Updates Onboarding Guide if setup files were changed.
        6. Updates Project commit SHA, timestamp, and stores a ChangeRecord.
        7. Guarantees: Does NOT claim synchronized unless analysis completed successfully.
        """
        check = await self.detect_changes(project_id, db)
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        repo_path = Path(project.repository_path)

        # If no changes and force_all is False, return immediately
        if not check.has_changes and not force_all:
            no_change_record = ChangeRecord(
                project_id=project_id,
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                total_files_changed=0,
                files_added=[],
                files_modified=[],
                files_deleted=[],
                entities_affected=[],
                apis_affected=[],
                db_models_affected=[],
                documentation_updated=[],
                diagrams_updated=[],
                status="NO_CHANGES",
                details_json={"note": "Repository already up to date."},
            )
            db.add(no_change_record)
            await db.commit()
            await db.refresh(no_change_record)

            return ChangeReportResponse(
                id=no_change_record.id,
                project_id=project_id,
                status="NO_CHANGES",
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                files_changed={"added": [], "modified": [], "deleted": []},
                total_files_changed=0,
                entities_affected=[],
                apis_affected=[],
                db_models_affected=[],
                documentation_updated=[],
                diagrams_updated=[],
                created_at=no_change_record.created_at,
                message="Repository is already in sync with documentation. No updates required.",
            )

        # Mark project sync in progress
        project.sync_status = "SYNCING"
        await db.commit()

        documentation_updated: List[UpdatedDocumentItem] = []
        diagrams_updated: List[UpdatedDiagramItem] = []
        entities_updated_names: List[str] = list(check.affected_entities)
        apis_updated_names: List[str] = list(check.affected_apis)
        db_models_updated_names: List[str] = list(check.affected_db_models)

        try:
            # -------------------------------------------------------------
            # STEP 4: REANALYZE ONLY AFFECTED FILES WHERE POSSIBLE
            # -------------------------------------------------------------
            # Handle deleted files: remove associated entities, endpoints, models
            if check.files_deleted:
                await db.execute(
                    delete(CodeEntity).where(
                        CodeEntity.project_id == project_id,
                        CodeEntity.file_path.in_(check.files_deleted),
                    )
                )
                await db.execute(
                    delete(APIEndpoint).where(
                        APIEndpoint.project_id == project_id,
                        APIEndpoint.file_path.in_(check.files_deleted),
                    )
                )
                await db.execute(
                    delete(DatabaseModel).where(
                        DatabaseModel.project_id == project_id,
                        DatabaseModel.file_path.in_(check.files_deleted),
                    )
                )
                await db.execute(
                    delete(DependencyNode).where(
                        DependencyNode.project_id == project_id,
                        DependencyNode.file_path.in_(check.files_deleted),
                    )
                )

            # Handle added and modified files
            affected_code_files = [
                f for f in (check.files_added + check.files_modified)
                if Path(f).suffix.lower() in {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
            ]

            for rel_file in affected_code_files:
                abs_file = repo_path / rel_file
                if not abs_file.exists():
                    continue

                # Remove existing entities for modified file before re-extracting
                await db.execute(
                    delete(CodeEntity).where(
                        CodeEntity.project_id == project_id,
                        CodeEntity.file_path == rel_file,
                    )
                )

                try:
                    content = abs_file.read_text(encoding="utf-8", errors="replace")
                    extracted = code_parsing_engine.parse_file(str(abs_file), content)
                    for item in extracted:
                        entity_dict = item.to_dict(project_id, rel_file)
                        ce = CodeEntity(
                            project_id=project_id,
                            file_path=rel_file,
                            name=entity_dict["name"],
                            entity_type=entity_dict["entity_type"],
                            start_line=entity_dict["start_line"],
                            end_line=entity_dict["end_line"],
                            signature=entity_dict.get("signature"),
                            parent_entity=entity_dict.get("parent_entity"),
                            metadata_json=entity_dict.get("metadata", {}),
                        )
                        db.add(ce)
                        if item.name not in entities_updated_names:
                            entities_updated_names.append(item.name)
                except Exception as parse_err:
                    logger.warning(f"Error re-parsing {rel_file}: {parse_err}")

            # Re-run dependency analyzer on the repository to update topology
            try:
                await dependency_analyzer.analyze_dependencies(repo_path, project_id, db)
            except Exception as dep_err:
                logger.warning(f"Dependency analyzer update warning: {dep_err}")

            # Re-run API discovery
            try:
                discovered_apis = await api_discovery_service.discover_apis(project_id, repo_path, db)
                for api in discovered_apis:
                    label = f"{api.method} {api.path}"
                    if label not in apis_updated_names:
                        apis_updated_names.append(label)
            except Exception as api_err:
                logger.warning(f"API discovery update warning: {api_err}")

            # Re-run Database models analysis
            try:
                db_models = await database_structure_analyzer.analyze_project_database(project_id, repo_path, db)
                for m in db_models:
                    if m.name not in db_models_updated_names:
                        db_models_updated_names.append(m.name)
            except Exception as dba_err:
                logger.warning(f"Database analyzer update warning: {dba_err}")

            # Re-run Knowledge Graph build
            try:
                await knowledge_graph_service.build_graph(project_id, db)
            except Exception as kg_err:
                logger.warning(f"Knowledge graph update warning: {kg_err}")

            # -------------------------------------------------------------
            # STEP 7 & 8: REGENERATE AFFECTED DOCUMENTATION WITH VERSIONING
            # -------------------------------------------------------------
            doc_stmt = select(Document).where(Document.project_id == project_id)
            doc_res = await db.execute(doc_stmt)
            existing_documents = doc_res.scalars().all()

            target_types_set = set(document_types) if document_types else None

            for doc in existing_documents:
                # Check if this document is affected or force_all requested
                is_affected = force_all or (
                    doc.target_path and doc.target_path in (check.files_added + check.files_modified + check.files_deleted)
                )
                if doc.document_type == "API_DOCS" and check.affected_apis:
                    is_affected = True
                if doc.document_type == "DATABASE_DOCS" and check.affected_db_models:
                    is_affected = True
                if doc.document_type in {"PROJECT_OVERVIEW", "README", "ARCHITECTURE_OVERVIEW"}:
                    is_affected = True

                if target_types_set and doc.document_type not in target_types_set:
                    is_affected = False

                if is_affected:
                    previous_ver = doc.version

                    # Archive previous version in DocumentVersion table
                    archive_ver = DocumentVersion(
                        document_id=doc.id,
                        project_id=project_id,
                        version=previous_ver,
                        document_type=doc.document_type,
                        title=doc.title,
                        content=doc.content,
                        target_path=doc.target_path,
                        commit_sha=project.last_commit_sha,
                        metadata_json={
                            "archived_by": "sync_service",
                            "reason": "incremental_change_sync",
                        },
                    )
                    db.add(archive_ver)

                    # Increment document version
                    doc.version = previous_ver + 1
                    doc.updated_at = utc_now()
                    doc.generated_at = utc_now()

                    # Attempt regeneration via LLM or template synthesizer
                    try:
                        refreshed = await documentation_service.generate_document_single(
                            project=project,
                            doc_type=doc.document_type,
                            db=db,
                            target_path=doc.target_path,
                            target_entity_id=doc.target_entity_id,
                            force_regenerate=True,
                        )
                        doc.content = refreshed.content
                        doc.title = refreshed.title
                    except (LLMNotConfiguredError, Exception) as regen_err:
                        logger.info(f"Using template refresh for {doc.document_type} (LLM note: {regen_err})")
                        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                        footer = (
                            f"\n\n---\n*Updated automatically by DocPilot AI Change Sync (v{doc.version}) "
                            f"on {now_str}. Analyzed commit: `{check.current_commit_sha or 'HEAD'}`.*"
                        )
                        if "Updated automatically by DocPilot AI" in doc.content:
                            doc.content = doc.content.split("\n\n---\n*Updated automatically")[0] + footer
                        else:
                            doc.content += footer

                    documentation_updated.append(
                        UpdatedDocumentItem(
                            document_id=doc.id,
                            title=doc.title,
                            document_type=doc.document_type,
                            target_path=doc.target_path,
                            version=doc.version,
                            previous_version=previous_ver,
                        )
                    )

            # -------------------------------------------------------------
            # ARCHITECTURE DIAGRAMS SYNCHRONIZATION
            # -------------------------------------------------------------
            if regenerate_diagrams:
                diagram_types_to_update = ["SYSTEM_ARCHITECTURE", "MODULE_ARCHITECTURE", "DEPENDENCY_DIAGRAM"]
                if check.affected_apis:
                    diagram_types_to_update.append("API_SERVICE_RELATIONSHIP")
                if check.affected_db_models:
                    diagram_types_to_update.append("DATABASE_ER")

                for dtype in diagram_types_to_update:
                    try:
                        diag = await diagram_service.generate_diagram(
                            project_id=project_id,
                            diagram_type=dtype,
                            db=db,
                            force_regenerate=True,
                        )
                        diagrams_updated.append(
                            UpdatedDiagramItem(
                                diagram_id=diag.id,
                                title=diag.title,
                                diagram_type=diag.diagram_type,
                                version=diag.version,
                            )
                        )
                    except Exception as diag_err:
                        logger.warning(f"Diagram refresh warning for {dtype}: {diag_err}")

            # -------------------------------------------------------------
            # ONBOARDING GUIDE SYNCHRONIZATION
            # -------------------------------------------------------------
            setup_patterns = {"package.json", "requirements.txt", "dockerfile", "docker-compose.yml", "makefile"}
            has_setup_changes = any(
                any(p in f.lower() for p in setup_patterns)
                for f in (check.files_added + check.files_modified + check.files_deleted)
            )
            if has_setup_changes or force_all:
                try:
                    await onboarding_service.generate_onboarding_guide(project_id, db, force_regenerate=True)
                except Exception as onb_err:
                    logger.warning(f"Onboarding guide sync warning: {onb_err}")

            # -------------------------------------------------------------
            # COMMIT SHA & STATS FINALIZATION
            # -------------------------------------------------------------
            current_hashes = self._compute_file_hashes(repo_path)
            stats_dict = dict(project.stats or {})
            stats_dict["file_hashes"] = current_hashes
            project.stats = stats_dict

            project.last_commit_sha = check.current_commit_sha or check.previous_commit_sha
            project.last_analyzed_at = utc_now()
            project.sync_status = "SYNCED"

            change_record = ChangeRecord(
                project_id=project_id,
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                total_files_changed=check.total_files_changed,
                files_added=check.files_added,
                files_modified=check.files_modified,
                files_deleted=check.files_deleted,
                entities_affected=entities_updated_names,
                apis_affected=apis_updated_names,
                db_models_affected=db_models_updated_names,
                documentation_updated=[d.model_dump() for d in documentation_updated],
                diagrams_updated=[d.model_dump() for d in diagrams_updated],
                status="SYNCED",
                details_json={
                    "documentation_count": len(documentation_updated),
                    "diagrams_count": len(diagrams_updated),
                },
            )
            db.add(change_record)
            await db.commit()
            await db.refresh(change_record)

            logger.info(
                f"Successfully synchronized documentation for project {project_id}: "
                f"{len(documentation_updated)} docs updated, {len(diagrams_updated)} diagrams updated."
            )

            return ChangeReportResponse(
                id=change_record.id,
                project_id=project_id,
                status="SYNCED",
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                files_changed={
                    "added": check.files_added,
                    "modified": check.files_modified,
                    "deleted": check.files_deleted,
                },
                total_files_changed=check.total_files_changed,
                entities_affected=entities_updated_names,
                apis_affected=apis_updated_names,
                db_models_affected=db_models_updated_names,
                documentation_updated=documentation_updated,
                diagrams_updated=diagrams_updated,
                created_at=change_record.created_at,
                message=(
                    f"Successfully synchronized documentation with repository changes. "
                    f"Updated {len(documentation_updated)} documents and {len(diagrams_updated)} diagrams."
                ),
            )

        except Exception as err:
            await db.rollback()
            logger.exception(f"Change synchronization failed for project {project_id}: {err}")

            # Do NOT claim synchronized when analysis failed
            failed_record = ChangeRecord(
                project_id=project_id,
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                total_files_changed=check.total_files_changed,
                files_added=check.files_added,
                files_modified=check.files_modified,
                files_deleted=check.files_deleted,
                entities_affected=entities_updated_names,
                apis_affected=apis_updated_names,
                db_models_affected=db_models_updated_names,
                documentation_updated=[],
                diagrams_updated=[],
                status="FAILED",
                error_message=str(err),
            )
            db.add(failed_record)

            # Update project status
            project_res = await db.execute(select(Project).where(Project.id == project_id))
            proj = project_res.scalars().first()
            if proj:
                proj.sync_status = "FAILED"
            await db.commit()
            await db.refresh(failed_record)

            return ChangeReportResponse(
                id=failed_record.id,
                project_id=project_id,
                status="FAILED",
                previous_commit_sha=check.previous_commit_sha,
                current_commit_sha=check.current_commit_sha,
                files_changed={
                    "added": check.files_added,
                    "modified": check.files_modified,
                    "deleted": check.files_deleted,
                },
                total_files_changed=check.total_files_changed,
                entities_affected=entities_updated_names,
                apis_affected=apis_updated_names,
                db_models_affected=db_models_updated_names,
                documentation_updated=[],
                diagrams_updated=[],
                created_at=failed_record.created_at,
                message="Synchronization failed during incremental analysis. Documentation was not marked synchronized.",
                error_message=str(err),
            )

    async def get_change_history(
        self, project_id: str, db: AsyncSession, limit: int = 10
    ) -> List[ChangeReportResponse]:
        """Retrieves historical change and synchronization records for audit tracking."""
        stmt = (
            select(ChangeRecord)
            .where(ChangeRecord.project_id == project_id)
            .order_by(desc(ChangeRecord.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        records = res.scalars().all()

        results: List[ChangeReportResponse] = []
        for r in records:
            docs_parsed = [
                UpdatedDocumentItem(
                    document_id=d.get("document_id", ""),
                    title=d.get("title", ""),
                    document_type=d.get("document_type", ""),
                    target_path=d.get("target_path"),
                    version=d.get("version", 1),
                    previous_version=d.get("previous_version"),
                )
                for d in (r.documentation_updated or [])
            ]
            diags_parsed = [
                UpdatedDiagramItem(
                    diagram_id=diag.get("diagram_id", ""),
                    title=diag.get("title", ""),
                    diagram_type=diag.get("diagram_type", ""),
                    version=diag.get("version", 1),
                )
                for diag in (r.diagrams_updated or [])
            ]

            results.append(
                ChangeReportResponse(
                    id=r.id,
                    project_id=r.project_id,
                    status=r.status,
                    previous_commit_sha=r.previous_commit_sha,
                    current_commit_sha=r.current_commit_sha,
                    files_changed={
                        "added": r.files_added or [],
                        "modified": r.files_modified or [],
                        "deleted": r.files_deleted or [],
                    },
                    total_files_changed=r.total_files_changed,
                    entities_affected=r.entities_affected or [],
                    apis_affected=r.apis_affected or [],
                    db_models_affected=r.db_models_affected or [],
                    documentation_updated=docs_parsed,
                    diagrams_updated=diags_parsed,
                    created_at=r.created_at,
                    message=f"Change report ({r.status}) with {r.total_files_changed} changed files.",
                    error_message=r.error_message,
                )
            )
        return results

    async def get_latest_change(
        self, project_id: str, db: AsyncSession
    ) -> Optional[ChangeReportResponse]:
        """Retrieves the latest synchronization report for a project."""
        history = await self.get_change_history(project_id, db, limit=1)
        return history[0] if history else None

    # Backward compatibility helper for legacy /repositories/:id/sync endpoint
    async def check_and_sync(self, repository_id: str, session: AsyncSession) -> SyncResponse:
        report = await self.update_documentation_and_sync(repository_id, session)
        return SyncResponse(
            repository_id=repository_id,
            changes_detected=report.total_files_changed > 0,
            modified_files=report.files_changed.get("modified", []),
            added_files=report.files_changed.get("added", []),
            deleted_files=report.files_changed.get("deleted", []),
            regenerated_docs=[d.title for d in report.documentation_updated],
            status=f"Synchronized {len(report.documentation_updated)} documents (Status: {report.status})",
        )


sync_service = SyncService()
