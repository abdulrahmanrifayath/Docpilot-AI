import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="zip"
    )  # "zip", "github", "local"
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    repository_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # "pending", "analyzing", "ready", "error"
    
    created_at: Mapped[datetime] = mapped_column(
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
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
