from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class DatabaseField(BaseModel):
    name: str
    data_type: str = "VARCHAR"
    primary_key: bool = False
    foreign_key: Optional[str] = None  # "users.id"
    nullable: bool = True
    default: Optional[str] = None
    unique: bool = False
    index: bool = False
    description: Optional[str] = None


class DatabaseRelationship(BaseModel):
    name: Optional[str] = None
    source_model: str
    source_table: str
    target_model: str
    target_table: str
    relationship_type: str = Field(..., description="ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY, FOREIGN_KEY")
    foreign_key: Optional[str] = None
    back_populates: Optional[str] = None
    secondary_table: Optional[str] = None
    confidence: float = 1.0
    cardinality_mermaid: str = "||--o{"
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class DatabaseModelBase(BaseModel):
    model_name: str
    table_name: str
    file_path: str
    line_number: Optional[int] = None
    orm_framework: str = "SQLAlchemy"
    docstring: Optional[str] = None
    fields: List[DatabaseField] = Field(default_factory=list)
    relationships: List[DatabaseRelationship] = Field(default_factory=list)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class DatabaseModelResponse(DatabaseModelBase):
    id: str
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatabaseModelListResponse(BaseModel):
    project_id: str
    total_models: int
    models: List[DatabaseModelResponse]
    frameworks_count: Dict[str, int]


class DatabaseRelationshipResponse(BaseModel):
    id: str
    project_id: str
    source_model: str
    source_table: str
    target_model: str
    target_table: str
    relationship_type: str
    foreign_key: Optional[str] = None
    confidence: float
    cardinality_mermaid: str
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatabaseRelationshipListResponse(BaseModel):
    project_id: str
    total_relationships: int
    relationships: List[DatabaseRelationshipResponse]
    counts_by_type: Dict[str, int]


class DatabaseDiagramResponse(BaseModel):
    project_id: str
    mermaid_code: str
    total_tables: int
    total_relationships: int
    models: List[DatabaseModelResponse]


class DatabaseAnalyzeResponse(BaseModel):
    project_id: str
    status: str
    total_models: int
    total_relationships: int
    duration_ms: float
    analyzed_at: datetime
