from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class KnowledgeNode(BaseModel):
    id: str
    node_key: str
    name: str
    category: str = Field(
        ...,
        description="FOLDER, FILE, MODULE, CLASS, FUNCTION, API, DATABASE_TABLE, COMPONENT",
    )
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: Dict[str, Any] = Field(default_factory=dict)
    in_degree: int = 0
    out_degree: int = 0

    model_config = ConfigDict(from_attributes=True)


class KnowledgeEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str = Field(
        ...,
        description="CONTAINS, DECLARES, HANDLES_ROUTE, EXPOSES_API, IMPORTS, CALLS, EXTENDS, QUERIES_TABLE, MAPS_TO_MODEL, DEPENDS_ON",
    )
    confidence: float = 1.0
    label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class KnowledgeGraphResponse(BaseModel):
    project_id: str
    total_nodes: int
    total_edges: int
    nodes: List[KnowledgeNode]
    edges: List[KnowledgeEdge]
    counts_by_category: Dict[str, int]
    counts_by_relationship: Dict[str, int]


class KnowledgeEntityDetail(BaseModel):
    node: KnowledgeNode
    upstream_callers: List[KnowledgeNode] = Field(default_factory=list)
    downstream_dependencies: List[KnowledgeNode] = Field(default_factory=list)
    connected_apis: List[KnowledgeNode] = Field(default_factory=list)
    connected_database_tables: List[KnowledgeNode] = Field(default_factory=list)
    parent_file_or_folder: Optional[KnowledgeNode] = None


class KnowledgeBuildResponse(BaseModel):
    project_id: str
    status: str
    total_nodes: int
    total_edges: int
    counts_by_category: Dict[str, int]
    duration_ms: float
    built_at: datetime
