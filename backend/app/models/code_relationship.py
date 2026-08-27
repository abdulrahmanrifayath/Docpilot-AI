import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class CodeRelationship(Base):
    __tablename__ = "code_relationships"

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
    source_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "file", "module", "class", "function", "service", "package"
    target_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    target_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "file", "module", "class", "function", "service", "package"
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # "IMPORTS", "CALLS", "EXTENDS", "IMPLEMENTS", "DEPENDS_ON", "USES"
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    line_number: Mapped[Optional[int]] = mapped_column(
        Integer,
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
        Index("ix_code_relationships_project_source", "project_id", "source_id"),
        Index("ix_code_relationships_project_target", "project_id", "target_id"),
        Index("ix_code_relationships_project_reltype", "project_id", "relationship_type"),
    )

    def __repr__(self) -> str:
        return f"<CodeRelationship({self.source_name} -[{self.relationship_type}]-> {self.target_name})>"
