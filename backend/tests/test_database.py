import io
import zipfile
import pytest
from fastapi.testclient import TestClient


def make_test_zip(files_dict: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files_dict.items():
            zf.writestr(path, content)
    buf.seek(0)
    return buf


def test_sqlalchemy_database_analysis(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "SQLAlchemy DB Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "backend/app/models/user.py": (
            "from typing import List, Optional\n"
            "from sqlalchemy import String, Integer, Boolean, ForeignKey\n"
            "from sqlalchemy.orm import Mapped, mapped_column, relationship\n"
            "from backend.app.database.base import Base\n\n"
            "class User(Base):\n"
            "    __tablename__ = 'users'\n\n"
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
            "    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)\n"
            "    is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n\n"
            "    projects: Mapped[List['Project']] = relationship('Project', back_populates='owner')\n"
            "    profile: Mapped[Optional['Profile']] = relationship('Profile', back_populates='user', uselist=False)\n"
        ),
        "backend/app/models/project.py": (
            "from typing import List, Optional\n"
            "from sqlalchemy import String, Integer, ForeignKey\n"
            "from sqlalchemy.orm import Mapped, mapped_column, relationship\n"
            "from backend.app.database.base import Base\n\n"
            "class Project(Base):\n"
            "    __tablename__ = 'projects'\n\n"
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
            "    name: Mapped[str] = mapped_column(String(255), nullable=False)\n"
            "    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))\n\n"
            "    owner: Mapped['User'] = relationship('User', back_populates='projects')\n"
            "    tags: Mapped[List['Tag']] = relationship('Tag', secondary='project_tags', back_populates='projects')\n"
        ),
        "backend/app/models/profile.py": (
            "from sqlalchemy import String, Integer, ForeignKey\n"
            "from sqlalchemy.orm import Mapped, mapped_column, relationship\n"
            "from backend.app.database.base import Base\n\n"
            "class Profile(Base):\n"
            "    __tablename__ = 'profiles'\n\n"
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
            "    bio: Mapped[str] = mapped_column(String(500), nullable=True)\n"
            "    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)\n\n"
            "    user: Mapped['User'] = relationship('User', back_populates='profile')\n"
        ),
        "backend/app/models/tag.py": (
            "from typing import List\n"
            "from sqlalchemy import String, Integer\n"
            "from sqlalchemy.orm import Mapped, mapped_column, relationship\n"
            "from backend.app.database.base import Base\n\n"
            "class Tag(Base):\n"
            "    __tablename__ = 'tags'\n\n"
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
            "    name: Mapped[str] = mapped_column(String(50), unique=True)\n\n"
            "    projects: Mapped[List['Project']] = relationship('Project', secondary='project_tags', back_populates='tags')\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("models.zip", zip_buf, "application/zip")})

    # 1. Trigger analyze
    analyze_res = client.post(f"/api/v1/projects/{proj_id}/database/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["status"] == "ANALYZED"
    assert data["total_models"] >= 4
    assert data["total_relationships"] >= 3

    # 2. Get Models
    models_res = client.get(f"/api/v1/projects/{proj_id}/database/models")
    assert models_res.status_code == 200
    models = models_res.json()["models"]

    table_names = [m["table_name"] for m in models]
    assert "users" in table_names
    assert "projects" in table_names
    assert "profiles" in table_names
    assert "tags" in table_names

    # Check User fields
    user_model = next(m for m in models if m["table_name"] == "users")
    field_names = [f["name"] for f in user_model["fields"]]
    assert "id" in field_names
    assert "email" in field_names
    assert "is_active" in field_names

    # Check Project foreign key
    proj_model = next(m for m in models if m["table_name"] == "projects")
    user_id_field = next(f for f in proj_model["fields"] if f["name"] == "user_id")
    assert user_id_field["foreign_key"] == "users.id"

    # 3. Get Relationships
    rels_res = client.get(f"/api/v1/projects/{proj_id}/database/relationships")
    assert rels_res.status_code == 200
    rels = rels_res.json()["relationships"]

    rel_types = {r["relationship_type"] for r in rels}
    assert "ONE_TO_MANY" in rel_types
    assert "ONE_TO_ONE" in rel_types or "MANY_TO_MANY" in rel_types

    # 4. Get Mermaid Diagram
    diag_res = client.get(f"/api/v1/projects/{proj_id}/database/diagram")
    assert diag_res.status_code == 200
    diag = diag_res.json()
    assert "erDiagram" in diag["mermaid_code"]
    assert "users {" in diag["mermaid_code"]
    assert "projects {" in diag["mermaid_code"]

    client.delete(f"/api/v1/projects/{proj_id}")


def test_django_and_raw_sql_analysis(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Django SQL DB Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "models.py": (
            "from django.db import models\n\n"
            "class Customer(models.Model):\n"
            "    name = models.CharField(max_length=100)\n"
            "    email = models.EmailField(unique=True)\n\n"
            "class Order(models.Model):\n"
            "    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)\n"
            "    total = models.DecimalField(max_digits=10, decimal_places=2)\n"
        ),
        "schema.sql": (
            "CREATE TABLE products (\n"
            "    id INT PRIMARY KEY,\n"
            "    name VARCHAR(255) NOT NULL,\n"
            "    price DECIMAL(10, 2)\n"
            ");\n\n"
            "CREATE TABLE order_items (\n"
            "    id INT PRIMARY KEY,\n"
            "    product_id INT REFERENCES products(id),\n"
            "    quantity INT NOT NULL\n"
            ");\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("mixed_db.zip", zip_buf, "application/zip")})

    models_res = client.get(f"/api/v1/projects/{proj_id}/database/models")
    assert models_res.status_code == 200
    models = models_res.json()["models"]

    table_names = [m["table_name"] for m in models]
    assert "products" in table_names
    assert "order_items" in table_names

    # Check relationships
    rels_res = client.get(f"/api/v1/projects/{proj_id}/database/relationships")
    assert rels_res.status_code == 200
    rels = rels_res.json()["relationships"]
    assert len(rels) >= 2

    client.delete(f"/api/v1/projects/{proj_id}")
