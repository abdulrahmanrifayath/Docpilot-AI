import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class DbModelRecord(Base):
    __tablename__ = "db_models"

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
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    table_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
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
    orm_framework: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SQLAlchemy",
    )  # "SQLAlchemy", "Django", "RawSQL"
    docstring: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    fields_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    relationships_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
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
        Index("ix_db_models_project_table", "project_id", "table_name"),
        Index("ix_db_models_project_model", "project_id", "model_name"),
    )

    def __repr__(self) -> str:
        return f"<DbModelRecord({self.model_name} -> {self.table_name})>"


class DbRelationshipRecord(Base):
    __tablename__ = "db_relationships"

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
    source_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_table: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    target_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_table: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # "ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_MANY", "FOREIGN_KEY"
    foreign_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    cardinality_mermaid: Mapped[str] = mapped_column(
        String(20),
        default="||--o{",
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
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
        Index("ix_db_relationships_project_src", "project_id", "source_table"),
        Index("ix_db_relationships_project_tgt", "project_id", "target_table"),
    )

    def __repr__(self) -> str:
        return f"<DbRelationshipRecord({self.source_table} -[{self.relationship_type}]-> {self.target_table})>"
