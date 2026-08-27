from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from backend.app.schemas.technology import (
    LanguageStat,
    FrameworkInfo,
    InfrastructureInfo,
    TechnologyDetectionResponse,
)


class StructureItem(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: int
    lines: int = 0
    category: str = "other"  # "source_code", "configuration", "documentation", "data", "infrastructure", "style", "asset", "other"
    language: Optional[str] = None
    extension: Optional[str] = None
    children: Optional[List["StructureItem"]] = None


class ProjectStructureResponse(BaseModel):
    project_id: str
    repository_path: str
    total_files: int
    total_directories: int
    total_lines: int
    total_size_bytes: int
    structure: List[StructureItem]


class FileSummaryInfo(BaseModel):
    path: str
    name: str
    lines: int
    size: int
    language: Optional[str] = None
    category: str


class ProjectStatisticsResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    total_lines: int
    total_size_bytes: int
    languages: Dict[str, LanguageStat]
    categories: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Category counts mapping e.g. {'source_code': {'files': 20, 'lines': 1400}}",
    )
    largest_files: List[FileSummaryInfo] = Field(default_factory=list)


class ScanResponse(BaseModel):
    project_id: str
    status: str
    scanned_at: datetime
    summary: ProjectStatisticsResponse
    technologies: TechnologyDetectionResponse
