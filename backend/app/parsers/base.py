from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ImportItem(BaseModel):
    module: str
    imported_names: List[str] = Field(default_factory=list)
    is_relative: bool = False
    alias: Optional[str] = None


class ParameterItem(BaseModel):
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None


class CodeSymbol(BaseModel):
    name: str
    symbol_type: str  # function, async_function, class, method, interface, type_alias
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[ParameterItem] = Field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = Field(default_factory=list)
    calls: List[str] = Field(default_factory=list)  # functions/methods called
    parent_symbol: Optional[str] = None  # e.g., enclosing class name


class APIEndpoint(BaseModel):
    method: str  # GET, POST, PUT, DELETE, PATCH, etc.
    path: str
    handler_name: str
    start_line: int
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    response_model: Optional[str] = None
    auth_required: bool = False
    framework: str = "FastAPI"


class DBField(BaseModel):
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None
    is_nullable: bool = True
    default: Optional[str] = None


class DBRelationship(BaseModel):
    name: str
    target_model: str
    relationship_type: str  # one_to_many, many_to_one, one_to_one, many_to_many


class DatabaseModel(BaseModel):
    name: str
    table_name: Optional[str] = None
    fields: List[DBField] = Field(default_factory=list)
    relationships: List[DBRelationship] = Field(default_factory=list)
    orm_type: str = "SQLAlchemy"  # SQLAlchemy, Django, Prisma, Mongoose, SQL
    start_line: int = 1


class ParsedFile(BaseModel):
    file_path: str
    relative_path: str
    language: str
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    imports: List[ImportItem] = Field(default_factory=list)
    classes: List[CodeSymbol] = Field(default_factory=list)
    functions: List[CodeSymbol] = Field(default_factory=list)
    interfaces: List[CodeSymbol] = Field(default_factory=list)
    apis: List[APIEndpoint] = Field(default_factory=list)
    db_models: List[DatabaseModel] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    raw_summary: Optional[str] = None


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, relative_path: str, content: str) -> ParsedFile:
        """Parse source code content and return structured metadata."""
        pass
