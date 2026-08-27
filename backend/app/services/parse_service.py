import os
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from backend.app.core.logging import logger
from backend.app.core.exceptions import ValidationException, NotFoundException
from backend.app.models.project import Project
from backend.app.models.code_entity import CodeEntity
from backend.app.schemas.entity import (
    CodeEntityResponse,
    FileEntitiesResponse,
    ProjectEntitiesResponse,
    ParseResponse,
)
from backend.app.analyzers.code_parser import CodeParser
from backend.app.services.project_service import ProjectService


class ParseService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "entities.json"

    @classmethod
    def parse_project(cls, project_id: str, db: Session) -> ParseResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        logger.info(f"Starting code parsing for project {project_id} at {repo_dir}")

        start_time = time.perf_counter()

        # 1. Parse repository files
        raw_entities = CodeParser.parse_repository(repo_dir)

        # 2. Clear existing entities for this project
        db.execute(delete(CodeEntity).where(CodeEntity.project_id == project_id))
        db.commit()

        # 3. Create DB Models and tally counts
        files_set = set()
        entities_by_type: Dict[str, int] = {}
        db_entities: List[CodeEntity] = []

        now = datetime.now(timezone.utc)

        for e in raw_entities:
            files_set.add(e.file_path)
            entities_by_type[e.entity_type] = entities_by_type.get(e.entity_type, 0) + 1

            db_entity = CodeEntity(
                id=str(uuid.uuid4()),
                project_id=project_id,
                file_path=e.file_path,
                name=e.name,
                entity_type=e.entity_type,
                start_line=e.start_line,
                end_line=e.end_line,
                signature=e.signature,
                parent_entity=e.parent_entity,
                docstring=e.docstring,
                metadata_json=e.metadata_json,
                created_at=now,
            )
            db_entities.append(db_entity)

        # Bulk save
        if db_entities:
            db.bulk_save_objects(db_entities)
            db.commit()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Parsed {len(raw_entities)} entities across {len(files_set)} files in {duration_ms}ms for project {project_id}")

        # 4. Save cache JSON
        cache_file = cls._get_cache_path(repo_dir)
        try:
            cached_data = [
                {
                    "id": ent.id,
                    "name": ent.name,
                    "entity_type": ent.entity_type,
                    "file_path": ent.file_path,
                    "start_line": ent.start_line,
                    "end_line": ent.end_line,
                    "signature": ent.signature,
                    "parent_entity": ent.parent_entity,
                    "docstring": ent.docstring,
                    "metadata_json": ent.metadata_json,
                }
                for ent in db_entities
            ]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save entities cache to {cache_file}: {e}")

        return ParseResponse(
            project_id=project_id,
            status="PARSED",
            files_parsed=len(files_set),
            total_entities=len(db_entities),
            entities_by_type=entities_by_type,
            duration_ms=duration_ms,
            parsed_at=now,
        )

    @classmethod
    def get_project_entities(
        cls,
        project_id: str,
        db: Session,
        entity_type: Optional[str] = None,
        file_path: Optional[str] = None,
        skip: int = 0,
        limit: int = 500,
    ) -> ProjectEntitiesResponse:
        # Check if project exists
        ProjectService.get_by_id(db, project_id)

        # Check if entities exist; if 0 entities, run parser automatically
        count_stmt = select(func.count(CodeEntity.id)).where(CodeEntity.project_id == project_id)
        total_in_db = db.execute(count_stmt).scalar() or 0

        if total_in_db == 0:
            # Auto-trigger parsing if repo exists
            try:
                cls.parse_project(project_id, db)
            except Exception as e:
                logger.warning(f"Could not auto-parse project {project_id}: {e}")

        # Build query
        stmt = select(CodeEntity).where(CodeEntity.project_id == project_id)
        if entity_type:
            stmt = stmt.where(CodeEntity.entity_type == entity_type.upper())
        if file_path:
            clean_path = file_path.replace("\\", "/").lstrip("/")
            stmt = stmt.where(CodeEntity.file_path == clean_path)

        stmt = stmt.order_by(CodeEntity.file_path, CodeEntity.start_line).offset(skip).limit(limit)
        entities = db.execute(stmt).scalars().all()

        # Count per type
        type_count_stmt = (
            select(CodeEntity.entity_type, func.count(CodeEntity.id))
            .where(CodeEntity.project_id == project_id)
            .group_by(CodeEntity.entity_type)
        )
        counts_raw = db.execute(type_count_stmt).all()
        entity_counts = {t: c for t, c in counts_raw}

        response_entities = [CodeEntityResponse.model_validate(e) for e in entities]

        return ProjectEntitiesResponse(
            project_id=project_id,
            total_entities=sum(entity_counts.values()),
            entities=response_entities,
            entity_counts=entity_counts,
        )

    @classmethod
    def get_entity_by_id(cls, project_id: str, entity_id: str, db: Session) -> CodeEntityResponse:
        stmt = select(CodeEntity).where(
            CodeEntity.project_id == project_id,
            CodeEntity.id == entity_id,
        )
        entity = db.execute(stmt).scalar_one_or_none()
        if not entity:
            raise NotFoundException("CodeEntity", entity_id)
        return CodeEntityResponse.model_validate(entity)

    @classmethod
    def get_file_entities(cls, project_id: str, file_path: str, db: Session) -> FileEntitiesResponse:
        # Check if project exists
        ProjectService.get_by_id(db, project_id)

        clean_path = file_path.replace("\\", "/").lstrip("/")

        # Check if project has entities parsed
        count_stmt = select(func.count(CodeEntity.id)).where(CodeEntity.project_id == project_id)
        total_in_db = db.execute(count_stmt).scalar() or 0
        if total_in_db == 0:
            try:
                cls.parse_project(project_id, db)
            except Exception:
                pass

        stmt = (
            select(CodeEntity)
            .where(CodeEntity.project_id == project_id, CodeEntity.file_path == clean_path)
            .order_by(CodeEntity.start_line)
        )
        entities = db.execute(stmt).scalars().all()

        entity_counts: Dict[str, int] = {}
        for e in entities:
            entity_counts[e.entity_type] = entity_counts.get(e.entity_type, 0) + 1

        response_entities = [CodeEntityResponse.model_validate(e) for e in entities]

        return FileEntitiesResponse(
            project_id=project_id,
            file_path=clean_path,
            total_entities=len(response_entities),
            entities=response_entities,
            entity_counts=entity_counts,
        )
