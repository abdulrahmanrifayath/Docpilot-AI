from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project display name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional project description")
    source_type: str = Field("zip", description="Source type: 'zip', 'git', or 'local'")
    source_url: Optional[str] = Field(None, max_length=500, description="GitHub repository URL if source_type is 'git'")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        valid_types = {"zip", "git", "local"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid source_type '{v}'. Must be one of: {', '.join(valid_types)}")
        return v.lower()


class ProjectCloneRequest(BaseModel):
    source_url: Optional[str] = Field(None, description="Public GitHub repository URL (e.g. https://github.com/owner/repo)")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    repository_path: str
    status: str
    error_message: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    languages: Dict[str, Any] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    structure: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ProjectFileNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    children: Optional[List["ProjectFileNode"]] = None


class ProjectFilesResponse(BaseModel):
    project_id: str
    total_files: int
    files: List[ProjectFileNode]


class SystemStatusResponse(BaseModel):
    status: str
    application: Dict[str, Any]
    database: Dict[str, Any]
    ai_provider: Dict[str, Any]
    vector_database: Dict[str, Any]
