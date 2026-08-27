from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class EntityType(str, Enum):
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    COMPONENT = "COMPONENT"


class CodeEntityBase(BaseModel):
    name: str = Field(..., description="Entity identifier name")
    entity_type: str = Field(..., description="MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT")
    file_path: str = Field(..., description="Relative file path in repository")
    start_line: int = Field(..., description="Starting line number (1-indexed)")
    end_line: int = Field(..., description="Ending line number (1-indexed)")
    signature: Optional[str] = Field(None, description="Full type signature or declaration")
    parent_entity: Optional[str] = Field(None, description="Enclosing class or component name if applicable")
    docstring: Optional[str] = Field(None, description="Associated docstring or header comment")
    metadata_json: Dict[str, Any] = Field(default_factory=dict, description="Language-specific metadata (parameters, return type, decorators, etc.)")


class CodeEntityCreate(CodeEntityBase):
    project_id: str


class CodeEntityResponse(CodeEntityBase):
    id: str
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileEntitiesResponse(BaseModel):
    project_id: str
    file_path: str
    total_entities: int
    entities: List[CodeEntityResponse]
    entity_counts: Dict[str, int]


class ProjectEntitiesResponse(BaseModel):
    project_id: str
    total_entities: int
    entities: List[CodeEntityResponse]
    entity_counts: Dict[str, int]


class ParseResponse(BaseModel):
    project_id: str
    status: str
    files_parsed: int
    total_entities: int
    entities_by_type: Dict[str, int]
    duration_ms: float
    parsed_at: datetime
