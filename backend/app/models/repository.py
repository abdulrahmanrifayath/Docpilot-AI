import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False, default="zip")  # zip, git, local
    source_url = Column(String(500), nullable=True)
    local_path = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, analyzing, completed, failed
    current_step = Column(String(100), nullable=False, default="Uploaded")
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    commit_hash = Column(String(100), nullable=True)
    
    # Analysis metadata stored as JSON
    languages = Column(JSON, default=dict)  # {"Python": {"files": 12, "lines": 1200, "percent": 80.0}}
    frameworks = Column(JSON, default=list)  # ["FastAPI", "React", "SQLAlchemy"]
    stats = Column(JSON, default=dict)  # {"files": 45, "lines": 5200, "classes": 20, "functions": 85, "apis": 12, "models": 6}
    structure = Column(JSON, default=dict)  # Folder structure breakdown with purposes
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    documents = relationship("Document", back_populates="repository", cascade="all, delete-orphan")
    diagrams = relationship("Diagram", back_populates="repository", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="repository", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # readme, api, architecture, onboarding, report, folder
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    repository = relationship("Repository", back_populates="documents")


class Diagram(Base):
    __tablename__ = "diagrams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    diagram_type = Column(String(50), nullable=False)  # architecture, sequence, er, dependency, react_flow
    title = Column(String(255), nullable=False)
    mermaid_code = Column(Text, nullable=True)
    flow_data = Column(JSON, nullable=True)  # { "nodes": [...], "edges": [...] } for React Flow
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    repository = relationship("Repository", back_populates="diagrams")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)  # [ { "file": "app/auth.py", "lines": "10-45", "symbol": "login" } ]
    
    created_at = Column(DateTime, default=utc_now)

    repository = relationship("Repository", back_populates="chat_messages")
