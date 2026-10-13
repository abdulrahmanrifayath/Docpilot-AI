import os
import re
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import EntityNotFoundException
from app.core.logging import logger
from app.models.project import (
    APIEndpoint,
    CodeEntity,
    DatabaseModel,
    DatabaseRelationship,
    DependencyNode,
    DependencyRelationship,
    KnowledgeEdge,
    KnowledgeNode,
    Project,
    utc_now,
)
from app.schemas.project import (
    KnowledgeBuildResponse,
    KnowledgeEdgeResponse,
    KnowledgeEntityDetailResponse,
    KnowledgeGraphResponse,
    KnowledgeGraphStats,
    KnowledgeNodeResponse,
)


class UnifiedKnowledgeGraphService:
    """
    Combines repository analysis results from Scanner, Code Parser,
    Dependency Analyzer, API Discovery, and Database Analyzer into a
    single unified project knowledge graph.
    """

    SERVICE_SUFFIXES = (
        "service",
        "manager",
        "client",
        "controller",
        "repository",
        "worker",
        "provider",
        "handler",
    )

    def _classify_class_node_type(self, name: str) -> str:
        nl = name.lower()
        if any(nl.endswith(sfx) for sfx in self.SERVICE_SUFFIXES):
            return "service"
        return "class"

    async def build_knowledge_graph(
        self, project_id: str, db: AsyncSession
    ) -> KnowledgeBuildResponse:
        """
        Builds or rebuilds the complete unified knowledge graph for the given project.
        """
        # 1. Fetch Project
        p_res = await db.execute(select(Project).where(Project.id == project_id))
        project = p_res.scalars().first()
        if not project:
            raise EntityNotFoundException("Project", project_id)

        # 2. Gather existing multi-phase data
        # Code entities
        ce_res = await db.execute(
            select(CodeEntity).where(CodeEntity.project_id == project_id)
        )
        code_entities = list(ce_res.scalars().all())

        # Dependency nodes and edges
        dn_res = await db.execute(
            select(DependencyNode).where(DependencyNode.project_id == project_id)
        )
        dep_nodes = list(dn_res.scalars().all())

        dr_res = await db.execute(
            select(DependencyRelationship).where(
                DependencyRelationship.project_id == project_id
            )
        )
        dep_rels = list(dr_res.scalars().all())

        # APIs
        api_res = await db.execute(
            select(APIEndpoint).where(APIEndpoint.project_id == project_id)
        )
        apis = list(api_res.scalars().all())

        # Database models & relationships
        db_res = await db.execute(
            select(DatabaseModel)
            .options(selectinload(DatabaseModel.fields))
            .where(DatabaseModel.project_id == project_id)
        )
        db_models = list(db_res.scalars().all())

        dbr_res = await db.execute(
            select(DatabaseRelationship).where(
                DatabaseRelationship.project_id == project_id
            )
        )
        db_rels = list(dbr_res.scalars().all())

        # 3. Data structures to collect nodes and edges without duplicates
        # Map: node_id -> dict
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        # Set of edge unique keys: (source_id, target_id, relationship_type) -> dict
        edges_dict: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        def make_scoped_id(raw_id: str) -> str:
            if raw_id.startswith(f"{project_id}:"):
                return raw_id
            return f"{project_id}:{raw_id}"

        def add_node(
            nid: str,
            name: str,
            label: str,
            node_type: str,
            file_path: Optional[str] = None,
            entity_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
        ):
            scoped_id = make_scoped_id(nid)
            if scoped_id not in nodes_dict:
                nodes_dict[scoped_id] = {
                    "id": scoped_id,
                    "name": name,
                    "label": label,
                    "node_type": node_type,
                    "file_path": file_path,
                    "entity_id": entity_id,
                    "metadata": metadata or {},
                }
            else:
                # Merge metadata if needed
                if metadata:
                    nodes_dict[scoped_id]["metadata"].update(metadata)

        def add_edge(
            source_id: str,
            target_id: str,
            rel_type: str,
            confidence: float = 1.0,
            metadata: Optional[Dict[str, Any]] = None,
        ):
            scoped_src = make_scoped_id(source_id)
            scoped_tgt = make_scoped_id(target_id)
            if scoped_src == scoped_tgt:
                return
            key = (scoped_src, scoped_tgt, rel_type)
            if key not in edges_dict:
                src_node = nodes_dict.get(scoped_src)
                tgt_node = nodes_dict.get(scoped_tgt)
                edges_dict[key] = {
                    "id": f"edge:{scoped_src}->{scoped_tgt}:{rel_type}",
                    "source_id": scoped_src,
                    "target_id": scoped_tgt,
                    "source_name": src_node["name"] if src_node else scoped_src,
                    "target_name": tgt_node["name"] if tgt_node else scoped_tgt,
                    "source_type": src_node["node_type"] if src_node else "unknown",
                    "target_type": tgt_node["node_type"] if tgt_node else "unknown",
                    "relationship_type": rel_type,
                    "confidence": confidence,
                    "metadata": metadata or {},
                }

        # ---------------------------------------------------------------------
        # LAYER 1: Folders & Files (Repository Scanner Hierarchy)
        # ---------------------------------------------------------------------
        structure = project.structure or {}
        file_tree = structure.get("file_tree", [])

        def walk_file_tree(nodes: List[Dict[str, Any]], parent_folder_id: Optional[str]):
            for n in nodes:
                path = n.get("path", "")
                name = n.get("name", "")
                ntype = n.get("type", "file")
                if ntype == "directory":
                    folder_id = f"folder:{path}"
                    add_node(
                        nid=folder_id,
                        name=name,
                        label=path or name,
                        node_type="folder",
                        file_path=path,
                        metadata={"size": n.get("size")},
                    )
                    if parent_folder_id:
                        add_edge(parent_folder_id, folder_id, "CONTAINS")
                    if n.get("children"):
                        walk_file_tree(n["children"], folder_id)
                else:
                    file_id = f"file:{path}"
                    add_node(
                        nid=file_id,
                        name=name,
                        label=path or name,
                        node_type="file",
                        file_path=path,
                        metadata={
                            "size": n.get("file_size") or n.get("size"),
                            "lines": n.get("estimated_line_count"),
                            "category": n.get("file_category"),
                            "language": n.get("language"),
                        },
                    )
                    if parent_folder_id:
                        add_edge(parent_folder_id, file_id, "CONTAINS")

        walk_file_tree(file_tree, None)

        # ---------------------------------------------------------------------
        # LAYER 2: Code Entities (AST Classes, Functions, Methods, Modules)
        # ---------------------------------------------------------------------
        entity_name_to_id: Dict[str, str] = {}
        file_path_to_id: Dict[str, str] = {}

        for ce in code_entities:
            c_type = ce.entity_type.lower()
            file_id = f"file:{ce.file_path}"
            file_path_to_id[ce.file_path] = file_id

            if c_type in ("class", "interface", "component"):
                k_type = self._classify_class_node_type(ce.name)
                nid = f"class:{ce.file_path}:{ce.name}"
                label = ce.name
                add_node(
                    nid=nid,
                    name=ce.name,
                    label=label,
                    node_type=k_type,
                    file_path=ce.file_path,
                    entity_id=ce.id,
                    metadata=ce.metadata_json or {},
                )
                entity_name_to_id[ce.name] = nid
                # Edge: file contains class
                add_edge(file_id, nid, "CONTAINS")

                # Inheritance
                bases = (ce.metadata_json or {}).get("bases") or (ce.metadata_json or {}).get("inheritance") or []
                for base in bases:
                    base_id = entity_name_to_id.get(base) or f"class:{base}"
                    add_edge(nid, base_id, "EXTENDS")

            elif c_type in ("function", "method"):
                nid = f"fn:{ce.file_path}:{ce.name}"
                label = f"{ce.name}()"
                add_node(
                    nid=nid,
                    name=ce.name,
                    label=label,
                    node_type="function",
                    file_path=ce.file_path,
                    entity_id=ce.id,
                    metadata=ce.metadata_json or {},
                )
                entity_name_to_id[ce.name] = nid

                # If inside parent class: class contains method
                if ce.parent_entity:
                    parent_nid = entity_name_to_id.get(ce.parent_entity) or f"class:{ce.file_path}:{ce.parent_entity}"
                    add_edge(parent_nid, nid, "CONTAINS")
                else:
                    # File contains function
                    add_edge(file_id, nid, "CONTAINS")

            elif c_type == "module":
                nid = f"module:{ce.file_path}"
                add_node(
                    nid=nid,
                    name=ce.name,
                    label=ce.name,
                    node_type="module",
                    file_path=ce.file_path,
                    entity_id=ce.id,
                    metadata=ce.metadata_json or {},
                )
                add_edge(file_id, nid, "CONTAINS")

        # ---------------------------------------------------------------------
        # LAYER 3: Dependency Relationships (Imports, Calls, Dependencies)
        # ---------------------------------------------------------------------
        # Map dependency nodes
        dep_node_map: Dict[str, str] = {}
        for dn in dep_nodes:
            # Map into knowledge node
            if dn.file_path and f"file:{dn.file_path}" in nodes_dict:
                dep_node_map[dn.name] = f"file:{dn.file_path}"
            elif dn.name in entity_name_to_id:
                dep_node_map[dn.name] = entity_name_to_id[dn.name]
            else:
                dn_type = self._classify_class_node_type(dn.name) if dn.node_type == "class" else dn.node_type
                if dn.is_external:
                    dn_type = "external"
                dn_id = f"{dn_type}:{dn.name}"
                add_node(
                    nid=dn_id,
                    name=dn.name,
                    label=dn.name,
                    node_type=dn_type,
                    file_path=dn.file_path,
                    entity_id=dn.id,
                    metadata=dn.metadata_json or {},
                )
                dep_node_map[dn.name] = dn_id

        for dr in dep_rels:
            src_id = dep_node_map.get(dr.source) or entity_name_to_id.get(dr.source)
            tgt_id = dep_node_map.get(dr.target) or entity_name_to_id.get(dr.target)
            if src_id and tgt_id:
                add_edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    rel_type=dr.relationship_type,
                    confidence=dr.confidence,
                    metadata=dr.metadata_json or {},
                )

        # ---------------------------------------------------------------------
        # LAYER 4: APIs (Endpoints, Handlers, Schemas, Related Components)
        # ---------------------------------------------------------------------
        api_nodes_list: List[str] = []
        for ep in apis:
            api_id = f"api:{ep.method}:{ep.path}"
            label = f"{ep.method} {ep.path}"
            add_node(
                nid=api_id,
                name=label,
                label=label,
                node_type="api",
                file_path=ep.file_path,
                entity_id=ep.id,
                metadata={
                    "method": ep.method,
                    "path": ep.path,
                    "handler_name": ep.handler_name,
                    "authentication_required": ep.authentication_required,
                    "tags": ep.tags or [],
                    "request_schema": ep.request_schema or {},
                    "response_schema": ep.response_schema or {},
                },
            )
            api_nodes_list.append(api_id)

            # Edge: file defines API
            file_id = f"file:{ep.file_path}"
            if file_id in nodes_dict:
                add_edge(file_id, api_id, "DEFINES_API")

            # Handler link: API -> handler function/method
            handler_id = None
            if ep.handler_name in entity_name_to_id:
                handler_id = entity_name_to_id[ep.handler_name]
            elif f"fn:{ep.file_path}:{ep.handler_name}" in nodes_dict:
                handler_id = f"fn:{ep.file_path}:{ep.handler_name}"

            if handler_id:
                add_edge(api_id, handler_id, "HANDLED_BY")
                add_edge(handler_id, api_id, "HANDLES_API")

            # Schema links
            if ep.request_schema and ep.request_schema.get("body_model"):
                b_model = ep.request_schema["body_model"]
                m_id = entity_name_to_id.get(b_model)
                if m_id:
                    add_edge(api_id, m_id, "USES_SCHEMA")
            if ep.response_schema and ep.response_schema.get("model"):
                r_model = ep.response_schema["model"]
                m_id = entity_name_to_id.get(r_model)
                if m_id:
                    add_edge(api_id, m_id, "USES_SCHEMA")

            # Related components
            meta = ep.metadata_json or {}
            raw_components = meta.get("related_components", [])
            for comp in raw_components:
                c_name = comp if isinstance(comp, str) else comp.get("name", "")
                c_id = entity_name_to_id.get(c_name) or dep_node_map.get(c_name)
                if c_id:
                    add_edge(api_id, c_id, "DEPENDS_ON")
                    if handler_id:
                        add_edge(handler_id, c_id, "CALLS")

        # ---------------------------------------------------------------------
        # LAYER 5: Database Models & Relationships
        # ---------------------------------------------------------------------
        db_model_map: Dict[str, str] = {}
        for dbm in db_models:
            db_id = f"db:{dbm.name}"
            label = f"{dbm.name} ({dbm.table_name})"
            field_names = [f.name for f in dbm.fields]
            add_node(
                nid=db_id,
                name=dbm.name,
                label=label,
                node_type="database",
                file_path=dbm.file_path,
                entity_id=dbm.id,
                metadata={
                    "table_name": dbm.table_name,
                    "orm_type": dbm.orm_type,
                    "fields_count": len(dbm.fields),
                    "fields": field_names,
                    "primary_keys": [f.name for f in dbm.fields if f.is_primary_key],
                    "foreign_keys": [f.name for f in dbm.fields if f.is_foreign_key],
                },
            )
            db_model_map[dbm.name] = db_id
            db_model_map[dbm.table_name] = db_id

            # File defines model
            file_id = f"file:{dbm.file_path}"
            if file_id in nodes_dict:
                add_edge(file_id, db_id, "DEFINES_MODEL")

            # If class exists with same name, link class to database model
            if dbm.name in entity_name_to_id:
                c_id = entity_name_to_id[dbm.name]
                add_edge(c_id, db_id, "MAPS_TO_TABLE")

        # Database relationships (foreign keys, ORM relationships)
        for dbr in db_rels:
            src_db = db_model_map.get(dbr.source_model)
            tgt_db = db_model_map.get(dbr.target_model)
            if src_db and tgt_db:
                add_edge(
                    source_id=src_db,
                    target_id=tgt_db,
                    rel_type="RELATIONSHIP_WITH",
                    metadata={
                        "cardinality": dbr.relationship_type,
                        "foreign_key_field": dbr.foreign_key_field,
                        "back_populates": dbr.back_populates,
                        "description": dbr.description,
                    },
                )

        # ---------------------------------------------------------------------
        # LAYER 6: Cross-Layer Bridge Connections (Frontend -> API -> Service -> DB)
        # ---------------------------------------------------------------------
        # Connect APIs to Database Models & Services to Database Models
        for node_id, node_data in list(nodes_dict.items()):
            n_type = node_data["node_type"]
            n_name = node_data["name"].lower()

            # 1. Check if class/service is a repository or service querying a DB model
            if n_type in ("service", "class", "function"):
                for m_name, db_id in db_model_map.items():
                    m_lower = m_name.lower()
                    # e.g. UserRepository -> User, OrderService -> Order, get_user -> User
                    if (
                        m_lower in n_name
                        and len(m_lower) >= 3
                        and node_id != db_id
                    ):
                        add_edge(node_id, db_id, "QUERIES_DB")

            # 2. Check if API routes directly reference DB entities
            if n_type == "api":
                for m_name, db_id in db_model_map.items():
                    m_lower = m_name.lower()
                    # Path includes resource name e.g. /users, /orders
                    if f"/{m_lower}" in n_name or f"/{m_lower}s" in n_name:
                        add_edge(node_id, db_id, "ACCESSES_DB")

            # 3. Frontend client files calling APIs
            if n_type == "file" and ("api" in n_name or "client" in n_name):
                for api_nid in api_nodes_list:
                    scoped_api_nid = make_scoped_id(api_nid)
                    api_node = nodes_dict.get(scoped_api_nid)
                    if api_node:
                        api_meta = api_node.get("metadata", {})
                        path = api_meta.get("path", "")
                        # Match client calling API
                        if path and path.split("/")[-1] in n_name:
                            add_edge(node_id, scoped_api_nid, "CALLS")

        # ---------------------------------------------------------------------
        # 4. Save to Database (Atomic Replace for this project)
        # ---------------------------------------------------------------------
        await db.execute(
            delete(KnowledgeEdge).where(KnowledgeEdge.project_id == project_id)
        )
        await db.execute(
            delete(KnowledgeNode).where(KnowledgeNode.project_id == project_id)
        )
        await db.commit()

        # Batch insert nodes
        created_nodes: List[KnowledgeNode] = []
        for n_data in nodes_dict.values():
            kn = KnowledgeNode(
                id=n_data["id"],
                project_id=project_id,
                name=n_data["name"],
                label=n_data["label"],
                node_type=n_data["node_type"],
                file_path=n_data["file_path"],
                entity_id=n_data["entity_id"],
                metadata_json=n_data["metadata"],
                created_at=utc_now(),
            )
            db.add(kn)
            created_nodes.append(kn)

        # Batch insert edges (validating both endpoints exist)
        created_edges: List[KnowledgeEdge] = []
        for e_data in edges_dict.values():
            if e_data["source_id"] in nodes_dict and e_data["target_id"] in nodes_dict:
                ke = KnowledgeEdge(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    source_id=e_data["source_id"],
                    target_id=e_data["target_id"],
                    source_name=e_data["source_name"],
                    target_name=e_data["target_name"],
                    source_type=e_data["source_type"],
                    target_type=e_data["target_type"],
                    relationship_type=e_data["relationship_type"],
                    confidence=e_data["confidence"],
                    metadata_json=e_data["metadata"],
                    created_at=utc_now(),
                )
                db.add(ke)
                created_edges.append(ke)

        await db.commit()

        # Stats
        node_types_count: Dict[str, int] = {}
        for n in created_nodes:
            node_types_count[n.node_type] = node_types_count.get(n.node_type, 0) + 1

        rel_types_count: Dict[str, int] = {}
        for e in created_edges:
            rel_types_count[e.relationship_type] = (
                rel_types_count.get(e.relationship_type, 0) + 1
            )

        logger.info(
            f"Knowledge Graph for project {project_id}: built {len(created_nodes)} nodes, "
            f"{len(created_edges)} edges across {len(node_types_count)} node types"
        )

        return KnowledgeBuildResponse(
            project_id=project_id,
            status="BUILT",
            total_nodes=len(created_nodes),
            total_edges=len(created_edges),
            node_types=node_types_count,
            relationship_types=rel_types_count,
            built_at=utc_now(),
        )

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
        """
        Retrieves the unified knowledge graph with optional node type filters,
        text search, focus neighborhood mode, depth limits, and pagination.
        """
        # Verify project exists
        p_res = await db.execute(select(Project).where(Project.id == project_id))
        if not p_res.scalars().first():
            raise EntityNotFoundException("Project", project_id)

        # If knowledge graph empty, build on the fly
        count_check = await db.execute(
            select(KnowledgeNode.id)
            .where(KnowledgeNode.project_id == project_id)
            .limit(1)
        )
        if not count_check.first():
            await self.build_knowledge_graph(project_id, db)

        # 1. Fetch total statistics
        all_nodes_res = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.project_id == project_id)
        )
        all_nodes = list(all_nodes_res.scalars().all())

        all_edges_res = await db.execute(
            select(KnowledgeEdge).where(KnowledgeEdge.project_id == project_id)
        )
        all_edges = list(all_edges_res.scalars().all())

        total_nodes = len(all_nodes)
        total_edges = len(all_edges)

        node_types_count: Dict[str, int] = {}
        for n in all_nodes:
            node_types_count[n.node_type] = node_types_count.get(n.node_type, 0) + 1

        rel_types_count: Dict[str, int] = {}
        for e in all_edges:
            rel_types_count[e.relationship_type] = (
                rel_types_count.get(e.relationship_type, 0) + 1
            )

        stats = KnowledgeGraphStats(
            total_nodes=total_nodes,
            total_edges=total_edges,
            node_types=node_types_count,
            relationship_types=rel_types_count,
        )

        node_map = {n.id: n for n in all_nodes}

        # 2. Focus Mode (BFS traversal around focus_id up to depth)
        if focus_id:
            # Resolve focus_id (check exact id, exact name, or case-insensitive)
            resolved_focus_node = node_map.get(focus_id)
            if not resolved_focus_node:
                for n in all_nodes:
                    if n.name == focus_id or n.id == focus_id:
                        resolved_focus_node = n
                        break
            if not resolved_focus_node:
                for n in all_nodes:
                    if n.name.lower() == focus_id.lower():
                        resolved_focus_node = n
                        break
            if not resolved_focus_node:
                for n in all_nodes:
                    if focus_id.lower() in n.name.lower() or focus_id.lower() in n.label.lower():
                        resolved_focus_node = n
                        break

            if not resolved_focus_node:
                raise EntityNotFoundException("KnowledgeNode", focus_id)

            actual_focus_id = resolved_focus_node.id
            visited_node_ids = {actual_focus_id}
            queue = deque([(actual_focus_id, 0)])

            # Build adjacency
            adj: Dict[str, Set[str]] = {n.id: set() for n in all_nodes}
            for e in all_edges:
                adj[e.source_id].add(e.target_id)
                adj[e.target_id].add(e.source_id)

            max_hops = min(max(depth, 1), 5)
            while queue:
                curr_id, curr_dist = queue.popleft()
                if curr_dist < max_hops:
                    for neighbor in adj.get(curr_id, set()):
                        if neighbor not in visited_node_ids:
                            visited_node_ids.add(neighbor)
                            queue.append((neighbor, curr_dist + 1))

            focused_nodes = [node_map[nid] for nid in visited_node_ids if nid in node_map]

            # Filter by node_type if specified
            if node_types:
                types_set = {t.lower() for t in node_types}
                focused_nodes = [
                    n for n in focused_nodes
                    if n.node_type.lower() in types_set or n.id == actual_focus_id
                ]

            # Search filter if specified
            if search:
                s_lower = search.lower()
                focused_nodes = [
                    n for n in focused_nodes
                    if s_lower in n.name.lower()
                    or s_lower in n.label.lower()
                    or n.id == actual_focus_id
                ]

            node_ids_set = {n.id for n in focused_nodes}
            focused_edges = [
                e for e in all_edges
                if e.source_id in node_ids_set and e.target_id in node_ids_set
            ]

            return KnowledgeGraphResponse(
                project_id=project_id,
                nodes=[KnowledgeNodeResponse.model_validate(n) for n in focused_nodes],
                edges=[KnowledgeEdgeResponse.model_validate(e) for e in focused_edges],
                stats=stats,
                limit=len(focused_nodes),
                offset=0,
                has_more=False,
                focus_id=actual_focus_id,
                depth=depth,
            )

        # 3. Standard Filtered & Paginated Mode
        filtered_nodes = all_nodes

        if node_types:
            types_set = {t.lower() for t in node_types}
            filtered_nodes = [
                n for n in filtered_nodes if n.node_type.lower() in types_set
            ]

        if search:
            s_lower = search.lower()
            filtered_nodes = [
                n for n in filtered_nodes
                if s_lower in n.name.lower() or s_lower in n.label.lower()
            ]

        # Order nodes by priority: APIs, Services, Database, Classes, Functions, Files, Folders
        type_priority = {
            "api": 1,
            "service": 2,
            "database": 3,
            "class": 4,
            "function": 5,
            "file": 6,
            "folder": 7,
            "module": 8,
            "external": 9,
        }
        filtered_nodes.sort(
            key=lambda n: (type_priority.get(n.node_type.lower(), 10), n.name.lower())
        )

        total_filtered = len(filtered_nodes)
        paged_nodes = filtered_nodes[offset : offset + limit]
        has_more = (offset + limit) < total_filtered

        paged_node_ids = {n.id for n in paged_nodes}
        relevant_edges = [
            e for e in all_edges
            if e.source_id in paged_node_ids and e.target_id in paged_node_ids
        ]

        return KnowledgeGraphResponse(
            project_id=project_id,
            nodes=[KnowledgeNodeResponse.model_validate(n) for n in paged_nodes],
            edges=[KnowledgeEdgeResponse.model_validate(e) for e in relevant_edges],
            stats=stats,
            limit=limit,
            offset=offset,
            has_more=has_more,
            focus_id=None,
            depth=None,
        )

    async def get_entity_knowledge(
        self,
        project_id: str,
        entity_id: str,
        db: AsyncSession,
    ) -> KnowledgeEntityDetailResponse:
        """
        Deep query for a specific entity in the unified knowledge graph:
        - "What uses this entity/function?" (incoming edges)
        - "Which APIs depend on this?" (reachable API nodes)
        - "Which database models are connected to this?" (reachable Database nodes)
        - "What are the dependencies of this module/class?" (outgoing edges)
        """
        # Fetch node by ID or lookup by name
        scoped_id = entity_id if entity_id.startswith(f"{project_id}:") else f"{project_id}:{entity_id}"
        res = await db.execute(
            select(KnowledgeNode).where(
                KnowledgeNode.project_id == project_id,
                (KnowledgeNode.id == entity_id)
                | (KnowledgeNode.id == scoped_id)
                | (KnowledgeNode.name == entity_id)
                | (KnowledgeNode.entity_id == entity_id),
            )
        )
        node = res.scalars().first()
        if not node:
            raise EntityNotFoundException("KnowledgeNode", entity_id)

        target_id = node.id

        # Fetch all edges for the project
        all_edges_res = await db.execute(
            select(KnowledgeEdge).where(KnowledgeEdge.project_id == project_id)
        )
        all_edges = list(all_edges_res.scalars().all())

        all_nodes_res = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.project_id == project_id)
        )
        all_nodes = list(all_nodes_res.scalars().all())
        node_map = {n.id: n for n in all_nodes}

        # 1. Incoming Edges ("What uses this?")
        incoming = [e for e in all_edges if e.target_id == target_id]
        dependents = [node_map[e.source_id] for e in incoming if e.source_id in node_map]

        # 2. Outgoing Edges ("What does this use / depend on?")
        outgoing = [e for e in all_edges if e.source_id == target_id]
        dependencies = [node_map[e.target_id] for e in outgoing if e.target_id in node_map]

        # 3. Upstream APIs: Multi-hop reverse traversal (Who can invoke this?)
        # Adjacency reverse: target -> sources
        rev_adj: Dict[str, List[str]] = {}
        for e in all_edges:
            rev_adj.setdefault(e.target_id, []).append(e.source_id)

        connected_apis: List[KnowledgeNode] = []
        visited_rev = {target_id}
        queue_rev = deque([(target_id, 0)])
        while queue_rev:
            curr, hops = queue_rev.popleft()
            curr_node = node_map.get(curr)
            if curr_node and curr_node.node_type == "api" and curr != target_id:
                if curr_node not in connected_apis:
                    connected_apis.append(curr_node)
            if hops < 3:
                for src in rev_adj.get(curr, []):
                    if src not in visited_rev:
                        visited_rev.add(src)
                        queue_rev.append((src, hops + 1))

        # 4. Downstream Database Models: Multi-hop forward traversal
        # Adjacency forward: source -> targets
        fwd_adj: Dict[str, List[str]] = {}
        for e in all_edges:
            fwd_adj.setdefault(e.source_id, []).append(e.target_id)

        connected_dbs: List[KnowledgeNode] = []
        visited_fwd = {target_id}
        queue_fwd = deque([(target_id, 0)])
        while queue_fwd:
            curr, hops = queue_fwd.popleft()
            curr_node = node_map.get(curr)
            if curr_node and curr_node.node_type == "database" and curr != target_id:
                if curr_node not in connected_dbs:
                    connected_dbs.append(curr_node)
            if hops < 3:
                for tgt in fwd_adj.get(curr, []):
                    if tgt not in visited_fwd:
                        visited_fwd.add(tgt)
                        queue_fwd.append((tgt, hops + 1))

        # 5. Neighborhood Subgraph (direct 1-hop connected nodes & edges)
        neighborhood_node_ids = {target_id}
        for e in incoming:
            neighborhood_node_ids.add(e.source_id)
        for e in outgoing:
            neighborhood_node_ids.add(e.target_id)

        neighborhood_nodes = [
            node_map[nid] for nid in neighborhood_node_ids if nid in node_map
        ]
        neighborhood_edges = [
            e for e in all_edges
            if e.source_id in neighborhood_node_ids and e.target_id in neighborhood_node_ids
        ]

        return KnowledgeEntityDetailResponse(
            entity=KnowledgeNodeResponse.model_validate(node),
            incoming_edges=[KnowledgeEdgeResponse.model_validate(e) for e in incoming],
            outgoing_edges=[KnowledgeEdgeResponse.model_validate(e) for e in outgoing],
            connected_apis=[KnowledgeNodeResponse.model_validate(n) for n in connected_apis],
            connected_database_models=[
                KnowledgeNodeResponse.model_validate(n) for n in connected_dbs
            ],
            dependencies=[KnowledgeNodeResponse.model_validate(n) for n in dependencies],
            dependents=[KnowledgeNodeResponse.model_validate(n) for n in dependents],
            neighborhood_nodes=[
                KnowledgeNodeResponse.model_validate(n) for n in neighborhood_nodes
            ],
            neighborhood_edges=[
                KnowledgeEdgeResponse.model_validate(e) for e in neighborhood_edges
            ],
        )


knowledge_graph_service = UnifiedKnowledgeGraphService()
