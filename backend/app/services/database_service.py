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
from backend.app.models.database_schema import DbModelRecord, DbRelationshipRecord
from backend.app.schemas.database_schema import (
    DatabaseModelResponse,
    DatabaseModelListResponse,
    DatabaseRelationshipResponse,
    DatabaseRelationshipListResponse,
    DatabaseDiagramResponse,
    DatabaseAnalyzeResponse,
    DatabaseField,
    DatabaseRelationship,
)
from backend.app.analyzers.database_analyzer import DatabaseAnalyzer
from backend.app.services.project_service import ProjectService


class DatabaseService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "database.json"

    @classmethod
    def analyze_database(cls, project_id: str, db: Session) -> DatabaseAnalyzeResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        logger.info(f"Starting database structure analysis for project {project_id} at {repo_dir}")

        start_time = time.perf_counter()

        # 1. Run Database Analyzer
        analysis_data = DatabaseAnalyzer.analyze_repository(repo_dir)
        models = analysis_data["models"]
        relationships = analysis_data["relationships"]
        mermaid_code = analysis_data["mermaid_code"]

        # 2. Clear existing records in DB
        db.execute(delete(DbRelationshipRecord).where(DbRelationshipRecord.project_id == project_id))
        db.execute(delete(DbModelRecord).where(DbModelRecord.project_id == project_id))
        db.commit()

        # 3. Store in DB
        now = datetime.now(timezone.utc)
        db_models: List[DbModelRecord] = []
        for m in models:
            rec = DbModelRecord(
                id=str(uuid.uuid4()),
                project_id=project_id,
                model_name=m.model_name,
                table_name=m.table_name,
                file_path=m.file_path,
                line_number=m.line_number,
                orm_framework=m.orm_framework,
                docstring=m.docstring,
                fields_json=[f.model_dump() for f in m.fields],
                relationships_json=[r.model_dump() for r in m.relationships],
                metadata_json=m.metadata_json,
                created_at=now,
            )
            db_models.append(rec)

        if db_models:
            db.bulk_save_objects(db_models)
            db.commit()

        db_rels: List[DbRelationshipRecord] = []
        for r in relationships:
            rel_rec = DbRelationshipRecord(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_model=r.source_model,
                source_table=r.source_table,
                target_model=r.target_model,
                target_table=r.target_table,
                relationship_type=r.relationship_type,
                foreign_key=r.foreign_key,
                confidence=r.confidence,
                cardinality_mermaid=r.cardinality_mermaid,
                description=r.description,
                metadata_json=r.metadata_json,
                created_at=now,
            )
            db_rels.append(rel_rec)

        if db_rels:
            db.bulk_save_objects(db_rels)
            db.commit()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Discovered {len(db_models)} models and {len(db_rels)} relationships in {duration_ms}ms")

        # 4. Cache JSON
        cache_file = cls._get_cache_path(repo_dir)
        try:
            cached_data = {
                "project_id": project_id,
                "analyzed_at": now.isoformat(),
                "total_models": len(db_models),
                "total_relationships": len(db_rels),
                "mermaid_code": mermaid_code,
                "models": [m.model_dump() for m in models],
                "relationships": [r.model_dump() for r in relationships],
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save database schema cache to {cache_file}: {e}")

        return DatabaseAnalyzeResponse(
            project_id=project_id,
            status="ANALYZED",
            total_models=len(db_models),
            total_relationships=len(db_rels),
            duration_ms=duration_ms,
            analyzed_at=now,
        )

    @classmethod
    def get_models(cls, project_id: str, db: Session) -> DatabaseModelListResponse:
        ProjectService.get_by_id(db, project_id)

        # Auto-run if 0
        count_stmt = select(func.count(DbModelRecord.id)).where(DbModelRecord.project_id == project_id)
        if (db.execute(count_stmt).scalar() or 0) == 0:
            try:
                cls.analyze_database(project_id, db)
            except Exception as e:
                logger.warning(f"Could not auto-analyze database models: {e}")

        stmt = select(DbModelRecord).where(DbModelRecord.project_id == project_id).order_by(DbModelRecord.table_name)
        results = db.execute(stmt).scalars().all()

        frameworks_count: Dict[str, int] = {}
        model_responses: List[DatabaseModelResponse] = []

        for r in results:
            frameworks_count[r.orm_framework] = frameworks_count.get(r.orm_framework, 0) + 1
            fields = [DatabaseField(**f) for f in r.fields_json]
            rels = [DatabaseRelationship(**rel) for rel in r.relationships_json]

            model_responses.append(
                DatabaseModelResponse(
                    id=r.id,
                    project_id=r.project_id,
                    model_name=r.model_name,
                    table_name=r.table_name,
                    file_path=r.file_path,
                    line_number=r.line_number,
                    orm_framework=r.orm_framework,
                    docstring=r.docstring,
                    fields=fields,
                    relationships=rels,
                    metadata_json=r.metadata_json,
                    created_at=r.created_at,
                )
            )

        return DatabaseModelListResponse(
            project_id=project_id,
            total_models=len(model_responses),
            models=model_responses,
            frameworks_count=frameworks_count,
        )

    @classmethod
    def get_relationships(cls, project_id: str, db: Session) -> DatabaseRelationshipListResponse:
        ProjectService.get_by_id(db, project_id)

        count_stmt = select(func.count(DbRelationshipRecord.id)).where(DbRelationshipRecord.project_id == project_id)
        if (db.execute(count_stmt).scalar() or 0) == 0:
            try:
                cls.analyze_database(project_id, db)
            except Exception as e:
                logger.warning(f"Could not auto-analyze database relationships: {e}")

        stmt = select(DbRelationshipRecord).where(DbRelationshipRecord.project_id == project_id).order_by(DbRelationshipRecord.source_table)
        results = db.execute(stmt).scalars().all()

        counts_by_type: Dict[str, int] = {}
        rel_responses: List[DatabaseRelationshipResponse] = []

        for r in results:
            counts_by_type[r.relationship_type] = counts_by_type.get(r.relationship_type, 0) + 1
            rel_responses.append(
                DatabaseRelationshipResponse(
                    id=r.id,
                    project_id=r.project_id,
                    source_model=r.source_model,
                    source_table=r.source_table,
                    target_model=r.target_model,
                    target_table=r.target_table,
                    relationship_type=r.relationship_type,
                    foreign_key=r.foreign_key,
                    confidence=r.confidence,
                    cardinality_mermaid=r.cardinality_mermaid,
                    description=r.description,
                    metadata_json=r.metadata_json,
                    created_at=r.created_at,
                )
            )

        return DatabaseRelationshipListResponse(
            project_id=project_id,
            total_relationships=len(rel_responses),
            relationships=rel_responses,
            counts_by_type=counts_by_type,
        )

    @classmethod
    def get_diagram(cls, project_id: str, db: Session) -> DatabaseDiagramResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path:
            raise ValidationException("Project has no repository files.")

        repo_dir = Path(project.repository_path).resolve()
        cache_file = cls._get_cache_path(repo_dir)

        if not cache_file.exists():
            cls.analyze_database(project_id, db)

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        models = cls.get_models(project_id, db).models

        return DatabaseDiagramResponse(
            project_id=project_id,
            mermaid_code=data.get("mermaid_code", "erDiagram"),
            total_tables=len(models),
            total_relationships=data.get("total_relationships", 0),
            models=models,
        )
