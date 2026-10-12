from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RepositoryCreate(BaseModel):
    name: Optional[str] = None
    source_type: str = "zip"  # zip, git, local
    source_url: Optional[str] = None


class RepositoryStats(BaseModel):
    files: int = 0
    lines: int = 0
    classes: int = 0
    functions: int = 0
    apis: int = 0
    models: int = 0


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    status: str
    current_step: str
    progress_percent: int
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    languages: Dict[str, Any] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)
    structure: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PipelineProgress(BaseModel):
    repository_id: str
    status: str
    current_step: str
    progress_percent: int
    error_message: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    doc_type: str
    title: str
    content: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DiagramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    diagram_type: str
    title: str
    mermaid_code: Optional[str] = None
    flow_data: Optional[Dict[str, Any]] = None
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    role: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ProviderSettings(BaseModel):
    llm_provider: str
    llm_model: str
    llm_base_url: Optional[str] = None
    is_configured: bool
    available_providers: List[str] = ["openai", "gemini", "anthropic", "ollama", "custom"]
    github_token_configured: bool = False


class ProviderSettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    github_token: Optional[str] = None


class SyncResponse(BaseModel):
    repository_id: str
    changes_detected: bool
    modified_files: List[str] = Field(default_factory=list)
    added_files: List[str] = Field(default_factory=list)
    deleted_files: List[str] = Field(default_factory=list)
    regenerated_docs: List[str] = Field(default_factory=list)
    status: str
