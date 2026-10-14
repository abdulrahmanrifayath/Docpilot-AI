import logging
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import (
    Project,
    CodeEntity,
    APIEndpoint,
    DatabaseModel,
    Document,
    SequenceDiagram,
)
from app.ai.embeddings import embedding_service
from app.ai.vector_store import VectorChunk, vector_store

logger = logging.getLogger("docpilot")


class ProjectIndexerService:
    """
    Intelligent Vector Knowledge Base Indexer.
    Generates structured, repository-specific vector chunks for:
    - Files
    - Classes
    - Functions
    - APIs
    - Database Models
    - Documentation Sections
    - Sequence Flows
    """

    async def index_project(self, project_id: str, db: AsyncSession, force: bool = False) -> int:
        """
        Indexes all parsed artifacts of a project into the vector store.
        Returns the count of chunks created and indexed.
        """
        # If already indexed and not force, check existing index
        if not force:
            existing = vector_store.load_index(project_id)
            if existing and len(existing) > 0:
                logger.info(f"Project {project_id} already has {len(existing)} vector chunks indexed.")
                return len(existing)

        project = await db.get(Project, project_id)
        if not project:
            logger.warning(f"Project {project_id} not found for vector indexing.")
            return 0

        chunks: List[VectorChunk] = []
        chunk_idx = 1

        # 1. Index Project Overview & Metadata Chunk
        languages_summary = ", ".join(project.languages.keys()) if project.languages else "Various"
        frameworks_summary = ", ".join(project.frameworks) if project.frameworks else "None detected"
        overview_content = (
            f"Project: {project.name}. Description: {project.description or 'No description'}. "
            f"Languages: {languages_summary}. Frameworks: {frameworks_summary}. "
            f"Repository Path: {project.repository_path}."
        )
        vec = await embedding_service.get_embedding(overview_content)
        chunks.append(
            VectorChunk(
                id=f"proj_{project_id}_overview",
                project_id=project_id,
                chunk_type="file",
                title=f"Project Overview: {project.name}",
                file_path="README.md",
                start_line=1,
                end_line=10,
                content=overview_content,
                metadata={"category": "overview", "frameworks": project.frameworks},
                vector=vec,
            )
        )

        # 2. Index Code Entities: Classes
        class_res = await db.execute(
            select(CodeEntity).where(
                CodeEntity.project_id == project_id,
                CodeEntity.entity_type == "CLASS",
            )
        )
        classes = class_res.scalars().all()
        for cls in classes:
            meta = cls.metadata_json or {}
            methods = meta.get("methods", [])
            fields = meta.get("fields", [])
            methods_str = ", ".join(methods[:8]) if methods else "None"
            fields_str = ", ".join(fields[:8]) if fields else "None"
            docstr = meta.get("docstring", "")

            content = (
                f"Class {cls.name} in file {cls.file_path} (lines {cls.start_line}-{cls.end_line}). "
                f"Signature: {cls.signature or cls.name}. "
                f"Docstring: {docstr}. "
                f"Methods: {methods_str}. Fields: {fields_str}."
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"cls_{cls.id}",
                    project_id=project_id,
                    chunk_type="class",
                    title=f"Class {cls.name}",
                    file_path=cls.file_path,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    content=content,
                    entity_id=cls.id,
                    entity_type="CLASS",
                    metadata={"class_name": cls.name, "methods": methods},
                    vector=vec,
                )
            )

        # 3. Index Code Entities: Functions & Methods
        fn_res = await db.execute(
            select(CodeEntity).where(
                CodeEntity.project_id == project_id,
                CodeEntity.entity_type.in_(["FUNCTION", "METHOD"]),
            )
        )
        functions = fn_res.scalars().all()
        for fn in functions:
            meta = fn.metadata_json or {}
            params = meta.get("parameters", [])
            calls = meta.get("calls", [])
            docstr = meta.get("docstring", "")
            params_str = ", ".join(params[:6]) if params else "None"
            calls_str = ", ".join(calls[:6]) if calls else "None"

            content = (
                f"Function {fn.name}({params_str}) in {fn.file_path} (lines {fn.start_line}-{fn.end_line}). "
                f"Parent: {fn.parent_entity or 'Module'}. "
                f"Docstring: {docstr}. "
                f"Calls internal/external dependencies: {calls_str}."
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"fn_{fn.id}",
                    project_id=project_id,
                    chunk_type="function",
                    title=f"Function {fn.name}",
                    file_path=fn.file_path,
                    start_line=fn.start_line,
                    end_line=fn.end_line,
                    content=content,
                    entity_id=fn.id,
                    entity_type=fn.entity_type,
                    metadata={"function_name": fn.name, "calls": calls},
                    vector=vec,
                )
            )

        # 4. Index API Endpoints
        api_res = await db.execute(select(APIEndpoint).where(APIEndpoint.project_id == project_id))
        apis = api_res.scalars().all()
        for api in apis:
            req_info = api.request_schema or {}
            resp_info = api.response_schema or {}
            auth_str = "Authentication required" if api.authentication_required else "Public endpoint"
            tags_str = ", ".join(api.tags) if api.tags else "None"

            content = (
                f"API Route: {api.method} {api.path}. Handler function: {api.handler_name} "
                f"in file {api.file_path}. Security: {auth_str}. Tags: {tags_str}. "
                f"Request Schema: {req_info.get('body_model', 'None')}. "
                f"Response Model: {resp_info.get('model', 'None')}. "
                f"Parameters: {', '.join([p.get('name', '') for p in req_info.get('parameters', [])])}."
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"api_{api.id}",
                    project_id=project_id,
                    chunk_type="api",
                    title=f"API {api.method} {api.path}",
                    file_path=api.file_path,
                    start_line=1,
                    end_line=20,
                    content=content,
                    entity_id=api.id,
                    entity_type="API",
                    metadata={
                        "method": api.method,
                        "path": api.path,
                        "handler": api.handler_name,
                        "auth": api.authentication_required,
                    },
                    vector=vec,
                )
            )

        # 5. Index Database Models
        db_res = await db.execute(select(DatabaseModel).where(DatabaseModel.project_id == project_id))
        db_models = db_res.scalars().all()
        for model in db_models:
            fields_meta = model.fields_json or []
            field_names = [f.get("name", "") for f in fields_meta if isinstance(f, dict)]
            pks = [f.get("name", "") for f in fields_meta if isinstance(f, dict) and f.get("primary_key")]
            fks = [f.get("name", "") for f in fields_meta if isinstance(f, dict) and f.get("foreign_key")]

            content = (
                f"Database Model: {model.model_name} (table: '{model.table_name}') in file {model.file_path}. "
                f"ORM framework: {model.orm_framework or 'SQLAlchemy'}. "
                f"Primary Keys: {', '.join(pks)}. Foreign Keys: {', '.join(fks)}. "
                f"Columns & Fields: {', '.join(field_names[:12])}."
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"db_{model.id}",
                    project_id=project_id,
                    chunk_type="model",
                    title=f"Database Model {model.model_name} ({model.table_name})",
                    file_path=model.file_path,
                    start_line=1,
                    end_line=30,
                    content=content,
                    entity_id=model.id,
                    entity_type="DATABASE_MODEL",
                    metadata={
                        "model_name": model.model_name,
                        "table_name": model.table_name,
                        "fields": field_names,
                    },
                    vector=vec,
                )
            )

        # 6. Index Generated Documents (Phase 9)
        doc_res = await db.execute(select(Document).where(Document.project_id == project_id))
        docs = doc_res.scalars().all()
        for doc in docs:
            # Chunk document by sections if long, or entire content if concise
            doc_body = doc.content[:2000]
            content = (
                f"Documentation [{doc.document_type}]: {doc.title}. Target: {doc.target_path or 'Project'}. "
                f"Content: {doc_body}"
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"doc_{doc.id}",
                    project_id=project_id,
                    chunk_type="doc",
                    title=f"Doc: {doc.title}",
                    file_path=doc.target_path or "docs/",
                    start_line=1,
                    end_line=50,
                    content=content,
                    entity_id=doc.id,
                    entity_type="DOCUMENT",
                    metadata={"document_type": doc.document_type},
                    vector=vec,
                )
            )

        # 7. Index Sequence Flows (Phase 11)
        seq_res = await db.execute(select(SequenceDiagram).where(SequenceDiagram.project_id == project_id))
        sequences = seq_res.scalars().all()
        for seq in sequences:
            steps_meta = seq.steps or []
            steps_desc = "; ".join(
                [f"{s.get('source')} -> {s.get('target')}: {s.get('action')}" for s in steps_meta[:6]]
            )
            content = (
                f"Sequence Flow: {seq.name} (category: {seq.flow_category}). "
                f"Trigger endpoint: {seq.trigger_method} {seq.trigger_endpoint}. "
                f"Involved components: {', '.join(seq.involved_components or [])}. "
                f"Steps: {steps_desc}."
            )
            vec = await embedding_service.get_embedding(content)
            chunks.append(
                VectorChunk(
                    id=f"seq_{seq.id}",
                    project_id=project_id,
                    chunk_type="sequence",
                    title=f"Sequence Flow: {seq.name}",
                    file_path=seq.trigger_endpoint or "flows/",
                    start_line=1,
                    end_line=30,
                    content=content,
                    entity_id=seq.id,
                    entity_type="SEQUENCE_FLOW",
                    metadata={
                        "category": seq.flow_category,
                        "trigger": seq.trigger_endpoint,
                        "components": seq.involved_components,
                    },
                    vector=vec,
                )
            )

        # Save to vector store strictly under project_id
        vector_store.clear(project_id)
        vector_store.add_chunks(project_id, chunks)

        logger.info(f"Vector knowledge base indexed for project {project_id}: {len(chunks)} chunks created.")
        return len(chunks)


project_indexer_service = ProjectIndexerService()
