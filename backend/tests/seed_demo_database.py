from pathlib import Path
import httpx

repo_dir = Path(r"C:\Users\arrah\OneDrive\Documents\GitHub\Docpilot-AI\storage\repos\c921a11b-1776-4a00-9148-5106b23f0454")
models_dir = repo_dir / "backend" / "app" / "models"
models_dir.mkdir(parents=True, exist_ok=True)

# 1. User model
(models_dir / "user.py").write_text(
    'from typing import List, Optional\n'
    'from sqlalchemy import String, Integer, Boolean, DateTime\n'
    'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
    'from backend.app.database.base import Base\n\n'
    'class User(Base):\n'
    '    """Represents registered platform developers and administrators."""\n'
    '    __tablename__ = "users"\n\n'
    '    id: Mapped[int] = mapped_column(primary_key=True)\n'
    '    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)\n'
    '    username: Mapped[str] = mapped_column(String(100), nullable=False)\n'
    '    is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n\n'
    '    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner")\n'
    '    profile: Mapped[Optional["Profile"]] = relationship("Profile", back_populates="user", uselist=False)\n',
    encoding="utf-8",
)

# 2. Project model
(models_dir / "project.py").write_text(
    'from typing import List\n'
    'from sqlalchemy import String, Integer, ForeignKey, Text\n'
    'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
    'from backend.app.database.base import Base\n\n'
    'class Project(Base):\n'
    '    """Represents an ingested software repository undergoing documentation analysis."""\n'
    '    __tablename__ = "projects"\n\n'
    '    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n'
    '    name: Mapped[str] = mapped_column(String(255), nullable=False)\n'
    '    description: Mapped[str] = mapped_column(Text, nullable=True)\n'
    '    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))\n\n'
    '    owner: Mapped["User"] = relationship("User", back_populates="projects")\n'
    '    entities: Mapped[List["CodeEntity"]] = relationship("CodeEntity", back_populates="project")\n'
    '    tags: Mapped[List["Tag"]] = relationship("Tag", secondary="project_tags", back_populates="projects")\n',
    encoding="utf-8",
)

# 3. CodeEntity model
(models_dir / "code_entity.py").write_text(
    'from typing import Optional\n'
    'from sqlalchemy import String, Integer, ForeignKey, Text\n'
    'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
    'from backend.app.database.base import Base\n\n'
    'class CodeEntity(Base):\n'
    '    """Structured AST code entity representing classes, functions, and modules."""\n'
    '    __tablename__ = "code_entities"\n\n'
    '    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n'
    '    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))\n'
    '    name: Mapped[str] = mapped_column(String(255), nullable=False)\n'
    '    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)\n'
    '    file_path: Mapped[str] = mapped_column(String(500), nullable=False)\n'
    '    start_line: Mapped[int] = mapped_column(Integer, nullable=False)\n'
    '    end_line: Mapped[int] = mapped_column(Integer, nullable=False)\n\n'
    '    project: Mapped["Project"] = relationship("Project", back_populates="entities")\n',
    encoding="utf-8",
)

# 4. Profile model
(models_dir / "profile.py").write_text(
    'from sqlalchemy import String, Integer, ForeignKey\n'
    'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
    'from backend.app.database.base import Base\n\n'
    'class Profile(Base):\n'
    '    """User settings and notification profile."""\n'
    '    __tablename__ = "profiles"\n\n'
    '    id: Mapped[int] = mapped_column(primary_key=True)\n'
    '    bio: Mapped[str] = mapped_column(String(500), nullable=True)\n'
    '    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)\n\n'
    '    user: Mapped["User"] = relationship("User", back_populates="profile")\n',
    encoding="utf-8",
)

# 5. Tag model
(models_dir / "tag.py").write_text(
    'from typing import List\n'
    'from sqlalchemy import String, Integer\n'
    'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
    'from backend.app.database.base import Base\n\n'
    'class Tag(Base):\n'
    '    """Categorical taxonomy tags."""\n'
    '    __tablename__ = "tags"\n\n'
    '    id: Mapped[int] = mapped_column(primary_key=True)\n'
    '    name: Mapped[str] = mapped_column(String(50), unique=True)\n\n'
    '    projects: Mapped[List["Project"]] = relationship("Project", secondary="project_tags", back_populates="tags")\n',
    encoding="utf-8",
)

# Trigger analysis on demo project
client = httpx.Client(base_url="http://127.0.0.1:8000")
res = client.post("/api/v1/projects/c921a11b-1776-4a00-9148-5106b23f0454/database/analyze")
print("Analyzed demo project database schema:", res.json())
