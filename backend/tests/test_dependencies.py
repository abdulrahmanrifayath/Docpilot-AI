import io
import zipfile
import pytest
from fastapi.testclient import TestClient


def make_test_zip(files_dict: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(path, content)
            else:
                zf.writestr(path, content)
    buf.seek(0)
    return buf


def test_python_dependency_analysis(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Dep Graph Python Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "app/api/auth.py": (
            "from fastapi import APIRouter\n"
            "from app.services.user_service import UserService\n\n"
            "router = APIRouter()\n"
            "def login_endpoint():\n"
            "    service = UserService()\n"
            "    return service.authenticate()\n"
        ),
        "app/services/user_service.py": (
            "from app.services.base_service import BaseService\n"
            "from app.repositories.user_repo import UserRepository\n"
            "from app.services.jwt_service import JWTService\n\n"
            "class UserService(BaseService):\n"
            "    def __init__(self, repo: UserRepository):\n"
            "        self.repo = repo\n"
            "        self.jwt = JWTService()\n\n"
            "    def authenticate(self):\n"
            "        return True\n"
        ),
        "app/services/base_service.py": "class BaseService:\n    pass\n",
        "app/repositories/user_repo.py": "class UserRepository:\n    pass\n",
        "app/services/jwt_service.py": "class JWTService:\n    pass\n",
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("py_deps.zip", zip_buf, "application/zip")})

    # 1. Analyze dependencies
    analyze_res = client.post(f"/api/v1/projects/{proj_id}/dependencies/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["status"] == "ANALYZED"
    assert data["total_nodes"] >= 5
    assert data["total_edges"] >= 4
    assert data["internal_edges"] >= 3

    # 2. Get list of dependencies
    deps_res = client.get(f"/api/v1/projects/{proj_id}/dependencies")
    assert deps_res.status_code == 200
    deps_list = deps_res.json()["dependencies"]

    rel_types = {d["relationship_type"] for d in deps_list}
    assert "IMPORTS" in rel_types
    assert "EXTENDS" in rel_types
    assert "DEPENDS_ON" in rel_types

    # Verify UserService EXTENDS BaseService
    extends_deps = [d for d in deps_list if d["relationship_type"] == "EXTENDS"]
    assert any(d["source_name"] == "UserService" and d["target_name"] == "BaseService" for d in extends_deps)

    # 3. Get graph for React Flow
    graph_res = client.get(f"/api/v1/projects/{proj_id}/dependencies/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    assert len(graph["nodes"]) >= 5
    assert len(graph["edges"]) >= 4
    node_labels = [n["label"] for n in graph["nodes"]]
    assert "UserService" in node_labels
    assert "BaseService" in node_labels

    # 4. Get entity dependencies
    ent_res = client.get(f"/api/v1/projects/{proj_id}/dependencies/entity/class:UserService")
    assert ent_res.status_code == 200
    ent_deps = ent_res.json()
    assert ent_deps["total_dependencies"] >= 1

    client.delete(f"/api/v1/projects/{proj_id}")


def test_typescript_dependency_graph(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Dep Graph TS Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "package.json": '{"name": "app"}\n',
        "src/App.tsx": (
            "import React from 'react';\n"
            "import { UserCard } from './components/UserCard';\n"
            "export const App = () => <UserCard />;\n"
        ),
        "src/components/UserCard.tsx": (
            "import React from 'react';\n"
            "import { ApiClient } from '../clients/ApiClient';\n"
            "export const UserCard = () => <div>Card</div>;\n"
        ),
        "src/clients/ApiClient.ts": (
            "import axios from 'axios';\n"
            "export class ApiClient extends BaseClient {\n"
            "}\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("ts_deps.zip", zip_buf, "application/zip")})

    graph_res = client.get(f"/api/v1/projects/{proj_id}/dependencies/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    node_ids = {n["id"] for n in graph["nodes"]}
    assert any("file:src/App.tsx" in nid for nid in node_ids)
    assert any("file:src/components/UserCard.tsx" in nid for nid in node_ids)

    # Check external package detection (axios, react)
    pkg_labels = [n["label"] for n in graph["nodes"] if n["type"] == "package"]
    assert "axios" in pkg_labels or "react" in pkg_labels

    client.delete(f"/api/v1/projects/{proj_id}")
