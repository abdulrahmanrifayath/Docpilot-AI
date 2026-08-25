from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project or repository name")
    description: Optional[str] = Field(None, description="Short summary or description")
    source_type: str = Field(default="zip", description="Type of source: 'zip', 'github', or 'local'")
    source_url: Optional[str] = Field(None, description="GitHub or remote URL if applicable")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    repository_path: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    repository_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
