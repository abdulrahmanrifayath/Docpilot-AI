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


def test_unified_knowledge_graph_build_and_query(client: TestClient):
    proj = client.post(
        "/api/v1/projects",
        json={"name": "Knowledge Graph Test Project", "source_type": "zip"},
    ).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "backend/app/main.py": (
            'from fastapi import FastAPI\n'
            'from backend.app.routers import users\n\n'
            'app = FastAPI()\n'
            'app.include_router(users.router)\n'
        ),
        "backend/app/routers/users.py": (
            'from fastapi import APIRouter, Depends\n'
            'from backend.app.services.user_service import UserService\n'
            'from backend.app.models.user import User\n\n'
            'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
            '@router.get("", summary="Get all users")\n'
            'def list_users(service: UserService = Depends()):\n'
            '    return service.get_all()\n'
        ),
        "backend/app/services/user_service.py": (
            'from backend.app.models.user import User\n\n'
            'class UserService:\n'
            '    def get_all(self):\n'
            '        return []\n'
        ),
        "backend/app/models/user.py": (
            'from sqlalchemy import String, Integer\n'
            'from sqlalchemy.orm import Mapped, mapped_column\n'
            'from backend.app.database.base import Base\n\n'
            'class User(Base):\n'
            '    __tablename__ = "users"\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    email: Mapped[str] = mapped_column(String(255), unique=True)\n'
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("knowledge.zip", zip_buf, "application/zip")})

    # 1. Build Knowledge Graph
    build_res = client.post(f"/api/v1/projects/{proj_id}/knowledge/build")
    assert build_res.status_code == 200
    build_data = build_res.json()

    assert build_data["status"] == "BUILT"
    assert build_data["total_nodes"] > 5
    assert build_data["total_edges"] > 3
    assert "API" in build_data["counts_by_category"]
    assert "DATABASE_TABLE" in build_data["counts_by_category"]

    # 2. Query full graph
    graph_res = client.get(f"/api/v1/projects/{proj_id}/knowledge/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert graph_data["total_nodes"] == build_data["total_nodes"]

    node_categories = {n["category"] for n in graph_data["nodes"]}
    assert "FILE" in node_categories
    assert "FUNCTION" in node_categories or "CLASS" in node_categories
    assert "API" in node_categories
    assert "DATABASE_TABLE" in node_categories

    edge_relationships = {e["relationship"] for e in graph_data["edges"]}
    assert "CONTAINS" in edge_relationships or "DECLARES" in edge_relationships

    # 3. Filter by Category
    filter_res = client.get(f"/api/v1/projects/{proj_id}/knowledge/graph", params={"categories": "API,DATABASE_TABLE"})
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert all(n["category"] in ["API", "DATABASE_TABLE"] for n in filter_data["nodes"])

    # 4. Query entity detail
    api_node = next(n for n in graph_data["nodes"] if n["category"] == "API")
    entity_res = client.get(f"/api/v1/projects/{proj_id}/knowledge/entity/{api_node['id']}")
    assert entity_res.status_code == 200
    entity_data = entity_res.json()
    assert entity_data["node"]["name"] == api_node["name"]

    # 5. Focus mode query
    focus_res = client.get(
        f"/api/v1/projects/{proj_id}/knowledge/graph",
        params={"focus_node_id": api_node["id"], "depth": 1},
    )
    assert focus_res.status_code == 200
    focus_data = focus_res.json()
    assert any(n["id"] == api_node["id"] for n in focus_data["nodes"])
    assert focus_data["total_nodes"] <= graph_data["total_nodes"]

    client.delete(f"/api/v1/projects/{proj_id}")
