import os
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Set
from collections import deque
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from backend.app.core.logging import logger
from backend.app.core.exceptions import ValidationException, NotFoundException
from backend.app.models.knowledge_graph import KnowledgeNodeRecord, KnowledgeEdgeRecord
from backend.app.schemas.knowledge_graph import (
    KnowledgeNode,
    KnowledgeEdge,
    KnowledgeGraphResponse,
    KnowledgeEntityDetail,
    KnowledgeBuildResponse,
)
from backend.app.analyzers.knowledge_builder import KnowledgeBuilder
from backend.app.services.project_service import ProjectService
from backend.app.services.scan_service import ScanService
from backend.app.services.parse_service import ParseService
from backend.app.services.dependency_service import DependencyService
from backend.app.services.api_service import ApiService
from backend.app.services.database_service import DatabaseService


class KnowledgeService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "knowledge_graph.json"

    @classmethod
    def build_knowledge_graph(cls, project_id: str, db: Session) -> KnowledgeBuildResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        logger.info(f"Building unified knowledge graph for project {project_id} at {repo_dir}")

        start_time = time.perf_counter()

        # 1. Fetch data from all underlying analyzers
        try:
            struct_data = ScanService.get_structure(project_id, db).structure
        except Exception:
            struct_data = []

        try:
            entities_data = ParseService.get_project_entities(project_id, db=db, limit=1000).entities
        except Exception:
            entities_data = []

        try:
            deps_data = DependencyService.get_dependencies(project_id, db=db, limit=1000).dependencies
        except Exception:
            deps_data = []

        try:
            apis_data = ApiService.get_apis(project_id, db=db, limit=1000).apis
        except Exception:
            apis_data = []

        try:
            models_data = DatabaseService.get_models(project_id, db=db).models
            db_rels_data = DatabaseService.get_relationships(project_id, db=db).relationships
        except Exception:
            models_data = []
            db_rels_data = []

        # 2. Build Unified Graph
        nodes, edges = KnowledgeBuilder.build_unified_graph(
            structure_items=struct_data,
            entities=entities_data,
            relationships=deps_data,
            api_endpoints=apis_data,
            db_models=models_data,
            db_relationships=db_rels_data,
        )

        # 3. Store in Database
        db.execute(delete(KnowledgeEdgeRecord).where(KnowledgeEdgeRecord.project_id == project_id))
        db.execute(delete(KnowledgeNodeRecord).where(KnowledgeNodeRecord.project_id == project_id))
        db.commit()

        now = datetime.now(timezone.utc)
        db_nodes: List[KnowledgeNodeRecord] = []
        counts_by_category: Dict[str, int] = {}

        for n in nodes:
            counts_by_category[n.category] = counts_by_category.get(n.category, 0) + 1
            rec = KnowledgeNodeRecord(
                id=n.id,
                project_id=project_id,
                node_key=n.node_key,
                name=n.name,
                category=n.category,
                file_path=n.file_path,
                line_number=n.line_number,
                metadata_json={
                    **n.metadata,
                    "position": n.position,
                    "in_degree": n.in_degree,
                    "out_degree": n.out_degree,
                },
                created_at=now,
            )
            db_nodes.append(rec)

        if db_nodes:
            db.bulk_save_objects(db_nodes)
            db.commit()

        db_edges: List[KnowledgeEdgeRecord] = []
        for e in edges:
            edge_rec = KnowledgeEdgeRecord(
                id=e.id,
                project_id=project_id,
                source_key=e.source,
                target_key=e.target,
                relationship=e.relationship,
                confidence=e.confidence,
                metadata_json={**e.metadata, "label": e.label},
                created_at=now,
            )
            db_edges.append(edge_rec)

        if db_edges:
            db.bulk_save_objects(db_edges)
            db.commit()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Built unified knowledge graph: {len(db_nodes)} nodes, {len(db_edges)} edges in {duration_ms}ms")

        # 4. Cache JSON
        cache_file = cls._get_cache_path(repo_dir)
        try:
            cached = {
                "project_id": project_id,
                "built_at": now.isoformat(),
                "total_nodes": len(db_nodes),
                "total_edges": len(db_edges),
                "counts_by_category": counts_by_category,
                "nodes": [n.model_dump() for n in nodes],
                "edges": [e.model_dump() for e in edges],
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write knowledge graph cache: {e}")

        return KnowledgeBuildResponse(
            project_id=project_id,
            status="BUILT",
            total_nodes=len(db_nodes),
            total_edges=len(db_edges),
            counts_by_category=counts_by_category,
            duration_ms=duration_ms,
            built_at=now,
        )

    @classmethod
    def get_knowledge_graph(
        cls,
        project_id: str,
        categories: Optional[str] = None,
        focus_node_id: Optional[str] = None,
        depth: int = 1,
        search_query: Optional[str] = None,
        limit: int = 500,
        db: Session = None,
    ) -> KnowledgeGraphResponse:
        ProjectService.get_by_id(db, project_id)

        # Auto-build if empty
        count_stmt = select(func.count(KnowledgeNodeRecord.id)).where(KnowledgeNodeRecord.project_id == project_id)
        if (db.execute(count_stmt).scalar() or 0) == 0:
            cls.build_knowledge_graph(project_id, db)

        # Query all records for this project
        node_stmt = select(KnowledgeNodeRecord).where(KnowledgeNodeRecord.project_id == project_id)
        raw_nodes = db.execute(node_stmt).scalars().all()

        edge_stmt = select(KnowledgeEdgeRecord).where(KnowledgeEdgeRecord.project_id == project_id)
        raw_edges = db.execute(edge_stmt).scalars().all()

        # Build in-memory lookup
        nodes_by_key: Dict[str, KnowledgeNode] = {}
        for r in raw_nodes:
            pos = r.metadata_json.get("position", {"x": 0, "y": 0})
            in_deg = r.metadata_json.get("in_degree", 0)
            out_deg = r.metadata_json.get("out_degree", 0)

            node = KnowledgeNode(
                id=r.id,
                node_key=r.node_key,
                name=r.name,
                category=r.category,
                file_path=r.file_path,
                line_number=r.line_number,
                position=pos,
                metadata=r.metadata_json,
                in_degree=in_deg,
                out_degree=out_deg,
            )
            nodes_by_key[r.node_key] = node

        edges_list: List[KnowledgeEdge] = []
        for e in raw_edges:
            edges_list.append(
                KnowledgeEdge(
                    id=e.id,
                    source=e.source_key,
                    target=e.target_key,
                    relationship=e.relationship,
                    confidence=e.confidence,
                    label=e.metadata_json.get("label"),
                    metadata=e.metadata_json,
                )
            )

        # ---------------------------------------------------------------------
        # Focus Node Sub-Graph (BFS traversal)
        # ---------------------------------------------------------------------
        retained_node_keys: Set[str] = set()

        if focus_node_id:
            # Find matching center node key
            center_key = None
            for k, n in nodes_by_key.items():
                if n.id == focus_node_id or n.node_key == focus_node_id:
                    center_key = k
                    break

            if center_key:
                retained_node_keys.add(center_key)
                queue = deque([(center_key, 0)])
                visited = {center_key}

                adj: Dict[str, Set[str]] = {}
                for e in edges_list:
                    adj.setdefault(e.source, set()).add(e.target)
                    adj.setdefault(e.target, set()).add(e.source)

                while queue:
                    curr, d = queue.popleft()
                    if d < depth:
                        for nbr in adj.get(curr, set()):
                            if nbr not in visited:
                                visited.add(nbr)
                                retained_node_keys.add(nbr)
                                queue.append((nbr, d + 1))
            else:
                retained_node_keys = set(nodes_by_key.keys())
        else:
            retained_node_keys = set(nodes_by_key.keys())

        # ---------------------------------------------------------------------
        # Category and Search Query Filters
        # ---------------------------------------------------------------------
        if categories:
            cat_set = {c.strip().upper() for c in categories.split(",") if c.strip()}
            retained_node_keys = {
                k for k in retained_node_keys if nodes_by_key[k].category.upper() in cat_set
            }

        if search_query and search_query.strip():
            q = search_query.strip().lower()
            retained_node_keys = {
                k
                for k in retained_node_keys
                if q in nodes_by_key[k].name.lower() or (nodes_by_key[k].file_path and q in nodes_by_key[k].file_path.lower())
            }

        # Apply Limit
        final_nodes = [nodes_by_key[k] for k in retained_node_keys][:limit]
        final_keys = {n.node_key for n in final_nodes}

        final_edges = [
            e for e in edges_list if e.source in final_keys and e.target in final_keys
        ]

        counts_by_category: Dict[str, int] = {}
        for n in final_nodes:
            counts_by_category[n.category] = counts_by_category.get(n.category, 0) + 1

        counts_by_relationship: Dict[str, int] = {}
        for e in final_edges:
            counts_by_relationship[e.relationship] = counts_by_relationship.get(e.relationship, 0) + 1

        return KnowledgeGraphResponse(
            project_id=project_id,
            total_nodes=len(final_nodes),
            total_edges=len(final_edges),
            nodes=final_nodes,
            edges=final_edges,
            counts_by_category=counts_by_category,
            counts_by_relationship=counts_by_relationship,
        )

    @classmethod
    def get_entity_knowledge(cls, project_id: str, entity_id: str, db: Session) -> KnowledgeEntityDetail:
        ProjectService.get_by_id(db, project_id)

        # Find target node
        stmt = select(KnowledgeNodeRecord).where(
            KnowledgeNodeRecord.project_id == project_id,
            (KnowledgeNodeRecord.id == entity_id)
            | (KnowledgeNodeRecord.node_key == entity_id)
            | (KnowledgeNodeRecord.node_key == f"entity:{entity_id}")
            | (KnowledgeNodeRecord.node_key == f"file:{entity_id}")
            | (KnowledgeNodeRecord.node_key == f"table:{entity_id}"),
        )
        node_rec = db.execute(stmt).scalars().first()
        if not node_rec:
            raise NotFoundException(f"Knowledge entity '{entity_id}' not found.")

        target_key = node_rec.node_key
        node = KnowledgeNode(
            id=node_rec.id,
            node_key=node_rec.node_key,
            name=node_rec.name,
            category=node_rec.category,
            file_path=node_rec.file_path,
            line_number=node_rec.line_number,
            position=node_rec.metadata_json.get("position", {"x": 0, "y": 0}),
            metadata=node_rec.metadata_json,
            in_degree=node_rec.metadata_json.get("in_degree", 0),
            out_degree=node_rec.metadata_json.get("out_degree", 0),
        )

        # Incoming edges (Upstream callers)
        in_stmt = select(KnowledgeEdgeRecord).where(
            KnowledgeEdgeRecord.project_id == project_id,
            KnowledgeEdgeRecord.target_key == target_key,
        )
        in_edges = db.execute(in_stmt).scalars().all()
        upstream_keys = {e.source_key for e in in_edges}

        # Outgoing edges (Downstream dependencies)
        out_stmt = select(KnowledgeEdgeRecord).where(
            KnowledgeEdgeRecord.project_id == project_id,
            KnowledgeEdgeRecord.source_key == target_key,
        )
        out_edges = db.execute(out_stmt).scalars().all()
        downstream_keys = {e.target_key for e in out_edges}

        all_keys = upstream_keys | downstream_keys
        rel_nodes_stmt = select(KnowledgeNodeRecord).where(
            KnowledgeNodeRecord.project_id == project_id,
            KnowledgeNodeRecord.node_key.in_(all_keys),
        )
        rel_records = {r.node_key: r for r in db.execute(rel_nodes_stmt).scalars().all()}

        upstream_nodes: List[KnowledgeNode] = []
        for k in upstream_keys:
            if k in rel_records:
                r = rel_records[k]
                upstream_nodes.append(
                    KnowledgeNode(
                        id=r.id,
                        node_key=r.node_key,
                        name=r.name,
                        category=r.category,
                        file_path=r.file_path,
                        line_number=r.line_number,
                        metadata=r.metadata_json,
                    )
                )

        downstream_nodes: List[KnowledgeNode] = []
        for k in downstream_keys:
            if k in rel_records:
                r = rel_records[k]
                downstream_nodes.append(
                    KnowledgeNode(
                        id=r.id,
                        node_key=r.node_key,
                        name=r.name,
                        category=r.category,
                        file_path=r.file_path,
                        line_number=r.line_number,
                        metadata=r.metadata_json,
                    )
                )

        connected_apis = [n for n in upstream_nodes + downstream_nodes if n.category == "API"]
        connected_tables = [n for n in upstream_nodes + downstream_nodes if n.category == "DATABASE_TABLE"]
        parent_item = next((n for n in upstream_nodes if n.category in ["FILE", "FOLDER"]), None)

        return KnowledgeEntityDetail(
            node=node,
            upstream_callers=upstream_nodes,
            downstream_dependencies=downstream_nodes,
            connected_apis=connected_apis,
            connected_database_tables=connected_tables,
            parent_file_or_folder=parent_item,
        )
