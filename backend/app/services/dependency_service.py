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
from backend.app.models.code_relationship import CodeRelationship
from backend.app.schemas.dependency import (
    GraphNode,
    GraphEdge,
    DependencyItem,
    DependencyListResponse,
    DependencyGraphResponse,
    EntityDependenciesResponse,
    AnalyzeDependenciesResponse,
)
from backend.app.analyzers.dependency_analyzer import DependencyAnalyzer
from backend.app.services.project_service import ProjectService


class DependencyService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "dependencies.json"

    @classmethod
    def analyze_dependencies(cls, project_id: str, db: Session) -> AnalyzeDependenciesResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        logger.info(f"Starting dependency analysis for project {project_id} at {repo_dir}")

        start_time = time.perf_counter()

        # 1. Run Dependency Analyzer
        graph_data = DependencyAnalyzer.analyze_repository(repo_dir)

        # 2. Clear existing relationships in DB
        db.execute(delete(CodeRelationship).where(CodeRelationship.project_id == project_id))
        db.commit()

        # 3. Store relationships in DB
        now = datetime.now(timezone.utc)
        db_items: List[CodeRelationship] = []

        for raw in graph_data["raw_dependencies"]:
            rel = CodeRelationship(
                id=str(uuid.uuid4()),
                project_id=project_id,
                source_id=raw["source_id"],
                source_name=raw["source_name"],
                source_type=raw["source_type"],
                target_id=raw["target_id"],
                target_name=raw["target_name"],
                target_type=raw["target_type"],
                relationship_type=raw["relationship_type"],
                confidence=raw["confidence"],
                is_internal=raw["is_internal"],
                file_path=raw["file_path"],
                line_number=raw["line_number"],
                metadata_json=raw["metadata_json"],
                created_at=now,
            )
            db_items.append(rel)

        if db_items:
            db.bulk_save_objects(db_items)
            db.commit()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Saved {len(db_items)} relationships across {graph_data['total_nodes']} nodes in {duration_ms}ms")

        # 4. Cache full graph JSON
        cache_file = cls._get_cache_path(repo_dir)
        try:
            cached_payload = {
                "project_id": project_id,
                "analyzed_at": now.isoformat(),
                "total_nodes": graph_data["total_nodes"],
                "total_edges": graph_data["total_edges"],
                "internal_edges_count": graph_data["internal_edges_count"],
                "external_edges_count": graph_data["external_edges_count"],
                "nodes": [n.model_dump() for n in graph_data["nodes"]],
                "edges": [e.model_dump() for e in graph_data["edges"]],
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save dependencies cache to {cache_file}: {e}")

        return AnalyzeDependenciesResponse(
            project_id=project_id,
            status="ANALYZED",
            total_nodes=graph_data["total_nodes"],
            total_edges=graph_data["total_edges"],
            internal_edges=graph_data["internal_edges_count"],
            external_edges=graph_data["external_edges_count"],
            duration_ms=duration_ms,
            analyzed_at=now,
        )

    @classmethod
    def get_dependencies(
        cls,
        project_id: str,
        db: Session,
        relationship_type: Optional[str] = None,
        is_internal: Optional[bool] = None,
        skip: int = 0,
        limit: int = 500,
    ) -> DependencyListResponse:
        ProjectService.get_by_id(db, project_id)

        # Check if DB has relationships; if 0, auto-run
        count_stmt = select(func.count(CodeRelationship.id)).where(CodeRelationship.project_id == project_id)
        if (db.execute(count_stmt).scalar() or 0) == 0:
            try:
                cls.analyze_dependencies(project_id, db)
            except Exception as e:
                logger.warning(f"Could not auto-analyze dependencies: {e}")

        stmt = select(CodeRelationship).where(CodeRelationship.project_id == project_id)
        if relationship_type:
            stmt = stmt.where(CodeRelationship.relationship_type == relationship_type.upper())
        if is_internal is not None:
            stmt = stmt.where(CodeRelationship.is_internal == is_internal)

        stmt = stmt.order_by(CodeRelationship.source_name).offset(skip).limit(limit)
        results = db.execute(stmt).scalars().all()

        type_count_stmt = (
            select(CodeRelationship.relationship_type, func.count(CodeRelationship.id))
            .where(CodeRelationship.project_id == project_id)
            .group_by(CodeRelationship.relationship_type)
        )
        counts = {t: c for t, c in db.execute(type_count_stmt).all()}

        items = [DependencyItem.model_validate(r) for r in results]

        return DependencyListResponse(
            project_id=project_id,
            total_dependencies=len(items),
            dependencies=items,
            counts_by_type=counts,
        )

    @classmethod
    def get_dependency_graph(
        cls, project_id: str, db: Session, include_external: bool = True
    ) -> DependencyGraphResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path:
            raise ValidationException("Project has no repository files.")

        repo_dir = Path(project.repository_path).resolve()
        cache_file = cls._get_cache_path(repo_dir)

        if not cache_file.exists():
            cls.analyze_dependencies(project_id, db)

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        nodes = [GraphNode(**n) for n in data["nodes"]]
        edges = [GraphEdge(**e) for e in data["edges"]]

        if not include_external:
            edges = [e for e in edges if e.is_internal]
            internal_node_ids = {e.source for e in edges}.union({e.target for e in edges})
            nodes = [n for n in nodes if n.is_internal or n.id in internal_node_ids]

        return DependencyGraphResponse(
            project_id=project_id,
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            internal_edges_count=sum(1 for e in edges if e.is_internal),
            external_edges_count=sum(1 for e in edges if not e.is_internal),
        )

    @classmethod
    def get_entity_dependencies(
        cls, project_id: str, entity_id: str, db: Session
    ) -> EntityDependenciesResponse:
        ProjectService.get_by_id(db, project_id)

        # Incoming (target is entity_id or target_name is entity_id)
        in_stmt = select(CodeRelationship).where(
            CodeRelationship.project_id == project_id,
            (CodeRelationship.target_id == entity_id) | (CodeRelationship.target_name == entity_id),
        )
        incoming = [DependencyItem.model_validate(r) for r in db.execute(in_stmt).scalars().all()]

        # Outgoing (source is entity_id or source_name is entity_id)
        out_stmt = select(CodeRelationship).where(
            CodeRelationship.project_id == project_id,
            (CodeRelationship.source_id == entity_id) | (CodeRelationship.source_name == entity_id),
        )
        outgoing = [DependencyItem.model_validate(r) for r in db.execute(out_stmt).scalars().all()]

        return EntityDependenciesResponse(
            entity_id=entity_id,
            entity_name=entity_id.split(":")[-1],
            entity_type="entity",
            incoming_dependencies=incoming,
            outgoing_dependencies=outgoing,
            total_dependencies=len(incoming) + len(outgoing),
        )
