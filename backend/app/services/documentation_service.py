import os
import time
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.project import Project
from backend.app.models.documentation import DocumentationRecord
from backend.app.schemas.documentation import (
    DocumentType,
    DocumentationResponse,
    DocumentationListResponse,
    DocStatusResponse,
    DocumentationGenerationResult,
)
from backend.app.llm.factory import get_llm_client
from backend.app.generators.doc_generator import DocumentationGenerator

from backend.app.services.scan_service import ScanService
from backend.app.services.parse_service import ParseService
from backend.app.services.dependency_service import DependencyService
from backend.app.services.api_service import ApiService
from backend.app.services.database_service import DatabaseService


class DocumentationService:
    """Service layer managing AI documentation generation, storage, retrieval, and versioning."""

    @classmethod
    def get_llm_status(cls, project_id: Optional[str] = None, db: Optional[Session] = None) -> DocStatusResponse:
        client = get_llm_client()
        available_types = [e.value for e in DocumentType]
        generated_types = []
        total_gen = 0

        if project_id and db:
            docs = db.query(DocumentationRecord).filter(DocumentationRecord.project_id == project_id).all()
            generated_types = [d.document_type for d in docs]
            total_gen = len(docs)

        return DocStatusResponse(
            llm_configured=client.is_configured(),
            provider=client.get_provider_name(),
            model=client.get_model_name(),
            available_doc_types=available_types,
            generated_doc_types=generated_types,
            total_generated=total_gen,
        )

    @classmethod
    async def generate_documentation(
        cls,
        project_id: str,
        db: Session,
        document_types: Optional[List[str]] = None,
        force_regenerate: bool = False,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> DocumentationGenerationResult:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found.",
            )

        client = get_llm_client(provider=provider, model=model)
        if not client.is_configured():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "LLM API Key is not configured. "
                    "Please set LLM_API_KEY or OPENAI_API_KEY in your environment, or configure provider settings."
                ),
            )

        start_time = time.perf_counter()

        # Gather structured repository analysis facts
        try:
            technologies = ScanService.get_technologies(project_id, db)
        except Exception:
            technologies = None

        try:
            statistics = ScanService.get_statistics(project_id, db)
        except Exception:
            statistics = None

        try:
            structure_res = ScanService.get_structure(project_id, db)
            structure_items = structure_res.structure
        except Exception:
            structure_items = []

        try:
            entities_res = ParseService.get_project_entities(project_id, db, limit=500)
            entities = entities_res.entities
        except Exception:
            entities = []

        try:
            dep_res = DependencyService.get_dependencies(project_id, db, limit=500)
            dependencies = dep_res.dependencies
        except Exception:
            dependencies = []

        try:
            api_res = ApiService.get_apis(project_id, db, limit=200)
            apis = api_res.apis
        except Exception:
            apis = []

        try:
            db_res = DatabaseService.get_models(project_id, db)
            db_models = db_res.models
        except Exception:
            db_models = []

        try:
            rel_res = DatabaseService.get_relationships(project_id, db)
            db_relationships = rel_res.relationships
        except Exception:
            db_relationships = []

        # Determine target doc types
        all_types = [e.value for e in DocumentType]
        target_types = document_types if document_types else all_types

        generator = DocumentationGenerator(client)
        generated_records: List[DocumentationRecord] = []

        docs_dir = Path(project.repository_path or f"{settings.REPO_STORAGE_PATH}/{project.id}") / ".docpilot" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        for dt in target_types:
            if dt not in all_types:
                continue

            existing = db.query(DocumentationRecord).filter(
                DocumentationRecord.project_id == project_id,
                DocumentationRecord.document_type == dt,
            ).first()

            if existing and not force_regenerate and document_types is None:
                # If generating all and already exists without force flag, keep existing
                generated_records.append(existing)
                continue

            title, content, source_entities, model_name, meta = await generator.generate_document(
                doc_type=dt,
                project_name=project.name,
                technologies=technologies,
                statistics=statistics,
                structure=structure_items,
                entities=entities,
                dependencies=dependencies,
                apis=apis,
                db_models=db_models,
                db_relationships=db_relationships,
            )

            if existing:
                existing.title = title
                existing.content = content
                existing.source_entities = source_entities
                existing.model = model_name
                existing.version += 1
                existing.metadata_json = meta
                db.add(existing)
                generated_records.append(existing)
            else:
                new_record = DocumentationRecord(
                    project_id=project_id,
                    document_type=dt,
                    title=title,
                    content=content,
                    source_entities=source_entities,
                    model=model_name,
                    version=1,
                    metadata_json=meta,
                )
                db.add(new_record)
                generated_records.append(new_record)

            # Also persist to disk as markdown file
            md_file = docs_dir / f"{dt.lower()}.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(content)

        db.commit()
        for r in generated_records:
            db.refresh(r)

        total_duration = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Generated {len(generated_records)} documentation files for project {project_id} in {total_duration}ms")

        return DocumentationGenerationResult(
            project_id=project_id,
            status="GENERATED",
            generated_count=len(generated_records),
            duration_ms=total_duration,
            documents=[DocumentationResponse.model_validate(r) for r in generated_records],
        )

    @classmethod
    def get_project_documentation(
        cls,
        project_id: str,
        db: Session,
        document_type: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> DocumentationListResponse:
        query = db.query(DocumentationRecord).filter(DocumentationRecord.project_id == project_id)

        if document_type and document_type != "ALL":
            query = query.filter(DocumentationRecord.document_type == document_type)

        if search_query:
            term = f"%{search_query}%"
            query = query.filter(
                (DocumentationRecord.title.ilike(term)) | (DocumentationRecord.content.ilike(term))
            )

        records = query.order_by(DocumentationRecord.document_type.asc()).all()

        counts_by_type: Dict[str, int] = {}
        for r in records:
            counts_by_type[r.document_type] = counts_by_type.get(r.document_type, 0) + 1

        return DocumentationListResponse(
            project_id=project_id,
            total_documents=len(records),
            documents=[DocumentationResponse.model_validate(r) for r in records],
            counts_by_type=counts_by_type,
        )

    @classmethod
    def get_document_by_id(
        cls,
        project_id: str,
        document_id: str,
        db: Session,
    ) -> DocumentationResponse:
        record = db.query(DocumentationRecord).filter(
            DocumentationRecord.id == document_id,
            DocumentationRecord.project_id == project_id,
        ).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documentation document with ID '{document_id}' not found in project '{project_id}'.",
            )

        return DocumentationResponse.model_validate(record)

    @classmethod
    async def regenerate_document(
        cls,
        project_id: str,
        document_id: str,
        db: Session,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> DocumentationResponse:
        record = db.query(DocumentationRecord).filter(
            DocumentationRecord.id == document_id,
            DocumentationRecord.project_id == project_id,
        ).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documentation document with ID '{document_id}' not found in project '{project_id}'.",
            )

        selected_provider = provider or (record.metadata_json or {}).get("provider")
        selected_model = model or (record.model if record.model != "gpt-4o-mini" else None)

        res = await cls.generate_documentation(
            project_id=project_id,
            db=db,
            document_types=[record.document_type],
            force_regenerate=True,
            provider=selected_provider,
            model=selected_model,
        )

        updated = next((d for d in res.documents if d.document_type == record.document_type), None)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate documentation document.",
            )

        return updated
