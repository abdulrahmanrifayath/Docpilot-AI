from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, AliasChoices


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
    infrastructure: List[str] = Field(default_factory=list)
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


class ProjectStructureNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    extension: Optional[str] = None
    file_size: Optional[int] = None
    estimated_line_count: Optional[int] = None
    file_category: Optional[str] = None
    language: Optional[str] = None
    children: Optional[List["ProjectStructureNode"]] = None


class ProjectStructureResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    tree: ProjectStructureNode


class ProjectTechnologiesResponse(BaseModel):
    project_id: str
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)


class ProjectStatisticsResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    total_lines: int
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    categories: Dict[str, int] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)


class ProjectScanResponse(BaseModel):
    project_id: str
    status: str
    total_files: int
    total_directories: int
    total_lines: int
    languages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    infrastructure: List[str] = Field(default_factory=list)
    scanned_at: datetime




class CodeEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    file_path: str
    name: str
    entity_type: str  # MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT
    start_line: int
    end_line: int
    signature: Optional[str] = None
    parent_entity: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"))



class ProjectParseResponse(BaseModel):
    project_id: str
    status: str
    total_files_parsed: int
    total_entities_extracted: int
    entity_breakdown: Dict[str, int] = Field(default_factory=dict)
    parsed_at: datetime


