from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "docpilot-ai"


class DatabaseStatus(BaseModel):
    status: str  # "connected", "error"
    engine: str  # "sqlite", "postgresql"
    message: Optional[str] = None


class AIProviderStatus(BaseModel):
    configured: bool
    provider: str = "openai"
    model: str
    embedding_model: str
    message: Optional[str] = None


class VectorDBStatus(BaseModel):
    status: str  # "ready", "uninitialized", "error"
    provider: str = "chromadb"
    storage_path: str
    message: Optional[str] = None


class SystemStatusResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    environment: str
    version: str = "1.0.0"
    timestamp: datetime
    database: DatabaseStatus
    ai_provider: AIProviderStatus
    vector_db: VectorDBStatus
