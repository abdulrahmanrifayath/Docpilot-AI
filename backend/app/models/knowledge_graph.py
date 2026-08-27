import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class KnowledgeNodeRecord(Base):
    __tablename__ = "knowledge_nodes"

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
    node_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )  # e.g. "folder:app", "file:app/main.py", "entity:uuid", "api:uuid", "table:users"
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # "FOLDER", "FILE", "MODULE", "CLASS", "FUNCTION", "API", "DATABASE_TABLE", "COMPONENT"
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        index=True,
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
        Index("ix_knowledge_nodes_project_cat", "project_id", "category"),
        Index("ix_knowledge_nodes_project_key", "project_id", "node_key"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeNodeRecord({self.category}: {self.name})>"


class KnowledgeEdgeRecord(Base):
    __tablename__ = "knowledge_edges"

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
    source_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    target_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    relationship: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # "CONTAINS", "DECLARES", "HANDLES_ROUTE", "EXPOSES_API", "IMPORTS", "CALLS", "EXTENDS", "QUERIES_TABLE", "MAPS_TO_MODEL", "DEPENDS_ON", "REFERENCES"
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
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
        Index("ix_knowledge_edges_project_src", "project_id", "source_key"),
        Index("ix_knowledge_edges_project_tgt", "project_id", "target_key"),
        Index("ix_knowledge_edges_project_rel", "project_id", "relationship"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeEdgeRecord({self.source_key} -[{self.relationship}]-> {self.target_key})>"
