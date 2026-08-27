from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LanguageStat(BaseModel):
    files: int = Field(..., description="Number of files in this language")
    lines: int = Field(..., description="Total estimated lines of code")
    percentage: float = Field(0.0, description="Percentage of total lines of code")


class FrameworkInfo(BaseModel):
    name: str = Field(..., description="Framework name (e.g. FastAPI, Django, React, Next.js)")
    category: str = Field(..., description="Framework type (e.g. Backend Web, Frontend UI, Fullstack)")
    confidence: str = Field(..., description="Detection confidence: HIGH, MEDIUM, LOW")
    indicators: List[str] = Field(default_factory=list, description="Files, dependencies, or imports triggering detection")
    version: Optional[str] = Field(None, description="Detected version if available in manifests")


class InfrastructureInfo(BaseModel):
    name: str = Field(..., description="Infrastructure technology (e.g. Docker, Kubernetes, GitHub Actions, Terraform)")
    type: str = Field(..., description="Type (e.g. Containerization, Orchestration, CI/CD, IaC, Configuration)")
    files: List[str] = Field(default_factory=list, description="Configuration/manifest files found")
    details: Optional[str] = Field(None, description="Additional details or detected services")


class TechnologyDetectionResponse(BaseModel):
    project_id: str
    languages: Dict[str, LanguageStat]
    primary_language: Optional[str] = None
    frameworks: List[FrameworkInfo] = Field(default_factory=list)
    infrastructure: List[InfrastructureInfo] = Field(default_factory=list)
    detected_at: datetime
