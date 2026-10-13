import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.core.config import settings
from app.models.project import (
    Project,
    Document,
    CodeEntity,
    DependencyNode,
    DependencyRelationship,
    APIEndpoint,
    DatabaseModel,
    KnowledgeNode,
    KnowledgeEdge,
)
from app.schemas.project import DocumentResponse, DocumentGenerateResponse
from app.ai.llm_client import (
    LLMClient,
    create_llm_client,
    LLMNotConfiguredError,
    default_llm_client,
)

logger = logging.getLogger("docpilot")

# Supported Documentation Types
DOC_TYPES = [
    "PROJECT_OVERVIEW",
    "README",
    "FOLDER_DOCS",
    "FILE_DOCS",
    "CLASS_DOCS",
    "FUNCTION_DOCS",
    "API_DOCS",
    "DATABASE_DOCS",
    "ARCHITECTURE_OVERVIEW",
]


class DocumentationService:
    """AI Documentation Generation Engine for DocPilot AI."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm_client = llm_client or default_llm_client

    def get_client(self) -> LLMClient:
        # Re-instantiate or get client to pick up runtime settings changes
        return create_llm_client()

    def is_configured(self) -> bool:
        return self.get_client().is_configured()

    # =========================================================================
    # CONTEXT BUILDER METHODS (Never send entire repo; assemble targeted context)
    # =========================================================================

    async def _build_project_overview_context(
        self, project: Project, db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = ["project:metadata"]
        lines = [
            f"PROJECT NAME: {project.name}",
            f"DESCRIPTION: {project.description or 'No description provided'}",
            f"SOURCE TYPE: {project.source_type}",
            f"DETECTED LANGUAGES: {list((project.languages or {}).keys())}",
            f"DETECTED FRAMEWORKS: {project.frameworks or []}",
            f"INFRASTRUCTURE ASSETS: {project.infrastructure or []}",
            f"STATISTICS: {project.stats or {}}",
        ]

        # Add top-level folder structure summary
        structure = project.structure or {}
        root_children = structure.get("children", [])
        if root_children:
            top_dirs = [c["name"] for c in root_children if c.get("type") == "directory"]
            top_files = [c["name"] for c in root_children if c.get("type") == "file"]
            lines.append(f"TOP-LEVEL DIRECTORIES: {top_dirs}")
            lines.append(f"ROOT FILES: {top_files}")

        # Top entities sample
        res = await db.execute(
            select(CodeEntity).where(CodeEntity.project_id == project.id).limit(15)
        )
        entities = res.scalars().all()
        if entities:
            ent_summary = [f"{e.entity_type} {e.name} in {e.file_path}" for e in entities]
            lines.append(f"KEY CODE ENTITIES: {', '.join(ent_summary)}")
            source_entities.extend([f"{e.file_path}:{e.name}" for e in entities])

        return "\n".join(lines), source_entities

    async def _build_readme_context(
        self, project: Project, db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = ["project:readme_context"]
        lines = [
            f"PROJECT NAME: {project.name}",
            f"DESCRIPTION: {project.description or 'A software project analyzed by DocPilot AI'}",
            f"FRAMEWORKS: {project.frameworks or []}",
            f"LANGUAGES: {list((project.languages or {}).keys())}",
        ]

        # Add discovered APIs sample
        api_res = await db.execute(
            select(APIEndpoint).where(APIEndpoint.project_id == project.id).limit(10)
        )
        apis = api_res.scalars().all()
        if apis:
            lines.append("CORE API ENDPOINTS:")
            for ep in apis:
                lines.append(f"  - {ep.method} {ep.path} (handler: {ep.handler_name})")
                source_entities.append(f"api:{ep.method}:{ep.path}")

        # Add database models sample
        db_res = await db.execute(
            select(DatabaseModel).where(DatabaseModel.project_id == project.id).limit(10)
        )
        models = db_res.scalars().all()
        if models:
            lines.append("CORE DATABASE MODELS:")
            for m in models:
                lines.append(f"  - {m.name} (table: {m.table_name or m.name})")
                source_entities.append(f"model:{m.name}")

        return "\n".join(lines), source_entities

    async def _build_architecture_context(
        self, project: Project, db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = ["project:architecture_topology"]
        lines = [
            f"PROJECT NAME: {project.name}",
            f"FRAMEWORKS: {project.frameworks or []}",
            f"INFRASTRUCTURE: {project.infrastructure or []}",
        ]

        # Knowledge edges summary (Cross-tier bridge connections)
        edges_res = await db.execute(
            select(KnowledgeEdge).where(KnowledgeEdge.project_id == project.id).limit(50)
        )
        edges = edges_res.scalars().all()
        if edges:
            lines.append("CROSS-TIER ARCHITECTURAL RELATIONSHIPS:")
            for e in edges:
                lines.append(f"  - {e.source_name} ({e.source_type}) -> [{e.relationship_type}] -> {e.target_name} ({e.target_type})")
                source_entities.append(f"{e.source_name}->{e.target_name}")

        return "\n".join(lines), source_entities

    async def _build_api_context(
        self, project: Project, db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        api_res = await db.execute(
            select(APIEndpoint).where(APIEndpoint.project_id == project.id)
        )
        apis = api_res.scalars().all()
        if not apis:
            return "No backend API routes were detected in this repository.", []

        lines = [f"TOTAL DETECTED APIS: {len(apis)}"]
        for ep in apis:
            source_entities.append(f"api:{ep.method}:{ep.path}")
            lines.append(f"\nENDPOINT: {ep.method} {ep.path}")
            lines.append(f"  File Location: {ep.file_path}")
            lines.append(f"  Handler: {ep.handler_name}")
            lines.append(f"  Authentication Required: {ep.authentication_required}")
            if ep.tags:
                lines.append(f"  Tags: {ep.tags}")
            if ep.request_schema:
                lines.append(f"  Request Schema: {ep.request_schema}")
            if ep.response_schema:
                lines.append(f"  Response Schema: {ep.response_schema}")

        return "\n".join(lines), source_entities

    async def _build_database_context(
        self, project: Project, db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        db_res = await db.execute(
            select(DatabaseModel).where(DatabaseModel.project_id == project.id)
        )
        models = db_res.scalars().all()
        if not models:
            return "No database ORM schema or SQL models were detected in this repository.", []

        lines = [f"TOTAL DETECTED DATABASE MODELS: {len(models)}"]
        for m in models:
            source_entities.append(f"database:{m.name}")
            lines.append(f"\nMODEL: {m.name} (Table: {m.table_name})")
            lines.append(f"  Source File: {m.file_path}")
            fields = getattr(m, "fields", None) or (m.metadata_json or {}).get("fields", [])
            if fields:
                lines.append("  Fields / Columns:")
                for f in fields:
                    f_name = getattr(f, "name", None) if not isinstance(f, dict) else f.get("name")
                    f_type = getattr(f, "data_type", None) if not isinstance(f, dict) else f.get("data_type")
                    is_pk = getattr(f, "is_primary_key", False) if not isinstance(f, dict) else f.get("is_primary_key", False)
                    is_fk = getattr(f, "is_foreign_key", False) if not isinstance(f, dict) else f.get("is_foreign_key", False)
                    fk_target = getattr(f, "foreign_key_target", None) if not isinstance(f, dict) else f.get("foreign_key_target")
                    pk_str = " [PK]" if is_pk else ""
                    fk_str = f" [FK -> {fk_target}]" if is_fk else ""
                    lines.append(f"    - {f_name}: {f_type}{pk_str}{fk_str}")
            rels = (m.metadata_json or {}).get("relationships", [])
            if rels:
                lines.append("  Relationships:")
                for r in rels:
                    lines.append(f"    - {r.get('relationship_type')}: target '{r.get('target_model')}'")

        return "\n".join(lines), source_entities

    async def _build_folder_context(
        self, project: Project, target_path: Optional[str], db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        folder_path = target_path or "root"
        lines = [f"FOLDER: {folder_path}"]

        # Find files matching this folder
        query = select(CodeEntity).where(CodeEntity.project_id == project.id)
        if target_path and target_path != "root":
            query = query.where(CodeEntity.file_path.startswith(target_path))
        query = query.limit(30)

        res = await db.execute(query)
        entities = res.scalars().all()
        if entities:
            lines.append("CONTAINED CODE ENTITIES:")
            for e in entities:
                lines.append(f"  - [{e.entity_type}] {e.name} ({e.file_path}:{e.start_line}-{e.end_line})")
                source_entities.append(f"{e.file_path}:{e.name}")
        else:
            lines.append("No parsed code entities under this directory.")

        return "\n".join(lines), source_entities

    async def _build_file_context(
        self, project: Project, target_path: Optional[str], db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        if not target_path:
            # Pick primary source file if not provided
            res = await db.execute(
                select(CodeEntity.file_path).where(CodeEntity.project_id == project.id).limit(1)
            )
            target_path = res.scalar() or "main.py"

        lines = [f"FILE PATH: {target_path}"]
        source_entities.append(f"file:{target_path}")

        # Entities in file
        ent_res = await db.execute(
            select(CodeEntity).where(
                CodeEntity.project_id == project.id,
                CodeEntity.file_path == target_path,
            )
        )
        entities = ent_res.scalars().all()
        if entities:
            lines.append("ENTITIES DECLARED IN THIS FILE:")
            for e in entities:
                sig = f" signature: {e.signature}" if e.signature else ""
                lines.append(f"  - [{e.entity_type}] {e.name} (Lines {e.start_line}-{e.end_line}){sig}")
                source_entities.append(f"{target_path}:{e.name}")

        # Relevant file code chunk (only relevant lines, never entire repository)
        if project.repository_path:
            full_path = Path(project.repository_path) / target_path
            if full_path.exists() and full_path.is_file():
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_lines = f.readlines()
                    # Include up to first 120 lines to respect context budget
                    chunk = "".join(file_lines[:120])
                    lines.append(f"\nSOURCE CODE EXCERPT (first {min(120, len(file_lines))} lines):\n```\n{chunk}\n```")
                except Exception as ex:
                    logger.warning(f"Could not read source file chunk: {ex}")

        return "\n".join(lines), source_entities

    async def _build_class_context(
        self, project: Project, target_entity_id: Optional[str], db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        query = select(CodeEntity).where(
            CodeEntity.project_id == project.id,
            CodeEntity.entity_type == "CLASS",
        )
        if target_entity_id:
            query = query.where(
                (CodeEntity.id == target_entity_id) | (CodeEntity.name == target_entity_id)
            )
        query = query.limit(5)
        res = await db.execute(query)
        classes = res.scalars().all()

        if not classes:
            return "No class definitions found in project AST entities.", []

        lines = []
        for c in classes:
            source_entities.append(f"{c.file_path}:{c.name}")
            lines.append(f"CLASS: {c.name}")
            lines.append(f"  File: {c.file_path}:{c.start_line}-{c.end_line}")
            meta = c.metadata_json or {}
            bases = meta.get("bases", [])
            if bases:
                lines.append(f"  Inherits from: {', '.join(bases)}")
            doc = meta.get("docstring")
            if doc:
                lines.append(f"  Docstring: {doc}")

            # Methods inside this class
            methods_res = await db.execute(
                select(CodeEntity).where(
                    CodeEntity.project_id == project.id,
                    CodeEntity.file_path == c.file_path,
                    CodeEntity.parent_entity == c.name,
                )
            )
            methods = methods_res.scalars().all()
            if methods:
                lines.append("  Methods:")
                for m in methods:
                    lines.append(f"    - {m.name} (Lines {m.start_line}-{m.end_line}): {m.signature or ''}")

        return "\n".join(lines), source_entities

    async def _build_function_context(
        self, project: Project, target_entity_id: Optional[str], db: AsyncSession
    ) -> Tuple[str, List[str]]:
        source_entities = []
        query = select(CodeEntity).where(
            CodeEntity.project_id == project.id,
            CodeEntity.entity_type.in_(["FUNCTION", "METHOD"]),
        )
        if target_entity_id:
            query = query.where(
                (CodeEntity.id == target_entity_id) | (CodeEntity.name == target_entity_id)
            )
        query = query.limit(10)
        res = await db.execute(query)
        functions = res.scalars().all()

        if not functions:
            return "No function or method definitions found in project AST entities.", []

        lines = []
        for fn in functions:
            source_entities.append(f"{fn.file_path}:{fn.name}")
            lines.append(f"FUNCTION: {fn.name}")
            lines.append(f"  Location: {fn.file_path}:{fn.start_line}-{fn.end_line}")
            lines.append(f"  Signature: {fn.signature or 'def ' + fn.name + '()'}")
            meta = fn.metadata_json or {}
            if meta.get("decorators"):
                lines.append(f"  Decorators: {meta.get('decorators')}")
            if meta.get("docstring"):
                lines.append(f"  Docstring: {meta.get('docstring')}")

        return "\n".join(lines), source_entities

    # =========================================================================
    # SYSTEM PROMPT BUILDER (Strict Grounding Rules)
    # =========================================================================

    def _build_system_prompt(self, document_type: str) -> str:
        return (
            "You are DocPilot AI, a senior technical writer and software architect.\n"
            "Generate high-quality, professional Markdown documentation based strictly on the supplied repository context.\n\n"
            "STRICT GROUNDING RULES:\n"
            "1. Base all explanations directly on the supplied repository context.\n"
            "2. Clearly distinguish detected facts from inferred explanations.\n"
            "3. NEVER invent components, modules, functions, or external services not found in the context.\n"
            "4. NEVER claim functionality or features not supported by the code.\n"
            "5. Use clear, concise, technical, and developer-friendly prose.\n"
            "6. Always reference relevant source files (e.g. `path/to/file.py:L1-L50`) and entity names where available.\n"
            "7. Output valid, beautiful GitHub-flavored Markdown formatted with headers, lists, and syntax-highlighted code blocks.\n"
        )

    def _build_user_prompt(
        self, project_name: str, doc_type: str, context: str, target_name: Optional[str] = None
    ) -> str:
        type_titles = {
            "PROJECT_OVERVIEW": f"Comprehensive Project Overview for '{project_name}'",
            "README": f"Production-Ready README.md for '{project_name}'",
            "FOLDER_DOCS": f"Directory & Module Architecture Guide for '{target_name or 'project directories'}'",
            "FILE_DOCS": f"Source File Technical Specification for '{target_name or 'source file'}'",
            "CLASS_DOCS": f"Object-Oriented Class Reference for '{target_name or 'project classes'}'",
            "FUNCTION_DOCS": f"Function & Method API Reference for '{target_name or 'project functions'}'",
            "API_DOCS": f"Backend REST API Reference Guide for '{project_name}'",
            "DATABASE_DOCS": f"Database Schema & Entity-Relationship Guide for '{project_name}'",
            "ARCHITECTURE_OVERVIEW": f"System Architecture & Cross-Tier Flow Specification for '{project_name}'",
        }
        title = type_titles.get(doc_type, f"{doc_type} Technical Document")

        return (
            f"Please generate the '{title}'.\n\n"
            "Here is the structured repository analysis context:\n"
            "-----------------------------------------\n"
            f"{context}\n"
            "-----------------------------------------\n\n"
            "Instructions:\n"
            f"- Structure the document cleanly with an introduction, detailed technical breakdown, source references, and code examples if appropriate.\n"
            "- Adhere strictly to the facts provided above.\n"
            "- If certain details (e.g. environment credentials) are absent from the context, explicitly state that they are configured via external environment variables.\n"
        )

    # =========================================================================
    # CORE GENERATION ENGINE PIPELINE
    # =========================================================================

    async def generate_document_single(
        self,
        project: Project,
        doc_type: str,
        db: AsyncSession,
        target_path: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> Document:
        client = self.get_client()
        if not client.is_configured():
            raise LLMNotConfiguredError(
                f"LLM Provider '{client.get_provider_name()}' is not configured. Please supply an API key in Settings.",
                provider=client.get_provider_name(),
            )

        # Context build according to document type
        if doc_type == "PROJECT_OVERVIEW":
            context, source_entities = await self._build_project_overview_context(project, db)
            title = f"{project.name} - Project Overview"
        elif doc_type == "README":
            context, source_entities = await self._build_readme_context(project, db)
            title = f"{project.name} - README"
        elif doc_type == "ARCHITECTURE_OVERVIEW":
            context, source_entities = await self._build_architecture_context(project, db)
            title = f"{project.name} - Architecture Overview"
        elif doc_type == "API_DOCS":
            context, source_entities = await self._build_api_context(project, db)
            title = f"{project.name} - API Documentation"
        elif doc_type == "DATABASE_DOCS":
            context, source_entities = await self._build_database_context(project, db)
            title = f"{project.name} - Database Documentation"
        elif doc_type == "FOLDER_DOCS":
            context, source_entities = await self._build_folder_context(project, target_path, db)
            title = f"Folder Documentation: {target_path or 'Root'}"
        elif doc_type == "FILE_DOCS":
            context, source_entities = await self._build_file_context(project, target_path, db)
            title = f"File Documentation: {target_path or 'Source'}"
        elif doc_type == "CLASS_DOCS":
            context, source_entities = await self._build_class_context(project, target_entity_id, db)
            title = f"Class Documentation: {target_entity_id or 'Core Classes'}"
        elif doc_type == "FUNCTION_DOCS":
            context, source_entities = await self._build_function_context(project, target_entity_id, db)
            title = f"Function Documentation: {target_entity_id or 'Core Functions'}"
        else:
            context, source_entities = await self._build_project_overview_context(project, db)
            title = f"{project.name} - {doc_type}"

        system_prompt = self._build_system_prompt(doc_type)
        user_prompt = self._build_user_prompt(
            project_name=project.name,
            doc_type=doc_type,
            context=context,
            target_name=target_path or target_entity_id,
        )

        content = await client.generate(prompt=user_prompt, system_prompt=system_prompt)

        # Check existing doc to update version or insert
        query = select(Document).where(
            Document.project_id == project.id,
            Document.document_type == doc_type,
        )
        if target_path:
            query = query.where(Document.target_path == target_path)
        if target_entity_id:
            query = query.where(Document.target_entity_id == target_entity_id)

        existing = (await db.execute(query)).scalars().first()

        now = datetime.now(timezone.utc)
        if existing and not force_regenerate:
            existing.version += 1
            existing.content = content
            existing.title = title
            existing.source_entities = source_entities
            existing.model = client.get_model_name()
            existing.generated_at = now
            existing.updated_at = now
            await db.commit()
            await db.refresh(existing)
            return existing
        elif existing and force_regenerate:
            existing.version += 1
            existing.content = content
            existing.title = title
            existing.source_entities = source_entities
            existing.model = client.get_model_name()
            existing.generated_at = now
            existing.updated_at = now
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            new_doc = Document(
                project_id=project.id,
                document_type=doc_type,
                title=title,
                content=content,
                target_path=target_path,
                target_entity_id=target_entity_id,
                source_entities=source_entities,
                model=client.get_model_name(),
                version=1,
                generated_at=now,
                metadata_json={
                    "char_count": len(content),
                    "provider": client.get_provider_name(),
                },
            )
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
            return new_doc

    async def generate_documentation(
        self,
        project_id: str,
        db: AsyncSession,
        document_types: Optional[List[str]] = None,
        target_path: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> DocumentGenerateResponse:
        client = self.get_client()
        if not client.is_configured():
            raise LLMNotConfiguredError(
                f"LLM Provider '{client.get_provider_name()}' is not configured with an API key. "
                "Please configure an API key in Settings to generate AI documentation.",
                provider=client.get_provider_name(),
            )

        # Retrieve project
        res = await db.execute(select(Project).where(Project.id == project_id))
        project = res.scalars().first()
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        # Determine types to generate
        types_to_generate = document_types or [
            "PROJECT_OVERVIEW",
            "README",
            "ARCHITECTURE_OVERVIEW",
            "API_DOCS",
            "DATABASE_DOCS",
        ]

        # Filter valid types
        valid_types = [t.upper() for t in types_to_generate if t.upper() in DOC_TYPES]
        if not valid_types:
            valid_types = ["PROJECT_OVERVIEW", "README"]

        generated_docs = []
        for dtype in valid_types:
            try:
                doc = await self.generate_document_single(
                    project=project,
                    doc_type=dtype,
                    db=db,
                    target_path=target_path,
                    target_entity_id=target_entity_id,
                    force_regenerate=force_regenerate,
                )
                generated_docs.append(DocumentResponse.model_validate(doc))
            except Exception as e:
                logger.error(f"Error generating {dtype} for project {project_id}: {e}")
                if isinstance(e, LLMNotConfiguredError):
                    raise e
                continue

        return DocumentGenerateResponse(
            status="COMPLETED",
            project_id=project_id,
            total_generated=len(generated_docs),
            documents=generated_docs,
            message=f"Successfully generated {len(generated_docs)} technical documentation documents.",
        )

    async def get_documents(
        self,
        project_id: str,
        db: AsyncSession,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[DocumentResponse]:
        query = select(Document).where(Document.project_id == project_id)
        if document_type:
            query = query.where(Document.document_type == document_type.upper())
        if search:
            query = query.where(
                (Document.title.ilike(f"%{search}%")) | (Document.content.ilike(f"%{search}%"))
            )
        query = query.order_by(Document.created_at.asc())

        res = await db.execute(query)
        docs = res.scalars().all()
        return [DocumentResponse.model_validate(d) for d in docs]

    async def get_document_by_id(
        self, project_id: str, document_id: str, db: AsyncSession
    ) -> DocumentResponse:
        res = await db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.id == document_id,
            )
        )
        doc = res.scalars().first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found in project '{project_id}'")
        return DocumentResponse.model_validate(doc)

    async def regenerate_document(
        self, project_id: str, document_id: str, db: AsyncSession
    ) -> DocumentResponse:
        client = self.get_client()
        if not client.is_configured():
            raise LLMNotConfiguredError(
                f"LLM Provider '{client.get_provider_name()}' is not configured with an API key. "
                "Please configure an API key in Settings.",
                provider=client.get_provider_name(),
            )

        res = await db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.id == document_id,
            )
        )
        doc = res.scalars().first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found")

        proj_res = await db.execute(select(Project).where(Project.id == project_id))
        project = proj_res.scalars().first()
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        updated_doc = await self.generate_document_single(
            project=project,
            doc_type=doc.document_type,
            db=db,
            target_path=doc.target_path,
            target_entity_id=doc.target_entity_id,
            force_regenerate=True,
        )
        return DocumentResponse.model_validate(updated_doc)


documentation_service = DocumentationService()
