import uuid
import math
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple

from backend.app.schemas.knowledge_graph import (
    KnowledgeNode,
    KnowledgeEdge,
)
from backend.app.schemas.structure import StructureItem
from backend.app.schemas.entity import CodeEntityResponse
from backend.app.schemas.dependency import DependencyItem
from backend.app.schemas.api_endpoint import ApiEndpointResponse
from backend.app.schemas.database_schema import DatabaseModelResponse, DatabaseRelationshipResponse


LAYER_RANKS = {
    "FOLDER": 0,
    "COMPONENT": 1,
    "API": 2,
    "FILE": 3,
    "FUNCTION": 4,
    "CLASS": 5,
    "MODULE": 5,
    "DATABASE_TABLE": 6,
}


class KnowledgeBuilder:
    @classmethod
    def build_unified_graph(
        cls,
        structure_items: List[StructureItem],
        entities: List[CodeEntityResponse],
        relationships: List[DependencyItem],
        api_endpoints: List[ApiEndpointResponse],
        db_models: List[DatabaseModelResponse],
        db_relationships: List[DatabaseRelationshipResponse],
    ) -> Tuple[List[KnowledgeNode], List[KnowledgeEdge]]:
        nodes_map: Dict[str, KnowledgeNode] = {}
        edges: List[KnowledgeEdge] = []
        seen_edge_keys: Set[str] = set()

        def add_node(
            node_key: str,
            name: str,
            category: str,
            file_path: Optional[str] = None,
            line_number: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> KnowledgeNode:
            if node_key in nodes_map:
                return nodes_map[node_key]

            node = KnowledgeNode(
                id=str(uuid.uuid4()),
                node_key=node_key,
                name=name,
                category=category,
                file_path=file_path,
                line_number=line_number,
                metadata=metadata or {},
            )
            nodes_map[node_key] = node
            return node

        def add_edge(
            source_key: str,
            target_key: str,
            relationship: str,
            confidence: float = 1.0,
            label: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
        ):
            if not source_key or not target_key or source_key == target_key:
                return
            if source_key not in nodes_map or target_key not in nodes_map:
                return

            edge_key = f"{source_key}->{target_key}:{relationship}"
            if edge_key in seen_edge_keys:
                return

            seen_edge_keys.add(edge_key)
            edges.append(
                KnowledgeEdge(
                    id=str(uuid.uuid4()),
                    source=source_key,
                    target=target_key,
                    relationship=relationship,
                    confidence=confidence,
                    label=label or relationship.lower().replace("_", " "),
                    metadata=metadata or {},
                )
            )

        # ---------------------------------------------------------------------
        # 1. Folders & Files (Hierarchy)
        # ---------------------------------------------------------------------
        def process_structure(item: StructureItem, parent_key: Optional[str] = None):
            norm_path = item.path.replace("\\", "/")
            if item.type == "directory":
                dir_key = f"folder:{norm_path}" if norm_path else "folder:root"
                dir_name = item.name or "root"
                add_node(
                    node_key=dir_key,
                    name=dir_name,
                    category="FOLDER",
                    file_path=norm_path,
                    metadata={"total_lines": item.lines, "category": item.category},
                )
                if parent_key:
                    add_edge(parent_key, dir_key, "CONTAINS")

                if item.children:
                    for child in item.children:
                        process_structure(child, dir_key)
            else:
                file_key = f"file:{norm_path}"
                add_node(
                    node_key=file_key,
                    name=item.name,
                    category="FILE",
                    file_path=norm_path,
                    metadata={
                        "language": item.language,
                        "lines": item.lines,
                        "size": item.size,
                        "category": item.category,
                    },
                )
                if parent_key:
                    add_edge(parent_key, file_key, "CONTAINS")

        for item in structure_items:
            process_structure(item)

        # ---------------------------------------------------------------------
        # 2. Database Models & Tables
        # ---------------------------------------------------------------------
        table_to_model_key: Dict[str, str] = {}
        for m in db_models:
            tbl_key = f"table:{m.table_name}"
            table_to_model_key[m.table_name] = tbl_key

            add_node(
                node_key=tbl_key,
                name=f"{m.table_name}",
                category="DATABASE_TABLE",
                file_path=m.file_path,
                line_number=m.line_number,
                metadata={
                    "model_name": m.model_name,
                    "orm_framework": m.orm_framework,
                    "columns_count": len(m.fields),
                    "primary_keys": [f.name for f in m.fields if f.primary_key],
                    "foreign_keys": [f"{f.name}->{f.foreign_key}" for f in m.fields if f.foreign_key],
                    "docstring": m.docstring,
                },
            )

            # Link file -> table
            file_key = f"file:{m.file_path}"
            if file_key in nodes_map:
                add_edge(file_key, tbl_key, "MAPS_TO_MODEL")

        for rel in db_relationships:
            src_tbl = rel.source_table
            tgt_tbl = rel.target_table
            src_key = f"table:{src_tbl}"
            tgt_key = f"table:{tgt_tbl}"
            add_edge(
                src_key,
                tgt_key,
                rel.relationship_type,
                confidence=rel.confidence,
                label=rel.cardinality_mermaid,
            )

        # ---------------------------------------------------------------------
        # 3. Code Entities (Classes, Functions, Methods, Components)
        # ---------------------------------------------------------------------
        entity_name_to_key: Dict[Tuple[str, str], str] = {}
        for ent in entities:
            ent_key = f"entity:{ent.id}"
            entity_name_to_key[(ent.file_path, ent.name)] = ent_key

            add_node(
                node_key=ent_key,
                name=ent.name,
                category=ent.entity_type,
                file_path=ent.file_path,
                line_number=ent.start_line,
                metadata={
                    "signature": ent.signature,
                    "docstring": ent.docstring,
                    "entity_type": ent.entity_type,
                },
            )

            # Link file -> entity
            file_key = f"file:{ent.file_path}"
            if file_key in nodes_map:
                add_edge(file_key, ent_key, "DECLARES")

        # ---------------------------------------------------------------------
        # 4. API Endpoints
        # ---------------------------------------------------------------------
        for api in api_endpoints:
            api_key = f"api:{api.method.upper()}_{api.path}"
            add_node(
                node_key=api_key,
                name=f"[{api.method.upper()}] {api.path}",
                category="API",
                file_path=api.file_path,
                line_number=api.line_number,
                metadata={
                    "method": api.method,
                    "path": api.path,
                    "handler_name": api.handler_name,
                    "authentication_required": api.authentication_required,
                    "tags": api.tags,
                    "summary": api.summary,
                    "response_model": api.response_schema.response_model if api.response_schema else None,
                },
            )

            # Link file -> API
            file_key = f"file:{api.file_path}"
            if file_key in nodes_map:
                add_edge(file_key, api_key, "EXPOSES_API")

            # Link API -> Handler Function
            handler_key = entity_name_to_key.get((api.file_path, api.handler_name))
            if not handler_key:
                # Find by name in same file or anywhere
                for (f_p, name), k in entity_name_to_key.items():
                    if name == api.handler_name:
                        handler_key = k
                        break

            if handler_key:
                add_edge(api_key, handler_key, "HANDLES_ROUTE")

            # Link Handler -> Database Tables (QUERIES_TABLE)
            # If handler or response model references a table model
            for m in db_models:
                tbl_key = f"table:{m.table_name}"
                model_name = m.model_name
                tbl_name = m.table_name

                # Check if API path or summary or response model refers to model
                api_text = f"{api.path} {api.handler_name} {api.summary or ''} {str(api.response_schema or '')}".lower()
                if model_name.lower() in api_text or tbl_name.lower() in api_text:
                    if handler_key:
                        add_edge(handler_key, tbl_key, "QUERIES_TABLE", confidence=0.85)
                    else:
                        add_edge(api_key, tbl_key, "QUERIES_TABLE", confidence=0.75)

        # ---------------------------------------------------------------------
        # 5. Dependencies & Relationships
        # ---------------------------------------------------------------------
        for dep in relationships:
            src_key = None
            tgt_key = None

            # Map source
            if dep.source_type == "file":
                src_key = f"file:{dep.source_id}"
            else:
                src_key = f"entity:{dep.source_id}"

            # Map target
            if dep.target_type == "file":
                tgt_key = f"file:{dep.target_id}"
            elif dep.target_type == "package":
                tgt_key = f"package:{dep.target_name}"
                add_node(
                    node_key=tgt_key,
                    name=dep.target_name,
                    category="MODULE",
                    metadata={"external": True},
                )
            else:
                tgt_key = f"entity:{dep.target_id}"

            if src_key and tgt_key:
                add_edge(
                    src_key,
                    tgt_key,
                    dep.relationship_type,
                    confidence=dep.confidence,
                )

        # ---------------------------------------------------------------------
        # 6. Calculate In-Degree, Out-Degree, and Coordinates
        # ---------------------------------------------------------------------
        for edge in edges:
            if edge.source in nodes_map:
                nodes_map[edge.source].out_degree += 1
            if edge.target in nodes_map:
                nodes_map[edge.target].in_degree += 1

        # Calculate Dagre/Layered positions
        nodes_by_layer: Dict[int, List[KnowledgeNode]] = {}
        for n in nodes_map.values():
            rank = LAYER_RANKS.get(n.category, 3)
            nodes_by_layer.setdefault(rank, []).append(n)

        for rank, layer_nodes in nodes_by_layer.items():
            total = len(layer_nodes)
            x_spacing = 260
            y_pos = rank * 220
            start_x = -((total - 1) * x_spacing) / 2

            for idx, n in enumerate(layer_nodes):
                n.position = {
                    "x": round(start_x + idx * x_spacing, 2),
                    "y": round(y_pos, 2),
                }

        return list(nodes_map.values()), edges
