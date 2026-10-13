import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship, synonym

from app.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False, default="zip")  # zip, git, local
    source_url = Column(String(500), nullable=True)
    repository_path = Column(String(500), nullable=False, default="")
    status = Column(String(50), nullable=False, default="CREATED")  # CREATED, UPLOADING, CLONING, READY, ANALYZING, ANALYZED, FAILED
    error_message = Column(Text, nullable=True)
    last_analyzed_at = Column(DateTime, nullable=True)
    current_step = Column(String(100), nullable=True, default="Created")
    progress_percent = Column(Integer, default=0)

    @property
    def local_path(self) -> str:
        return self.repository_path

    @local_path.setter
    def local_path(self, val: str) -> None:
        self.repository_path = val
    
    # Analysis metadata stored as JSON
    languages = Column(JSON, default=dict)
    frameworks = Column(JSON, default=list)
    stats = Column(JSON, default=dict)
    structure = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    diagrams = relationship("Diagram", back_populates="project", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    repository_id = synonym("project_id")
    doc_type = Column(String(50), nullable=False)  # readme, api, architecture, onboarding, report
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="documents")
    repository = synonym("project")


class Diagram(Base):
    __tablename__ = "diagrams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    repository_id = synonym("project_id")
    diagram_type = Column(String(50), nullable=False)  # architecture, sequence, er, dependency, react_flow
    title = Column(String(255), nullable=False)
    mermaid_code = Column(Text, nullable=True)
    flow_data = Column(JSON, nullable=True)  # React Flow nodes & edges
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="diagrams")
    repository = synonym("project")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    repository_id = synonym("project_id")
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="chat_messages")
    repository = synonym("project")


# Backward compatibility aliases
Repository = Project
