from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class ApiParameter(BaseModel):
    name: str
    in_location: str = Field("query", description="path, query, body, header, dependency")
    type: Optional[str] = None
    required: bool = True
    default: Optional[str] = None
    description: Optional[str] = None


class ApiRequestSchema(BaseModel):
    parameters: List[ApiParameter] = Field(default_factory=list)
    body_model: Optional[str] = None
    content_type: Optional[str] = "application/json"


class ApiResponseSchema(BaseModel):
    status_code: Optional[int] = 200
    response_model: Optional[str] = None
    return_type: Optional[str] = None
    description: Optional[str] = None


class ApiEndpointBase(BaseModel):
    method: str = Field(..., description="HTTP Method: GET, POST, PUT, DELETE, PATCH, etc.")
    path: str = Field(..., description="API Route path e.g. /api/v1/users/{id}")
    handler_name: str = Field(..., description="Function/handler name")
    file_path: str = Field(..., description="Relative file path")
    line_number: Optional[int] = None
    framework: str = Field("FastAPI", description="FastAPI, Flask, Express")
    request_schema: Optional[ApiRequestSchema] = None
    response_schema: Optional[ApiResponseSchema] = None
    authentication_required: bool = False
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    docstring: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ApiEndpointCreate(ApiEndpointBase):
    pass


class ApiEndpointResponse(ApiEndpointBase):
    id: str
    project_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiEndpointListResponse(BaseModel):
    project_id: str
    total_apis: int
    apis: List[ApiEndpointResponse]
    methods_count: Dict[str, int]
    frameworks_count: Dict[str, int]


class ApiAnalyzeResponse(BaseModel):
    project_id: str
    status: str
    total_apis: int
    apis_by_method: Dict[str, int]
    apis_by_framework: Dict[str, int]
    duration_ms: float
    analyzed_at: datetime
