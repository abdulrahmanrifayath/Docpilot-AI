import io
import zipfile
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


def make_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, c in files_dict.items():
            zf.writestr(p, c)
    buf.seek(0)
    return buf


def run_phase7_live_tests():
    print("=========================================================")
    print("PHASE 7 LIVE VERIFICATION: DATABASE STRUCTURE & ER")
    print("=========================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live Database Schema Project",
            "description": "SQLAlchemy and SQL schema discovery validation",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "backend/app/models/user.py": (
            'from typing import List, Optional\n'
            'from sqlalchemy import String, Integer, Boolean\n'
            'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
            'from backend.app.database.base import Base\n\n'
            'class User(Base):\n'
            '    __tablename__ = "users"\n\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)\n'
            '    username: Mapped[str] = mapped_column(String(100), nullable=False)\n'
            '    is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n\n'
            '    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner")\n'
            '    profile: Mapped[Optional["Profile"]] = relationship("Profile", back_populates="user", uselist=False)\n'
        ),
        "backend/app/models/project.py": (
            'from typing import List\n'
            'from sqlalchemy import String, Integer, ForeignKey\n'
            'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
            'from backend.app.database.base import Base\n\n'
            'class Project(Base):\n'
            '    __tablename__ = "projects"\n\n'
            '    id: Mapped[str] = mapped_column(String(36), primary_key=True)\n'
            '    name: Mapped[str] = mapped_column(String(255), nullable=False)\n'
            '    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))\n\n'
            '    owner: Mapped["User"] = relationship("User", back_populates="projects")\n'
            '    tags: Mapped[List["Tag"]] = relationship("Tag", secondary="project_tags", back_populates="projects")\n'
        ),
        "backend/app/models/tag.py": (
            'from typing import List\n'
            'from sqlalchemy import String, Integer\n'
            'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
            'from backend.app.database.base import Base\n\n'
            'class Tag(Base):\n'
            '    __tablename__ = "tags"\n\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    name: Mapped[str] = mapped_column(String(50), unique=True)\n\n'
            '    projects: Mapped[List["Project"]] = relationship("Project", secondary="project_tags", back_populates="tags")\n'
        ),
        "backend/app/models/profile.py": (
            'from sqlalchemy import String, Integer, ForeignKey\n'
            'from sqlalchemy.orm import Mapped, mapped_column, relationship\n'
            'from backend.app.database.base import Base\n\n'
            'class Profile(Base):\n'
            '    __tablename__ = "profiles"\n\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    bio: Mapped[str] = mapped_column(String(500), nullable=True)\n'
            '    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)\n\n'
            '    user: Mapped["User"] = relationship("User", back_populates="profile")\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("db_project.zip", sample_zip, "application/zip")})

    # 2. Trigger Database Analysis
    print("\n--- 1. Testing POST /database/analyze ---")
    analyze_res = client.post(f"/api/v1/projects/{p_id}/database/analyze")
    assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
    analyze_data = analyze_res.json()

    print(f"Status: {analyze_data['status']}")
    print(f"Total Models: {analyze_data['total_models']}")
    print(f"Total Relationships: {analyze_data['total_relationships']}")
    print(f"Duration: {analyze_data['duration_ms']}ms")

    assert analyze_data["status"] == "ANALYZED"
    assert analyze_data["total_models"] >= 4
    assert analyze_data["total_relationships"] >= 3

    # 3. Query GET /database/models
    print("\n--- 2. Testing GET /database/models ---")
    models_res = client.get(f"/api/v1/projects/{p_id}/database/models")
    assert models_res.status_code == 200
    models_data = models_res.json()
    print(f"Retrieved {models_data['total_models']} models")

    for m in models_data["models"]:
        pk_cols = [f["name"] for f in m["fields"] if f["primary_key"]]
        fk_cols = [f"{f['name']} -> {f['foreign_key']}" for f in m["fields"] if f["foreign_key"]]
        print(f"  • Table '{m['table_name']}' (Model: {m['model_name']}, {m['orm_framework']})")
        print(f"    - Fields ({len(m['fields'])}): {[f['name'] + ' (' + f['data_type'] + ')' for f in m['fields']]}")
        print(f"    - PKs: {pk_cols} | FKs: {fk_cols}")

    # 4. Query GET /database/relationships
    print("\n--- 3. Testing GET /database/relationships ---")
    rels_res = client.get(f"/api/v1/projects/{p_id}/database/relationships")
    assert rels_res.status_code == 200
    rels_data = rels_res.json()
    print(f"Retrieved {rels_data['total_relationships']} relationships")

    for r in rels_data["relationships"]:
        print(f"  • {r['source_table']} {r['cardinality_mermaid']} {r['target_table']} [{r['relationship_type']}]")

    # 5. Query GET /database/diagram
    print("\n--- 4. Testing GET /database/diagram ---")
    diag_res = client.get(f"/api/v1/projects/{p_id}/database/diagram")
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    print(f"Mermaid Code Generated ({len(diag_data['mermaid_code'])} bytes):")
    print("--------------------------------------------------")
    print(diag_data["mermaid_code"])
    print("--------------------------------------------------")

    assert "erDiagram" in diag_data["mermaid_code"]
    assert "users {" in diag_data["mermaid_code"]
    assert "projects {" in diag_data["mermaid_code"]

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n=========================================================")
    print("ALL PHASE 7 DATABASE TESTS PASSED SUCCESSFULLY!")
    print("=========================================================")


if __name__ == "__main__":
    run_phase7_live_tests()
