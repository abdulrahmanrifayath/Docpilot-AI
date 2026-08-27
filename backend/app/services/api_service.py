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
from backend.app.models.api_endpoint import ApiEndpoint
from backend.app.schemas.api_endpoint import (
    ApiEndpointResponse,
    ApiEndpointListResponse,
    ApiAnalyzeResponse,
    ApiRequestSchema,
    ApiResponseSchema,
)
from backend.app.analyzers.api_detector import ApiDetector
from backend.app.services.project_service import ProjectService


class ApiService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "apis.json"

    @classmethod
    def analyze_apis(cls, project_id: str, db: Session) -> ApiAnalyzeResponse:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        logger.info(f"Starting API discovery for project {project_id} at {repo_dir}")

        start_time = time.perf_counter()

        # 1. Run API Detector
        detected_endpoints = ApiDetector.detect_apis(repo_dir)

        # 2. Clear existing API records in DB
        db.execute(delete(ApiEndpoint).where(ApiEndpoint.project_id == project_id))
        db.commit()

        # 3. Store in DB
        now = datetime.now(timezone.utc)
        db_items: List[ApiEndpoint] = []
        methods_count: Dict[str, int] = {}
        frameworks_count: Dict[str, int] = {}

        for ep in detected_endpoints:
            methods_count[ep.method] = methods_count.get(ep.method, 0) + 1
            frameworks_count[ep.framework] = frameworks_count.get(ep.framework, 0) + 1

            record = ApiEndpoint(
                id=str(uuid.uuid4()),
                project_id=project_id,
                method=ep.method,
                path=ep.path,
                handler_name=ep.handler_name,
                file_path=ep.file_path,
                line_number=ep.line_number,
                framework=ep.framework,
                request_schema=ep.request_schema.model_dump() if ep.request_schema else None,
                response_schema=ep.response_schema.model_dump() if ep.response_schema else None,
                authentication_required=ep.authentication_required,
                tags=ep.tags,
                summary=ep.summary,
                docstring=ep.docstring,
                metadata_json=ep.metadata_json,
                created_at=now,
            )
            db_items.append(record)

        if db_items:
            db.bulk_save_objects(db_items)
            db.commit()

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"Discovered {len(db_items)} API endpoints in {duration_ms}ms")

        # 4. Cache JSON payload
        cache_file = cls._get_cache_path(repo_dir)
        try:
            cached_data = {
                "project_id": project_id,
                "analyzed_at": now.isoformat(),
                "total_apis": len(db_items),
                "apis_by_method": methods_count,
                "apis_by_framework": frameworks_count,
                "apis": [ep.model_dump() for ep in detected_endpoints],
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save apis cache to {cache_file}: {e}")

        return ApiAnalyzeResponse(
            project_id=project_id,
            status="ANALYZED",
            total_apis=len(db_items),
            apis_by_method=methods_count,
            apis_by_framework=frameworks_count,
            duration_ms=duration_ms,
            analyzed_at=now,
        )

    @classmethod
    def get_apis(
        cls,
        project_id: str,
        db: Session,
        method: Optional[str] = None,
        tag: Optional[str] = None,
        auth_required: Optional[bool] = None,
        skip: int = 0,
        limit: int = 500,
    ) -> ApiEndpointListResponse:
        ProjectService.get_by_id(db, project_id)

        # If DB count is 0, auto-run
        count_stmt = select(func.count(ApiEndpoint.id)).where(ApiEndpoint.project_id == project_id)
        if (db.execute(count_stmt).scalar() or 0) == 0:
            try:
                cls.analyze_apis(project_id, db)
            except Exception as e:
                logger.warning(f"Could not auto-analyze APIs: {e}")

        stmt = select(ApiEndpoint).where(ApiEndpoint.project_id == project_id)
        if method:
            stmt = stmt.where(ApiEndpoint.method == method.upper())
        if auth_required is not None:
            stmt = stmt.where(ApiEndpoint.authentication_required == auth_required)

        stmt = stmt.order_by(ApiEndpoint.path, ApiEndpoint.method).offset(skip).limit(limit)
        results = db.execute(stmt).scalars().all()

        # Compute counts
        m_counts: Dict[str, int] = {}
        f_counts: Dict[str, int] = {}
        for r in results:
            m_counts[r.method] = m_counts.get(r.method, 0) + 1
            f_counts[r.framework] = f_counts.get(r.framework, 0) + 1

        api_responses: List[ApiEndpointResponse] = []
        for r in results:
            api_responses.append(
                ApiEndpointResponse(
                    id=r.id,
                    project_id=r.project_id,
                    method=r.method,
                    path=r.path,
                    handler_name=r.handler_name,
                    file_path=r.file_path,
                    line_number=r.line_number,
                    framework=r.framework,
                    request_schema=ApiRequestSchema(**r.request_schema) if r.request_schema else None,
                    response_schema=ApiResponseSchema(**r.response_schema) if r.response_schema else None,
                    authentication_required=r.authentication_required,
                    tags=r.tags,
                    summary=r.summary,
                    docstring=r.docstring,
                    metadata_json=r.metadata_json,
                    created_at=r.created_at,
                )
            )

        return ApiEndpointListResponse(
            project_id=project_id,
            total_apis=len(api_responses),
            apis=api_responses,
            methods_count=m_counts,
            frameworks_count=f_counts,
        )

    @classmethod
    def get_api_by_id(cls, project_id: str, api_id: str, db: Session) -> ApiEndpointResponse:
        ProjectService.get_by_id(db, project_id)
        stmt = select(ApiEndpoint).where(
            ApiEndpoint.project_id == project_id,
            ApiEndpoint.id == api_id,
        )
        endpoint = db.execute(stmt).scalar_one_or_none()
        if not endpoint:
            raise NotFoundException(f"API endpoint with ID {api_id} not found in project.")

        return ApiEndpointResponse(
            id=endpoint.id,
            project_id=endpoint.project_id,
            method=endpoint.method,
            path=endpoint.path,
            handler_name=endpoint.handler_name,
            file_path=endpoint.file_path,
            line_number=endpoint.line_number,
            framework=endpoint.framework,
            request_schema=ApiRequestSchema(**endpoint.request_schema) if endpoint.request_schema else None,
            response_schema=ApiResponseSchema(**endpoint.response_schema) if endpoint.response_schema else None,
            authentication_required=endpoint.authentication_required,
            tags=endpoint.tags,
            summary=endpoint.summary,
            docstring=endpoint.docstring,
            metadata_json=endpoint.metadata_json,
            created_at=endpoint.created_at,
        )
