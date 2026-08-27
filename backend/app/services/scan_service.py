import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.core.exceptions import ValidationException, NotFoundException
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectStatus
from backend.app.schemas.technology import (
    LanguageStat,
    FrameworkInfo,
    InfrastructureInfo,
    TechnologyDetectionResponse,
)
from backend.app.schemas.structure import (
    StructureItem,
    ProjectStructureResponse,
    ProjectStatisticsResponse,
    FileSummaryInfo,
    ScanResponse,
)
from backend.app.analyzers.file_scanner import FileScanner
from backend.app.analyzers.tech_detector import TechDetector
from backend.app.services.project_service import ProjectService


class ScanService:
    @staticmethod
    def _get_cache_path(repo_dir: Path) -> Path:
        cache_dir = repo_dir / ".docpilot"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "scan.json"

    @classmethod
    def scan_project(cls, project_id: str, db: Session) -> ScanResponse:
        project = ProjectService.get_by_id(db, project_id)

        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()

        # Update status to ANALYZING
        project.status = ProjectStatus.ANALYZING.value
        project.status_message = "Analyzing repository structure and detecting technologies..."
        db.commit()

        try:
            logger.info(f"Starting repository scan for project {project_id} at {repo_dir}")

            # 1. Run File Discovery & Line Counting
            scan_data = FileScanner.scan_repository(repo_dir)

            # 2. Run Technology, Framework, & Infrastructure Detection
            frameworks = TechDetector.detect_frameworks(repo_dir, scan_data["flat_files"])
            infrastructure = TechDetector.detect_infrastructure(repo_dir, scan_data["flat_files"])

            # 3. Determine Primary Language
            primary_language = None
            if scan_data["languages"]:
                primary_language = next(iter(scan_data["languages"]))

            now = datetime.now(timezone.utc)

            tech_response = TechnologyDetectionResponse(
                project_id=project.id,
                languages=scan_data["languages"],
                primary_language=primary_language,
                frameworks=frameworks,
                infrastructure=infrastructure,
                detected_at=now,
            )

            stats_response = ProjectStatisticsResponse(
                project_id=project.id,
                total_files=scan_data["total_files"],
                total_directories=scan_data["total_directories"],
                total_lines=scan_data["total_lines"],
                total_size_bytes=scan_data["total_size_bytes"],
                languages=scan_data["languages"],
                categories=scan_data["categories"],
                largest_files=scan_data["largest_files"],
            )

            structure_response = ProjectStructureResponse(
                project_id=project.id,
                repository_path=str(repo_dir),
                total_files=scan_data["total_files"],
                total_directories=scan_data["total_directories"],
                total_lines=scan_data["total_lines"],
                total_size_bytes=scan_data["total_size_bytes"],
                structure=scan_data["structure"],
            )

            scan_response = ScanResponse(
                project_id=project.id,
                status=ProjectStatus.ANALYZED.value,
                scanned_at=now,
                summary=stats_response,
                technologies=tech_response,
            )

            # 4. Save cache file to repo_dir/.docpilot/scan.json
            cache_file = cls._get_cache_path(repo_dir)
            cached_payload = {
                "project_id": project.id,
                "scanned_at": now.isoformat(),
                "summary": stats_response.model_dump(mode="json"),
                "technologies": tech_response.model_dump(mode="json"),
                "structure": structure_response.model_dump(mode="json"),
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_payload, f, indent=2)

            # 5. Update Project DB record
            project.status = ProjectStatus.ANALYZED.value
            project.last_analyzed_at = now
            project.status_message = (
                f"Scan complete: {scan_data['total_files']} files, {scan_data['total_lines']} lines of code."
            )
            db.commit()
            db.refresh(project)

            logger.info(f"Scan completed successfully for project {project_id}")
            return scan_response

        except Exception as e:
            logger.error(f"Error scanning project {project_id}: {e}")
            project.status = ProjectStatus.FAILED.value
            project.status_message = f"Scan failed: {str(e)}"
            db.commit()
            raise ValidationException(f"Repository analysis failed: {str(e)}")

    @classmethod
    def _get_or_create_scan(cls, project_id: str, db: Session) -> Dict[str, Any]:
        project = ProjectService.get_by_id(db, project_id)
        if not project.repository_path or not os.path.exists(project.repository_path):
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        repo_dir = Path(project.repository_path).resolve()
        cache_file = cls._get_cache_path(repo_dir)

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_file}: {e}")

        # If cache doesn't exist, trigger scan
        cls.scan_project(project_id, db)
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def get_structure(cls, project_id: str, db: Session) -> ProjectStructureResponse:
        data = cls._get_or_create_scan(project_id, db)
        return ProjectStructureResponse(**data["structure"])

    @classmethod
    def get_technologies(cls, project_id: str, db: Session) -> TechnologyDetectionResponse:
        data = cls._get_or_create_scan(project_id, db)
        return TechnologyDetectionResponse(**data["technologies"])

    @classmethod
    def get_statistics(cls, project_id: str, db: Session) -> ProjectStatisticsResponse:
        data = cls._get_or_create_scan(project_id, db)
        return ProjectStatisticsResponse(**data["summary"])
