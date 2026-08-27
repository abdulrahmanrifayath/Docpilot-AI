from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class RelationshipType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"


class NodeType(str, Enum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    SERVICE = "service"
    PACKAGE = "package"


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class GraphNode(BaseModel):
    id: str = Field(..., description="Unique node ID")
    label: str = Field(..., description="Display label")
    type: str = Field("file", description="Node type: file, module, class, function, service, package")
    file_path: Optional[str] = Field(None, description="Relative file path")
    line_number: Optional[int] = Field(None, description="Definition line number")
    is_internal: bool = Field(True, description="Whether node is inside repository")
    position: NodePosition = Field(default_factory=NodePosition)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str = Field(..., description="Unique edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, USES")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Inference confidence score")
    is_internal: bool = Field(True, description="Whether relationship is between internal code")
    label: Optional[str] = Field(None, description="Edge display text")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DependencyItem(BaseModel):
    id: str
    project_id: str
    source_id: str
    source_name: str
    source_type: str
    target_id: str
    target_name: str
    target_type: str
    relationship_type: str
    confidence: float
    is_internal: bool
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DependencyListResponse(BaseModel):
    project_id: str
    total_dependencies: int
    dependencies: List[DependencyItem]
    counts_by_type: Dict[str, int]


class DependencyGraphResponse(BaseModel):
    project_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int
    internal_edges_count: int
    external_edges_count: int


class EntityDependenciesResponse(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    incoming_dependencies: List[DependencyItem]
    outgoing_dependencies: List[DependencyItem]
    total_dependencies: int


class AnalyzeDependenciesResponse(BaseModel):
    project_id: str
    status: str
    total_nodes: int
    total_edges: int
    internal_edges: int
    external_edges: int
    duration_ms: float
    analyzed_at: datetime
