import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.base import Base


class DocumentationRecord(Base):
    """SQLAlchemy model for AI-generated project documentation."""
    __tablename__ = "project_documentation"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_entities: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        default="gpt-4o-mini",
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DocumentationRecord(id='{self.id}', type='{self.document_type}', title='{self.title}', v={self.version})>"
