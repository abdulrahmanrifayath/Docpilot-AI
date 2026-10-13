"""
Automatic Architecture Diagram Generation Engine for DocPilot AI (Phase 10).

This module synthesizes structured diagrams directly from repository analysis:
1. High-level System Architecture (SYSTEM_ARCHITECTURE)
2. Module Architecture (MODULE_ARCHITECTURE)
3. Component Dependency Diagram (DEPENDENCY_DIAGRAM)
4. API-to-Service Relationships (API_SERVICE_RELATIONSHIP)
5. Database ER Diagram (DATABASE_ER)

Pipeline:
Structured repository metadata
-> Diagram graph model
-> Mermaid syntax
-> Validation
-> Database persistence & frontend rendering
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import (
    Project,
    CodeEntity,
    DependencyNode,
    DependencyRelationship,
    APIEndpoint,
    DatabaseModel,
    DatabaseField,
    DatabaseRelationship,
    KnowledgeNode,
    KnowledgeEdge,
    Diagram,
)
from app.schemas.project import DiagramResponse, DiagramGenerateResponse
from app.ai.llm_client import get_llm_client

logger = logging.getLogger("docpilot.diagrams")


# =============================================================================
# MERMAID SYNTAX VALIDATION
# =============================================================================

def validate_mermaid_syntax(mermaid_code: str) -> Tuple[bool, Optional[str]]:
    """
    Validates Mermaid diagram syntax before saving.
    Checks:
    - Non-empty content
    - Valid diagram header keywords
    - Balanced delimiters (brackets, parentheses, braces, quotes)
    - Balanced subgraphs and end statements
    """
    if not mermaid_code or not mermaid_code.strip():
        return False, "Mermaid code is empty or whitespace only"

    lines = [line.strip() for line in mermaid_code.strip().splitlines() if line.strip() and not line.strip().startswith("%%")]
    if not lines:
        return False, "Mermaid code contains no executable statements"

    first_line = lines[0].lower()
    valid_starters = (
        "flowchart",
        "graph",
        "erdiagram",
        "sequencediagram",
        "classdiagram",
        "statediagram",
        "gantt",
        "pie",
        "gitgraph",
        "c4context",
        "c4container",
        "c4component",
    )

    if not any(first_line.startswith(starter) for starter in valid_starters):
        return False, f"Invalid diagram header '{lines[0]}'. Must start with a valid Mermaid diagram declaration (flowchart, graph, erDiagram, etc.)"

    # Delimiter balance check across entire code (ignoring escaped characters)
    # Check square brackets [ ]
    sq_open = mermaid_code.count("[")
    sq_close = mermaid_code.count("]")
    if sq_open != sq_close:
        return False, f"Unbalanced square brackets in Mermaid syntax: {sq_open} '[' vs {sq_close} ']'"

    # Check curly braces { } (ignoring ER diagram cardinality symbols like ||--o{ and }o--||)
    braces_check_text = mermaid_code
    if first_line.startswith("erdiagram"):
        braces_check_text = re.sub(r'[o|]\s*\{', '', braces_check_text)
        braces_check_text = re.sub(r'\}\s*[o|]', '', braces_check_text)

    cr_open = braces_check_text.count("{")
    cr_close = braces_check_text.count("}")
    if cr_open != cr_close:
        return False, f"Unbalanced curly braces in Mermaid syntax: {cr_open} '{{' vs {cr_close} '}}'"

    # Check parentheses ( )
    pr_open = mermaid_code.count("(")
    pr_close = mermaid_code.count(")")
    if pr_open != pr_close:
        return False, f"Unbalanced parentheses in Mermaid syntax: {pr_open} '(' vs {pr_close} ')'"

    # Check subgraph ... end balancing for flowcharts
    if first_line.startswith(("flowchart", "graph")):
        subgraph_count = len(re.findall(r'^\s*subgraph\b', mermaid_code, re.MULTILINE | re.IGNORECASE))
        end_count = len(re.findall(r'^\s*end\b', mermaid_code, re.MULTILINE | re.IGNORECASE))
        if subgraph_count != end_count:
            return False, f"Unbalanced subgraphs: found {subgraph_count} 'subgraph' blocks but {end_count} 'end' statements"

    return True, None


class DiagramService:
    """Service orchestrating automatic architecture diagram generation from repository analysis."""

    SUPPORTED_TYPES = [
        "SYSTEM_ARCHITECTURE",
        "MODULE_ARCHITECTURE",
        "DEPENDENCY_DIAGRAM",
        "API_SERVICE_RELATIONSHIP",
        "DATABASE_ER",
    ]

    # Map aliases and lowercase representations to canonical uppercase enum
    TYPE_ALIASES = {
        "system_architecture": "SYSTEM_ARCHITECTURE",
        "system": "SYSTEM_ARCHITECTURE",
        "architecture": "SYSTEM_ARCHITECTURE",
        "module_architecture": "MODULE_ARCHITECTURE",
        "module": "MODULE_ARCHITECTURE",
        "modules": "MODULE_ARCHITECTURE",
        "dependency_diagram": "DEPENDENCY_DIAGRAM",
        "dependency": "DEPENDENCY_DIAGRAM",
        "dependencies": "DEPENDENCY_DIAGRAM",
        "api_service_relationship": "API_SERVICE_RELATIONSHIP",
        "api_service": "API_SERVICE_RELATIONSHIP",
        "api": "API_SERVICE_RELATIONSHIP",
        "apis": "API_SERVICE_RELATIONSHIP",
        "database_er": "DATABASE_ER",
        "database": "DATABASE_ER",
        "er": "DATABASE_ER",
    }

    def _normalize_type(self, raw_type: str) -> str:
        cleaned = raw_type.strip().lower()
        return self.TYPE_ALIASES.get(cleaned, raw_type.strip().upper())

    # =========================================================================
    # Helpers & Sanitization
    # =========================================================================

    def _clean_node_id(self, raw: str, prefix: str = "node") -> str:
        """Sanitizes an arbitrary string into a safe, alphanumeric Mermaid node ID."""
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', raw)
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        if not cleaned or not cleaned[0].isalpha():
            cleaned = f"{prefix}_{cleaned or 'id'}"
        return cleaned

    def _escape_label(self, raw: str) -> str:
        """Sanitizes and quotes a node label for safe display in Mermaid."""
        if not raw:
            return "Component"
        clean = raw.replace('"', "'").replace("\n", " ").strip()
        if len(clean) > 80:
            clean = clean[:77] + "..."
        return clean

    # =========================================================================
    # Diagram Generation Synthesizers
    # =========================================================================

    def _build_system_architecture(
        self,
        project: Project,
        entities: List[CodeEntity],
        dependencies: List[DependencyRelationship],
        apis: List[APIEndpoint],
        db_models: List[DatabaseModel],
    ) -> Tuple[str, Dict[str, Any], List[str], str]:
        """
        Synthesizes High-Level System Architecture.
        Tiers:
        - Clients (Web / Mobile / API Consumers)
        - Frontend (React / Vue / Vite SPA)
        - API Gateway / Routing (FastAPI / Express / Django)
        - Application / Domain Services
        - Persistence / Database (SQLAlchemy / Postgres / SQLite)
        - External Systems (Cloud / 3rd Party APIs)
        """
        lines = ["flowchart TB"]
        source_entities: List[str] = []
        flow_nodes: List[Dict[str, Any]] = []
        flow_edges: List[Dict[str, Any]] = []

        frameworks = project.frameworks or []
        infra = project.infrastructure or []
        lang_stats = project.languages or {}

        has_frontend = any(f.lower() in ("react", "vue", "angular", "svelte", "next.js", "nextjs") for f in frameworks) or "TypeScript" in lang_stats or "JavaScript" in lang_stats
        has_backend = any(f.lower() in ("fastapi", "flask", "django", "express", "express.js", "nest.js") for f in frameworks) or "Python" in lang_stats

        # Extract domain service entities
        service_classes = [e for e in entities if e.entity_type == "CLASS" and ("service" in e.name.lower() or "client" in e.name.lower() or "manager" in e.name.lower())][:6]
        if not service_classes:
            service_classes = [e for e in entities if e.entity_type == "CLASS"][:5]

        # 1. Clients
        lines.append('    subgraph Clients["Client Tier"]')
        lines.append('        Client_User["Web & Mobile Clients"]')
        lines.append('    end')
        source_entities.append("client:web_mobile")

        # 2. Frontend Tier
        if has_frontend:
            lines.append('    subgraph Frontend["Frontend Tier (SPA)"]')
            frontend_fw = "React / Vite" if any("react" in f.lower() for f in frameworks) else "Client Application"
            lines.append(f'        FE_App["{self._escape_label(frontend_fw)}"]')
            lines.append('        FE_Router["View Components & State"]')
            lines.append('        FE_App --> FE_Router')
            lines.append('    end')
            source_entities.append(f"tier:frontend:{frontend_fw}")

        # 3. Backend / API Gateway Tier
        lines.append('    subgraph Backend["API & Routing Tier"]')
        backend_name = "REST API Gateway"
        if any("fastapi" in f.lower() for f in frameworks):
            backend_name = "FastAPI Application"
        elif any("express" in f.lower() for f in frameworks):
            backend_name = "Express API Server"
        elif any("django" in f.lower() for f in frameworks):
            backend_name = "Django REST Backend"

        lines.append(f'        API_GW["{self._escape_label(backend_name)}"]')
        source_entities.append(f"tier:api:{backend_name}")

        if apis:
            api_count = len(apis)
            api_sample = apis[0].path if apis else "/api/v1"
            lines.append(f'        API_Routes["REST Endpoints ({api_count} detected)"]')
            lines.append('        API_GW --> API_Routes')
            for a in apis[:5]:
                source_entities.append(f"api:{a.method}:{a.path}")
        lines.append('    end')

        # 4. Core Domain Services Tier
        if service_classes:
            lines.append('    subgraph Domain["Application Services Tier"]')
            for svc in service_classes:
                node_id = self._clean_node_id(svc.name, prefix="svc")
                lines.append(f'        {node_id}["{self._escape_label(svc.name)}"]')
                source_entities.append(f"class:{svc.file_path}:{svc.name}")
            lines.append('    end')

        # 5. Database & Storage Tier
        lines.append('    subgraph Data["Persistence & Storage Tier"]')
        db_type = "SQL Database"
        if any("postgres" in inf.lower() for inf in infra):
            db_type = "PostgreSQL"
        elif any("sqlite" in inf.lower() for inf in infra):
            db_type = "SQLite Database"
        elif db_models and any(m.orm_type == "SQLAlchemy" for m in db_models):
            db_type = "Relational DB (SQLAlchemy ORM)"

        lines.append(f'        DB_Main[("({self._escape_label(db_type)})")]')
        source_entities.append(f"database:{db_type}")

        if db_models:
            for dm in db_models[:5]:
                m_node = self._clean_node_id(dm.name, prefix="tbl")
                lines.append(f'        {m_node}["{self._escape_label(dm.name)} Table"]')
                source_entities.append(f"table:{dm.table_name or dm.name}")
                lines.append(f'        DB_Main --- {m_node}')
        lines.append('    end')

        # 6. Inter-Tier Connectors
        if has_frontend:
            lines.append('    Client_User -->|HTTPS| FE_App')
            lines.append('    FE_Router -->|REST API Calls| API_GW')
        else:
            lines.append('    Client_User -->|HTTP REST| API_GW')

        if service_classes:
            target_api = "API_Routes" if apis else "API_GW"
            for svc in service_classes:
                s_id = self._clean_node_id(svc.name, prefix="svc")
                lines.append(f'    {target_api} --> {s_id}')
                lines.append(f'    {s_id} --> DB_Main')
        else:
            target_api = "API_Routes" if apis else "API_GW"
            lines.append(f'    {target_api} --> DB_Main')

        mermaid_code = "\n".join(lines)
        description = (
            f"High-level system topology depicting client entry points, {backend_name}, "
            f"core application logic, and persistence infrastructure."
        )
        return mermaid_code, {"nodes": flow_nodes, "edges": flow_edges}, source_entities, description

    def _build_module_architecture(
        self,
        project: Project,
        entities: List[CodeEntity],
        dependencies: List[DependencyRelationship],
    ) -> Tuple[str, Dict[str, Any], List[str], str]:
        """
        Synthesizes Module Architecture.
        Groups detected modules and files into their parent packages/directories,
        and connects inter-module imports and dependencies.
        """
        lines = ["flowchart LR"]
        source_entities: List[str] = []

        # Group entities and files by parent folder
        modules_by_dir: Dict[str, List[str]] = {}
        for ent in entities:
            if ent.file_path:
                parts = ent.file_path.replace("\\", "/").split("/")
                dir_name = parts[0] if len(parts) > 1 else "root"
                if dir_name not in modules_by_dir:
                    modules_by_dir[dir_name] = []
                if ent.name not in modules_by_dir[dir_name]:
                    modules_by_dir[dir_name].append(ent.name)

        if not modules_by_dir:
            modules_by_dir = {"app": ["main", "router", "models"]}

        # Render subgraphs for top modules (up to 8 directories)
        dir_keys = list(modules_by_dir.keys())[:8]
        dir_node_map: Dict[str, str] = {}

        for dir_name in dir_keys:
            dir_node = self._clean_node_id(dir_name, prefix="pkg")
            dir_node_map[dir_name] = dir_node
            items = modules_by_dir[dir_name][:4]

            lines.append(f'    subgraph Sub_{dir_node}["Module: {self._escape_label(dir_name)}"]')
            for item in items:
                item_node = self._clean_node_id(f"{dir_name}_{item}", prefix="mod")
                lines.append(f'        {item_node}["{self._escape_label(item)}"]')
                source_entities.append(f"entity:{dir_name}/{item}")
            lines.append('    end')

        # Detect cross-module relationships from dependencies
        inter_module_edges: Set[Tuple[str, str, str]] = set()
        for rel in dependencies:
            s_file = (rel.metadata_json or {}).get("source_file", "")
            t_file = (rel.metadata_json or {}).get("target_file", "")

            s_dir = s_file.replace("\\", "/").split("/")[0] if s_file else None
            t_dir = t_file.replace("\\", "/").split("/")[0] if t_file else None

            if s_dir and t_dir and s_dir != t_dir and s_dir in dir_node_map and t_dir in dir_node_map:
                s_node = dir_node_map[s_dir]
                t_node = dir_node_map[t_dir]
                rel_kind = rel.relationship_type.lower()
                inter_module_edges.add((s_node, t_node, rel_kind))

        # Add edges
        if inter_module_edges:
            for s_n, t_n, kind in list(inter_module_edges)[:15]:
                lines.append(f'    Sub_{s_n} -->|{kind}| Sub_{t_n}')
        else:
            # Fallback linear module flow if cross-directory dependencies are absent
            nodes = [f"Sub_{dir_node_map[d]}" for d in dir_keys]
            for i in range(len(nodes) - 1):
                lines.append(f'    {nodes[i]} --> {nodes[i+1]}')

        mermaid_code = "\n".join(lines)
        description = (
            f"Module boundaries and cross-package dependencies across {len(dir_keys)} primary "
            "subsystems detected in repository source code."
        )
        return mermaid_code, {}, source_entities, description

    def _build_dependency_diagram(
        self,
        project: Project,
        entities: List[CodeEntity],
        dependencies: List[DependencyRelationship],
    ) -> Tuple[str, Dict[str, Any], List[str], str]:
        """
        Synthesizes Component Dependencies Diagram.
        Renders the highest-connectivity classes, modules, and functions
        with directional labels (calls, imports, extends, uses).
        """
        lines = ["flowchart TD"]
        source_entities: List[str] = []

        # Color and style classes
        lines.append("    classDef classNode fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef funcNode fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef modNode fill:#1e293b,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;")

        # Compute degree for each entity in dependencies
        degrees: Dict[str, int] = {}
        for rel in dependencies:
            src = getattr(rel, "source", None) or getattr(rel, "source_name", "")
            tgt = getattr(rel, "target", None) or getattr(rel, "target_name", "")
            if src:
                degrees[src] = degrees.get(src, 0) + 1
            if tgt:
                degrees[tgt] = degrees.get(tgt, 0) + 1

        # Select top 25 nodes
        sorted_nodes = sorted(degrees.keys(), key=lambda k: degrees[k], reverse=True)[:25]
        active_nodes = set(sorted_nodes)

        # If few relationships, take classes and functions
        if len(active_nodes) < 5:
            for ent in entities[:15]:
                active_nodes.add(ent.name)

        # Entity type lookup
        entity_types: Dict[str, str] = {e.name: e.entity_type for e in entities}

        # Render nodes
        rendered_nodes: Dict[str, str] = {}
        for name in active_nodes:
            nid = self._clean_node_id(name, prefix="comp")
            etype = entity_types.get(name, "MODULE")
            css_class = "classNode" if etype == "CLASS" else ("funcNode" if etype in ("FUNCTION", "METHOD") else "modNode")
            shape_open, shape_close = ("[", "]") if etype == "CLASS" else (("(", ")") if etype in ("FUNCTION", "METHOD") else ("[[", "]]"))

            label = f"{name} ({etype.title()})" if etype != "MODULE" else name
            lines.append(f'    {nid}{shape_open}"{self._escape_label(label)}"{shape_close}:::{css_class}')
            rendered_nodes[name] = nid
            source_entities.append(f"entity:{etype}:{name}")

        # Render edges
        edges_rendered = 0
        for rel in dependencies:
            src = getattr(rel, "source", None) or getattr(rel, "source_name", "")
            tgt = getattr(rel, "target", None) or getattr(rel, "target_name", "")
            if src in rendered_nodes and tgt in rendered_nodes and src != tgt:
                s_id = rendered_nodes[src]
                t_id = rendered_nodes[tgt]
                label = rel.relationship_type.lower()
                lines.append(f'    {s_id} -->|{label}| {t_id}')
                edges_rendered += 1
                if edges_rendered >= 35:
                    break

        if edges_rendered == 0 and len(rendered_nodes) > 1:
            keys = list(rendered_nodes.values())
            for i in range(min(5, len(keys) - 1)):
                lines.append(f'    {keys[i]} --> {keys[i+1]}')

        mermaid_code = "\n".join(lines)
        description = (
            f"Component dependency graph featuring {len(rendered_nodes)} key code entities "
            f"and {edges_rendered} static relationships (calls, imports, inheritance)."
        )
        return mermaid_code, {}, source_entities, description

    def _build_api_service_relationship(
        self,
        project: Project,
        apis: List[APIEndpoint],
        entities: List[CodeEntity],
        dependencies: List[DependencyRelationship],
        db_models: List[DatabaseModel],
    ) -> Tuple[str, Dict[str, Any], List[str], str]:
        """
        Synthesizes API-to-Service Relationships.
        Traces:
        REST API Endpoints -> Handlers -> Domain Services -> Database Models.
        """
        lines = ["flowchart LR"]
        source_entities: List[str] = []

        # 1. Endpoints
        lines.append('    subgraph Endpoints["HTTP Endpoints"]')
        ep_map: Dict[str, str] = {}
        for idx, ep in enumerate(apis[:8]):
            ep_id = f"ep_{idx}"
            ep_label = f"{ep.method} {ep.path}"
            lines.append(f'        {ep_id}["{self._escape_label(ep_label)}"]')
            ep_map[ep.id] = ep_id
            source_entities.append(f"api:{ep.method}:{ep.path}")
        if not apis:
            lines.append('        ep_demo["GET /api/v1/health"]')
            ep_map["demo"] = "ep_demo"
        lines.append('    end')

        # 2. Handlers
        lines.append('    subgraph Handlers["Route Handlers"]')
        handler_map: Dict[str, str] = {}
        for idx, ep in enumerate(apis[:8]):
            h_name = ep.handler_name or f"handler_{idx}"
            h_id = self._clean_node_id(f"h_{h_name}_{idx}", prefix="h")
            lines.append(f'        {h_id}["{self._escape_label(h_name)}()"]')
            handler_map[ep.id] = h_id
            source_entities.append(f"handler:{h_name}")
        if not apis:
            lines.append('        h_demo["health_check()"]')
            handler_map["demo"] = "h_demo"
        lines.append('    end')

        # 3. Domain Services
        lines.append('    subgraph Services["Domain Services"]')
        service_classes = [e for e in entities if e.entity_type == "CLASS" and ("service" in e.name.lower() or "client" in e.name.lower() or "manager" in e.name.lower())][:6]
        if not service_classes:
            service_classes = [e for e in entities if e.entity_type == "CLASS"][:4]

        svc_nodes: List[str] = []
        for svc in service_classes:
            s_id = self._clean_node_id(svc.name, prefix="svc")
            lines.append(f'        {s_id}["{self._escape_label(svc.name)}"]')
            svc_nodes.append(s_id)
            source_entities.append(f"service:{svc.name}")
        if not svc_nodes:
            lines.append('        svc_app["ApplicationService"]')
            svc_nodes.append("svc_app")
        lines.append('    end')

        # 4. Database Models
        lines.append('    subgraph Models["Database Models"]')
        model_nodes: List[str] = []
        for dm in db_models[:6]:
            m_id = self._clean_node_id(dm.name, prefix="dbm")
            lines.append(f'        {m_id}[("({self._escape_label(dm.name)})")]')
            model_nodes.append(m_id)
            source_entities.append(f"model:{dm.name}")
        if not model_nodes:
            lines.append('        dbm_app[("(Database Storage)")]')
            model_nodes.append("dbm_app")
        lines.append('    end')

        # Connect Endpoints -> Handlers
        for ep_key, ep_nid in ep_map.items():
            if ep_key in handler_map:
                h_nid = handler_map[ep_key]
                lines.append(f'    {ep_nid} -->|dispatches| {h_nid}')

        # Connect Handlers -> Services
        for h_nid in handler_map.values():
            target_svc = svc_nodes[0]
            lines.append(f'    {h_nid} -->|invokes| {target_svc}')

        # Connect Services -> Models
        for s_nid in svc_nodes:
            target_m = model_nodes[0]
            lines.append(f'    {s_nid} -->|queries/updates| {target_m}')

        mermaid_code = "\n".join(lines)
        description = (
            f"End-to-end request lifecycle mapping {len(apis)} HTTP endpoints to controller handlers, "
            f"application services, and database entities."
        )
        return mermaid_code, {}, source_entities, description

    def _build_database_er(
        self,
        project: Project,
        db_models: List[DatabaseModel],
        db_relationships: List[DatabaseRelationship],
    ) -> Tuple[str, Dict[str, Any], List[str], str]:
        """
        Synthesizes Database ER Diagram.
        Uses detected models, fields, primary/foreign keys, and relationships.
        """
        source_entities: List[str] = []
        if not db_models:
            fallback = (
                "erDiagram\n"
                "    %% No database ORM models or SQL tables detected\n"
                "    APPLICATION {\n"
                "        string status \"Ready\"\n"
                "    }\n"
            )
            return fallback, {}, ["status:no_models"], "Database ER diagram (no relational tables detected)."

        lines = ["erDiagram"]

        # 1. Render Relationships
        for rel in db_relationships:
            src = self._clean_node_id(rel.source_model, prefix="M")
            tgt = self._clean_node_id(rel.target_model, prefix="M")
            rel_type = (rel.relationship_type or "ONE_TO_MANY").upper()
            raw_label = rel.description or rel.back_populates or "relates"
            label = re.sub(r'[^a-zA-Z0-9_]', '_', raw_label).strip('_') or "relates"

            connector = "||--o{"
            if rel_type == "ONE_TO_ONE":
                connector = "||--||"
            elif rel_type in ("ONE_TO_MANY", "FOREIGN_KEY"):
                connector = "||--o{"
            elif rel_type == "MANY_TO_MANY":
                connector = "}o--o{"

            lines.append(f'    {src} {connector} {tgt} : "{label}"')
            source_entities.append(f"rel:{rel.source_model}->{rel.target_model}")

        lines.append("")

        # 2. Render Models with Fields
        for dm in db_models:
            m_ident = self._clean_node_id(dm.name, prefix="M")
            lines.append(f"    {m_ident} {{")
            source_entities.append(f"table:{dm.table_name or dm.name}")

            fields = dm.fields or []
            if not fields and isinstance(dm.metadata_json, dict):
                fields = dm.metadata_json.get("fields", [])

            for f in fields:
                fname = getattr(f, "name", None) or (f.get("name") if isinstance(f, dict) else "field")
                fname_clean = re.sub(r'[^a-zA-Z0-9_]', '_', fname)

                dtype = getattr(f, "data_type", None) or (f.get("data_type") if isinstance(f, dict) else "string")
                dtype_clean = re.sub(r'[^a-zA-Z0-9_]', '', dtype).lower() or "string"

                is_pk = getattr(f, "is_primary_key", False) or (f.get("is_primary_key", False) if isinstance(f, dict) else False)
                is_fk = getattr(f, "is_foreign_key", False) or (f.get("is_foreign_key", False) if isinstance(f, dict) else False)

                flags = []
                if is_pk:
                    flags.append("PK")
                if is_fk:
                    flags.append("FK")
                flag_str = f" {' '.join(flags)}" if flags else ""

                lines.append(f"        {dtype_clean} {fname_clean}{flag_str}")

            lines.append("    }")

        mermaid_code = "\n".join(lines)
        description = (
            f"Relational schema diagram detailing {len(db_models)} database models and "
            f"{len(db_relationships)} cardinality relationships."
        )
        return mermaid_code, {}, source_entities, description

    # =========================================================================
    # Public Execution Engine
    # =========================================================================

    async def generate_diagram(
        self,
        project_id: str,
        diagram_type: str,
        db: AsyncSession,
        include_flow_data: bool = True,
        use_llm_enhancement: bool = False,
        force_regenerate: bool = False,
    ) -> Diagram:
        """
        Generates or regenerates a single architecture diagram of the requested type.
        Validates Mermaid syntax before committing to the database.
        """
        canonical_type = self._normalize_type(diagram_type)
        if canonical_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported diagram type '{diagram_type}'. Supported: {', '.join(self.SUPPORTED_TYPES)}")

        # Fetch project with related analysis data
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.code_entities),
                selectinload(Project.dependency_relationships),
                selectinload(Project.api_endpoints),
                selectinload(Project.database_models).selectinload(DatabaseModel.fields),
                selectinload(Project.database_relationships),
            )
        )
        res = await db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        entities = project.code_entities or []
        dependencies = project.dependency_relationships or []
        apis = project.api_endpoints or []
        db_models = project.database_models or []
        db_relationships = project.database_relationships or []

        # Titles for diagram types
        type_titles = {
            "SYSTEM_ARCHITECTURE": f"{project.name} - High-Level System Architecture",
            "MODULE_ARCHITECTURE": f"{project.name} - Module Architecture & Boundaries",
            "DEPENDENCY_DIAGRAM": f"{project.name} - Component Dependency Graph",
            "API_SERVICE_RELATIONSHIP": f"{project.name} - API-to-Service Request Flow",
            "DATABASE_ER": f"{project.name} - Database Entity-Relationship Diagram",
        }
        title = type_titles.get(canonical_type, f"{project.name} - {canonical_type.title()} Diagram")

        # Synthesize Mermaid code, flow data, and grounded source entities
        if canonical_type == "SYSTEM_ARCHITECTURE":
            mermaid_code, flow_data, sources, desc = self._build_system_architecture(
                project, entities, dependencies, apis, db_models
            )
        elif canonical_type == "MODULE_ARCHITECTURE":
            mermaid_code, flow_data, sources, desc = self._build_module_architecture(
                project, entities, dependencies
            )
        elif canonical_type == "DEPENDENCY_DIAGRAM":
            mermaid_code, flow_data, sources, desc = self._build_dependency_diagram(
                project, entities, dependencies
            )
        elif canonical_type == "API_SERVICE_RELATIONSHIP":
            mermaid_code, flow_data, sources, desc = self._build_api_service_relationship(
                project, apis, entities, dependencies, db_models
            )
        elif canonical_type == "DATABASE_ER":
            mermaid_code, flow_data, sources, desc = self._build_database_er(
                project, db_models, db_relationships
            )
        else:
            raise ValueError(f"Unknown diagram type {canonical_type}")

        # Mermaid Syntax Validation
        is_valid, validation_error = validate_mermaid_syntax(mermaid_code)
        if not is_valid:
            logger.error(f"Mermaid validation failed for {canonical_type}: {validation_error}")
            # Safe minimal fallback diagram
            mermaid_code = (
                f"flowchart TB\n"
                f"    ErrNode[\"Diagram generation syntax check: {self._escape_label(validation_error or 'Syntax error')}\"]\n"
            )

        # Optional LLM Enhancement (Title & description only, never architecture invention)
        if use_llm_enhancement:
            try:
                llm = get_llm_client()
                if llm.is_configured():
                    prompt = (
                        f"Provide a concise 1-sentence technical description and polished title for a {canonical_type} diagram "
                        f"of the project '{project.name}'.\n"
                        f"Detected components: {', '.join(sources[:12])}.\n"
                        "Do not invent components not mentioned."
                    )
                    llm_resp = await llm.generate(
                        prompt=prompt,
                        system_prompt="You are a precise software architecture documentation assistant.",
                        temperature=0.2,
                    )
                    if llm_resp and len(llm_resp.strip()) > 10:
                        desc = llm_resp.strip()
            except Exception as e:
                logger.warning(f"Optional LLM enhancement skipped: {e}")

        # Check existing record in DB (handling legacy aliases like 'er' or 'architecture')
        match_types = [canonical_type]
        if canonical_type == "DATABASE_ER":
            match_types.append("er")
        elif canonical_type == "SYSTEM_ARCHITECTURE":
            match_types.append("architecture")
        elif canonical_type == "DEPENDENCY_DIAGRAM":
            match_types.append("dependency")

        diag_stmt = (
            select(Diagram)
            .where(
                Diagram.project_id == project_id,
                Diagram.diagram_type.in_(match_types),
            )
        )
        diag_res = await db.execute(diag_stmt)
        existing = diag_res.scalars().first()

        now = datetime.now(timezone.utc)
        meta = {
            "validation_passed": is_valid,
            "source_entities_count": len(sources),
            "generated_at": now.isoformat(),
            "pipeline": "static_code_analysis",
        }

        if existing:
            existing.diagram_type = canonical_type
            existing.title = title
            existing.description = desc
            existing.mermaid_code = mermaid_code
            existing.flow_data = flow_data if include_flow_data else None
            existing.source_entities = sources
            existing.version = existing.version + 1
            existing.metadata_json = meta
            existing.updated_at = now
            diagram_obj = existing
        else:
            diagram_obj = Diagram(
                project_id=project_id,
                diagram_type=canonical_type,
                title=title,
                description=desc,
                mermaid_code=mermaid_code,
                flow_data=flow_data if include_flow_data else None,
                source_entities=sources,
                version=1,
                metadata_json=meta,
                created_at=now,
                updated_at=now,
            )
            db.add(diagram_obj)

        await db.commit()
        await db.refresh(diagram_obj)
        logger.info(f"Generated diagram '{canonical_type}' (v{diagram_obj.version}) for project {project_id}")
        return diagram_obj

    async def generate_all_diagrams(
        self,
        project_id: str,
        diagram_types: Optional[List[str]],
        db: AsyncSession,
        include_flow_data: bool = True,
        use_llm_enhancement: bool = False,
        force_regenerate: bool = False,
    ) -> DiagramGenerateResponse:
        """
        Generates all 5 architecture diagram types (or the requested subset) for a project.
        """
        target_types = self.SUPPORTED_TYPES
        if diagram_types:
            target_types = [self._normalize_type(t) for t in diagram_types]

        results: List[Diagram] = []
        for dtype in target_types:
            diag = await self.generate_diagram(
                project_id=project_id,
                diagram_type=dtype,
                db=db,
                include_flow_data=include_flow_data,
                use_llm_enhancement=use_llm_enhancement,
                force_regenerate=force_regenerate,
            )
            results.append(diag)

        responses = [DiagramResponse.model_validate(d) for d in results]
        return DiagramGenerateResponse(
            status="SUCCESS",
            project_id=project_id,
            total_generated=len(responses),
            diagrams=responses,
            message=f"Successfully generated {len(responses)} architecture diagrams.",
        )

    async def list_diagrams(
        self,
        project_id: str,
        db: AsyncSession,
        diagram_type: Optional[str] = None,
    ) -> List[DiagramResponse]:
        """Lists all stored architecture diagrams for a project with optional type filter."""
        stmt = select(Diagram).where(Diagram.project_id == project_id)
        if diagram_type:
            canonical = self._normalize_type(diagram_type)
            match_types = [canonical]
            if canonical == "DATABASE_ER":
                match_types.append("er")
            elif canonical == "SYSTEM_ARCHITECTURE":
                match_types.append("architecture")
            elif canonical == "DEPENDENCY_DIAGRAM":
                match_types.append("dependency")
            stmt = stmt.where(Diagram.diagram_type.in_(match_types))

        stmt = stmt.order_by(Diagram.diagram_type.asc())
        res = await db.execute(stmt)
        diagrams = res.scalars().all()
        return [DiagramResponse.model_validate(d) for d in diagrams]

    async def get_diagram_by_id(
        self,
        project_id: str,
        diagram_id: str,
        db: AsyncSession,
    ) -> DiagramResponse:
        """Retrieves a single diagram by ID."""
        stmt = select(Diagram).where(
            Diagram.project_id == project_id,
            Diagram.id == diagram_id,
        )
        res = await db.execute(stmt)
        diagram = res.scalar_one_or_none()
        if not diagram:
            raise ValueError(f"Diagram with ID '{diagram_id}' not found for project '{project_id}'")
        return DiagramResponse.model_validate(diagram)

    async def regenerate_diagram(
        self,
        project_id: str,
        diagram_id: str,
        db: AsyncSession,
    ) -> DiagramResponse:
        """Regenerates a specific diagram by ID, refreshing analysis context and incrementing version."""
        stmt = select(Diagram).where(
            Diagram.project_id == project_id,
            Diagram.id == diagram_id,
        )
        res = await db.execute(stmt)
        diagram = res.scalar_one_or_none()
        if not diagram:
            raise ValueError(f"Diagram with ID '{diagram_id}' not found for project '{project_id}'")

        updated = await self.generate_diagram(
            project_id=project_id,
            diagram_type=diagram.diagram_type,
            db=db,
            include_flow_data=True,
            force_regenerate=True,
        )
        return DiagramResponse.model_validate(updated)


diagram_service = DiagramService()
