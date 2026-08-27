import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )  # "GET", "POST", "PUT", "DELETE", "PATCH", etc.
    path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )  # "/api/v1/users/{id}"
    handler_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    line_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    framework: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="FastAPI",
    )  # "FastAPI", "Flask", "Express"
    request_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )  # parameters, body schema, query params
    response_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )  # response model, return type
    authentication_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    tags: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    docstring: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_api_endpoints_project_method", "project_id", "method"),
        Index("ix_api_endpoints_project_path", "project_id", "path"),
        Index("ix_api_endpoints_project_auth", "project_id", "authentication_required"),
    )

    def __repr__(self) -> str:
        return f"<ApiEndpoint({self.method} {self.path} -> {self.handler_name})>"
