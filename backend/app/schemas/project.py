from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ProjectStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    CLONING = "CLONING"
    READY = "READY"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project or repository name")
    description: Optional[str] = Field(None, description="Short summary or description")
    source_type: str = Field(default="zip", description="Type of source: 'zip', 'github', or 'local'")
    source_url: Optional[str] = Field(None, description="GitHub or remote URL if applicable")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    repository_path: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None


class ProjectResponse(ProjectBase):
    id: str
    repository_path: Optional[str] = None
    status: str
    status_message: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CloneRequest(BaseModel):
    url: str = Field(..., description="Public GitHub repository URL (e.g., https://github.com/owner/repo)")


class FileItem(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: int
    extension: Optional[str] = None
    children: Optional[List["FileItem"]] = None


class FileTreeResponse(BaseModel):
    project_id: str
    repository_path: str
    total_files: int
    total_directories: int
    total_size_bytes: int
    files: List[FileItem]
    language_counts: Dict[str, int] = Field(default_factory=dict)
