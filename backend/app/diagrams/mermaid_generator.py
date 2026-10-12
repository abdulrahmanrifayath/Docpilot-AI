from typing import Any, Dict, List


class MermaidGenerator:
    def generate_architecture_diagram(
        self,
        repo_name: str,
        frameworks: List[str],
        apis: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        folder_purposes: Dict[str, str],
    ) -> str:
        """Generates a comprehensive Mermaid Architecture diagram with layered subgraphs."""
        lines = [
            "graph TB",
            "    %% System Architecture Diagram",
            "    classDef client fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:#fff;",
            "    classDef presentation fill:#8b5cf6,stroke:#6d28d9,stroke-width:2px,color:#fff;",
            "    classDef routing fill:#06b6d4,stroke:#0891b2,stroke-width:2px,color:#fff;",
            "    classDef logic fill:#10b981,stroke:#059669,stroke-width:2px,color:#fff;",
            "    classDef data fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff;",
            "    classDef ext fill:#64748b,stroke:#475569,stroke-width:2px,color:#fff;",
            "",
            '    subgraph Clients["Clients & Consumers"]',
            '        web["Web Browser / Client App"]:::client',
            '        mobile["Mobile / API Client"]:::client',
            "    end",
            "",
        ]

        # Frontend layer if React or Vue detected
        has_frontend = any(f in frameworks for f in ["React", "Vue", "Next.js", "Angular"])
        if has_frontend:
            lines.extend([
                '    subgraph Presentation["Presentation Layer"]',
                '        ui["UI Components & Pages"]:::presentation',
                '        state["State Management & Hooks"]:::presentation',
                "    end",
                "",
                "    web --> ui",
                "    ui --> state",
                "    state --> api_gateway",
                "",
            ])
        else:
            lines.extend([
                "    web --> api_gateway",
                "    mobile --> api_gateway",
                "",
            ])

        # API & Routing Layer
        route_nodes = []
        if apis:
            # Group by tag
            tags = {a.get("tag", "General") for a in apis[:8]}
            for t in tags:
                node_id = f"route_{t.lower()}"
                route_nodes.append(f'        {node_id}["/{t.lower()} Router"]:::routing')
        else:
            route_nodes.append('        router_main["REST API Router"]:::routing')

        lines.extend([
            f'    subgraph Gateway["API & Routing Layer ({", ".join(frameworks[:2]) if frameworks else "API Gateway"})"]',
            '        api_gateway["API Entrypoint / CORS Middleware"]:::routing',
            *route_nodes,
            "    end",
            "",
            "    api_gateway --> " + (route_nodes[0].split("[")[0].strip() if route_nodes else "api_gateway"),
            "",
        ])

        # Business Logic Layer
        lines.extend([
            '    subgraph Core["Business Logic & Domain Layer"]',
            '        svc_auth["Authentication & Security"]:::logic',
            '        svc_core["Domain Business Services"]:::logic',
            '        svc_utils["Utility & Helper Services"]:::logic',
            "    end",
            "",
        ])
        for r_line in route_nodes:
            r_id = r_line.split("[")[0].strip()
            lines.append(f"    {r_id} --> svc_core")
        lines.append("    svc_core --> svc_auth")
        lines.append("")

        # Data Persistence Layer
        db_nodes = []
        if models:
            for m in models[:6]:
                node_id = f"model_{m['name'].lower()}"
                db_nodes.append(f'        {node_id}[("Model: {m["name"]}")]:::data')
        else:
            db_nodes.append('        db_main[("Application Database")]:::data')

        lines.extend([
            '    subgraph Persistence["Persistence & Storage Layer"]',
            '        orm["ORM / Session Layer"]:::data',
            *db_nodes,
            "    end",
            "",
            "    svc_core --> orm",
            "    orm --> " + (db_nodes[0].split("[")[0].strip() if db_nodes else "orm"),
            "",
        ])

        return "\n".join(lines)

    def generate_sequence_diagram(
        self,
        apis: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
    ) -> str:
        """Generates a Mermaid Sequence diagram for standard request lifecycle."""
        sample_endpoint = apis[0]["path"] if apis else "/api/resource"
        sample_method = apis[0]["method"] if apis else "POST"
        sample_model = models[0]["name"] if models else "Entity"

        return f"""sequenceDiagram
    autonumber
    actor Client as Client / Frontend
    participant API as API Router
    participant Auth as Auth Middleware
    participant Service as Domain Service
    participant DB as Database / ORM

    Client->>API: {sample_method} {sample_endpoint}
    activate API
    API->>Auth: Validate Credentials / Token
    activate Auth
    Auth-->>API: Authorized Context
    deactivate Auth

    API->>Service: Process Request(Payload)
    activate Service
    Service->>DB: Query / Mutate {sample_model}
    activate DB
    DB-->>Service: Record Result / Confirmation
    deactivate DB

    Service-->>API: Return Formatted Response
    deactivate Service

    API-->>Client: 200 OK (JSON Payload)
    deactivate API
"""

    def generate_er_diagram(self, database_analysis: Dict[str, Any]) -> str:
        """Generates a Mermaid ER Diagram representing database schema and foreign keys."""
        models = database_analysis.get("models", [])
        relationships = database_analysis.get("relationships", [])

        if not models:
            return """erDiagram
    APPLICATION_ENTITY {
        string id PK
        string name
        datetime created_at
    }
"""

        lines = ["erDiagram"]
        for m in models[:12]:
            lines.append(f"    {m['name'].upper()} {{")
            for f in m.get("fields", [])[:10]:
                pk_flag = "PK" if f.get("is_primary_key") else ""
                fk_flag = "FK" if f.get("is_foreign_key") else ""
                flag = f"{pk_flag} {fk_flag}".strip()
                dtype = f.get("data_type", "string").replace(" ", "_")
                fname = f.get("name", "field")
                lines.append(f"        {dtype} {fname} {flag}".rstrip())
            lines.append("    }")

        for r in relationships[:15]:
            src = r.get("source_model", "").upper()
            tgt = r.get("target_model", "").upper()
            if src and tgt and src != tgt:
                rel_type = r.get("type", "many_to_one")
                if rel_type in ("one_to_many", "one_to_many_rel"):
                    lines.append(f'    {src} ||--o{{ {tgt} : "has"')
                elif rel_type in ("many_to_many",):
                    lines.append(f'    {src} }}o--o{{ {tgt} : "references"')
                else:
                    lines.append(f'    {src} }}o--|| {tgt} : "belongs_to"')

        return "\n".join(lines)

    def generate_dependency_diagram(self, dependency_analysis: Dict[str, Any]) -> str:
        """Generates a Mermaid Component/Dependency graph."""
        lines = [
            "graph LR",
            "    classDef core fill:#f97316,stroke:#c2410c,stroke-width:2px,color:#fff;",
            "    classDef module fill:#0284c7,stroke:#0369a1,stroke-width:1px,color:#fff;",
            "",
        ]

        edges = dependency_analysis.get("edges", [])[:25]
        core_files = {c["file"] for c in dependency_analysis.get("core_modules", [])[:5]}

        seen_nodes = set()
        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            src_id = "n_" + src.replace("/", "_").replace(".", "_").replace("-", "_")
            tgt_id = "n_" + tgt.replace("/", "_").replace(".", "_").replace("-", "_")

            if src not in seen_nodes:
                c_style = ":::core" if src in core_files else ":::module"
                lines.append(f'    {src_id}["{src}"]{c_style}')
                seen_nodes.add(src)

            if tgt not in seen_nodes:
                c_style = ":::core" if tgt in core_files else ":::module"
                lines.append(f'    {tgt_id}["{tgt}"]{c_style}')
                seen_nodes.add(tgt)

            lines.append(f"    {src_id} --> {tgt_id}")

        if len(lines) <= 4:
            lines.append('    app["Application Core"] --> models["Data Models"]')
            lines.append('    app --> services["Services"]')

        return "\n".join(lines)
