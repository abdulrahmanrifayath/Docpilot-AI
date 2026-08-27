from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class DocumentType(str, Enum):
    PROJECT_OVERVIEW = "PROJECT_OVERVIEW"
    README = "README"
    ARCHITECTURE_OVERVIEW = "ARCHITECTURE_OVERVIEW"
    API_DOCUMENTATION = "API_DOCUMENTATION"
    DATABASE_DOCUMENTATION = "DATABASE_DOCUMENTATION"
    FOLDER_DOC = "FOLDER_DOC"
    FILE_DOC = "FILE_DOC"
    CLASS_DOC = "CLASS_DOC"
    FUNCTION_DOC = "FUNCTION_DOC"


class DocumentationBase(BaseModel):
    document_type: str = Field(..., description="Document type identifier")
    title: str = Field(..., description="Human readable title of the document")
    content: str = Field(..., description="Markdown document content")
    source_entities: List[str] = Field(default_factory=list, description="Referenced entity IDs, table names, or file paths")
    model: str = Field(..., description="LLM model identifier used")
    version: int = Field(default=1, description="Version number incremented on regeneration")
    metadata_json: Dict[str, Any] = Field(default_factory=dict, description="Metadata such as tokens, duration, status")


class DocumentationCreate(DocumentationBase):
    project_id: str


class DocumentationResponse(DocumentationBase):
    id: str
    project_id: str
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentationListResponse(BaseModel):
    project_id: str
    total_documents: int
    documents: List[DocumentationResponse]
    counts_by_type: Dict[str, int]


class GenerateDocRequest(BaseModel):
    document_types: Optional[List[str]] = Field(
        None,
        description="Optional list of specific document types to generate. If omitted, generates all standard types.",
    )
    force_regenerate: bool = Field(
        False,
        description="Whether to overwrite existing documents or increment their version.",
    )
    provider: Optional[str] = Field(
        None,
        description="Optional override for LLM provider (openai, mock, etc.)",
    )
    model: Optional[str] = Field(
        None,
        description="Optional override for LLM model",
    )


class DocStatusResponse(BaseModel):
    llm_configured: bool
    provider: str
    model: str
    available_doc_types: List[str]
    generated_doc_types: List[str]
    total_generated: int


class DocumentationGenerationResult(BaseModel):
    project_id: str
    status: str
    generated_count: int
    duration_ms: float
    documents: List[DocumentationResponse]
