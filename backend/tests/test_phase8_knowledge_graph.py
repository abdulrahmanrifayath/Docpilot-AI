import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_unified_knowledge_graph_pipeline_and_queries():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 8 Knowledge Graph Project",
                "description": "Multi-tier full-stack application for Unified Project Knowledge Graph testing",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Package sample multi-tier codebase
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Database models
            zf.writestr(
                "backend/models/user.py",
                "from sqlalchemy import Column, Integer, String, Boolean\n"
                "from sqlalchemy.orm import declarative_base, relationship\n"
                "Base = declarative_base()\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    username = Column(String(50), nullable=False)\n"
                "    email = Column(String(100), nullable=False)\n"
                "    is_active = Column(Boolean, default=True)\n"
            )

            # Service & Repository
            zf.writestr(
                "backend/services/user_service.py",
                "from backend.models.user import User\n"
                "\n"
                "class UserRepository:\n"
                "    def find_by_email(self, email: str):\n"
                "        return User()\n"
                "\n"
                "class UserService:\n"
                "    def __init__(self):\n"
                "        self.repo = UserRepository()\n"
                "\n"
                "    def authenticate_user(self, email: str, password: str):\n"
                "        user = self.repo.find_by_email(email)\n"
                "        return user\n"
            )

            # API routes
            zf.writestr(
                "backend/api/auth.py",
                "from fastapi import APIRouter, Depends\n"
                "from pydantic import BaseModel\n"
                "from backend.services.user_service import UserService\n"
                "\n"
                "router = APIRouter(prefix='/api/v1/auth', tags=['Authentication'])\n"
                "\n"
                "class LoginRequest(BaseModel):\n"
                "    email: str\n"
                "    password: str\n"
                "\n"
                "class UserResponse(BaseModel):\n"
                "    id: str\n"
                "    email: str\n"
                "\n"
                "def get_user_service():\n"
                "    return UserService()\n"
                "\n"
                "@router.post('/login', response_model=UserResponse)\n"
                "def login_endpoint(payload: LoginRequest, service = Depends(get_user_service)):\n"
                "    return service.authenticate_user(payload.email, payload.password)\n"
                "\n"
                "@router.get('/profile')\n"
                "def get_profile():\n"
                "    return {'status': 'ok'}\n"
            )

            # Frontend API client
            zf.writestr(
                "frontend/src/api/authClient.ts",
                "export async function loginApi(email: string, pass: string) {\n"
                "  return fetch('/api/v1/auth/login');\n"
                "}\n"
            )

        zip_buf.seek(0)

        # 3. Upload project source
        upload_res = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert upload_res.status_code == 200

        # 4. Run preceding analyzers to populate entities, APIs, DB models
        await client.post(f"/api/v1/projects/{project_id}/scan")
        await client.post(f"/api/v1/projects/{project_id}/parse")
        await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{project_id}/database/analyze")

        # 5. Build Unified Knowledge Graph (POST /knowledge/build)
        build_res = await client.post(f"/api/v1/projects/{project_id}/knowledge/build")
        assert build_res.status_code == 200
        build_data = build_res.json()
        assert build_data["status"] == "BUILT"
        assert build_data["total_nodes"] >= 10
        assert build_data["total_edges"] >= 10
        assert "api" in build_data["node_types"]
        assert "database" in build_data["node_types"]
        assert "service" in build_data["node_types"] or "class" in build_data["node_types"]
        assert "CONTAINS" in build_data["relationship_types"]

        # 6. Retrieve Unified Knowledge Graph (GET /knowledge/graph)
        graph_res = await client.get(f"/api/v1/projects/{project_id}/knowledge/graph")
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert len(graph_data["nodes"]) >= 10
        assert len(graph_data["edges"]) >= 10
        assert graph_data["stats"]["total_nodes"] == build_data["total_nodes"]

        # 7. Test Filtering by Node Types (e.g. node_types=api,database)
        filtered_res = await client.get(
            f"/api/v1/projects/{project_id}/knowledge/graph?node_types=api,database"
        )
        assert filtered_res.status_code == 200
        filtered_graph = filtered_res.json()
        for node in filtered_graph["nodes"]:
            assert node["node_type"] in ("api", "database")

        # 8. Test Search Filter
        search_res = await client.get(f"/api/v1/projects/{project_id}/knowledge/graph?search=login")
        assert search_res.status_code == 200
        search_nodes = search_res.json()["nodes"]
        assert len(search_nodes) >= 1
        assert any("login" in n["name"].lower() or "login" in n["label"].lower() for n in search_nodes)

        # 9. Test Focus Mode (focus on User model or UserService)
        focus_res = await client.get(
            f"/api/v1/projects/{project_id}/knowledge/graph?focus_id=User&depth=2"
        )
        assert focus_res.status_code == 200
        focus_graph = focus_res.json()
        assert focus_graph["focus_id"] is not None
        print("FOCUS ID:", focus_graph["focus_id"])
        print("FOCUS NODES:", [(n["name"], n["node_type"]) for n in focus_graph["nodes"]])
        assert len(focus_graph["nodes"]) >= 1
        assert any(n["name"] == "User" for n in focus_graph["nodes"])

        # 10. Test Entity Deep Query (GET /knowledge/entity/{entity_id})
        # Find UserService node
        all_nodes = graph_data["nodes"]
        user_service_node = next(
            (n for n in all_nodes if "UserService" in n["name"]), None
        )
        assert user_service_node is not None

        entity_res = await client.get(
            f"/api/v1/projects/{project_id}/knowledge/entity/{user_service_node['id']}"
        )
        assert entity_res.status_code == 200
        entity_detail = entity_res.json()
        assert entity_detail["entity"]["name"] == user_service_node["name"]
        
        # Verify cross-tier connections:
        # Connected database models: UserService queries User database model
        assert len(entity_detail["connected_database_models"]) >= 1
        assert any(m["name"] == "User" for m in entity_detail["connected_database_models"])

        # Test API entity query (login_endpoint or /api/v1/auth/login)
        api_node = next((n for n in all_nodes if n["node_type"] == "api" and "login" in n["name"]), None)
        assert api_node is not None
        api_detail_res = await client.get(
            f"/api/v1/projects/{project_id}/knowledge/entity/{api_node['id']}"
        )
        assert api_detail_res.status_code == 200
        api_detail = api_detail_res.json()
        assert api_detail["entity"]["node_type"] == "api"
        # Connected downstream database models reachable from this API
        assert len(api_detail["connected_database_models"]) >= 1
        assert any(m["name"] == "User" for m in api_detail["connected_database_models"])


@pytest.mark.asyncio
async def test_knowledge_graph_consistency_and_pagination():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Consistency Verification Project",
                "description": "Verifies graph integrity, pagination, and consistency constraints",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # Package project
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "models.py",
                "class Item:\n"
                "    __tablename__ = 'items'\n"
                "    id = 1\n"
            )
            zf.writestr(
                "service.py",
                "from models import Item\n"
                "def calculate_total(item_id: int):\n"
                "    return item_id * 10\n"
            )
            zf.writestr(
                "api.py",
                "from fastapi import APIRouter\n"
                "from service import calculate_total\n"
                "router = APIRouter()\n"
                "@router.get('/items/{item_id}/total')\n"
                "def get_total(item_id: int):\n"
                "    return {'total': calculate_total(item_id)}\n"
            )
        zip_buf.seek(0)

        await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        await client.post(f"/api/v1/projects/{project_id}/scan")
        await client.post(f"/api/v1/projects/{project_id}/parse")
        await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{project_id}/database/analyze")

        build_res = await client.post(f"/api/v1/projects/{project_id}/knowledge/build")
        assert build_res.status_code == 200

        # Full graph consistency check
        full_graph = (await client.get(f"/api/v1/projects/{project_id}/knowledge/graph")).json()
        nodes = full_graph["nodes"]
        edges = full_graph["edges"]
        node_ids = {n["id"] for n in nodes}

        # 1. No dangling edges (every edge source and target must be in node_ids)
        for edge in edges:
            assert edge["source_id"] in node_ids, f"Dangling source in edge: {edge['source_id']}"
            assert edge["target_id"] in node_ids, f"Dangling target in edge: {edge['target_id']}"

        # 2. No duplicate edges with identical (source_id, target_id, relationship_type)
        edge_keys = [(e["source_id"], e["target_id"], e["relationship_type"]) for e in edges]
        assert len(edge_keys) == len(set(edge_keys)), "Duplicate edge found in knowledge graph!"

        # 3. Test Pagination (limit=3, offset=0 and offset=3)
        page1 = (await client.get(f"/api/v1/projects/{project_id}/knowledge/graph?limit=3&offset=0")).json()
        page2 = (await client.get(f"/api/v1/projects/{project_id}/knowledge/graph?limit=3&offset=3")).json()
        assert len(page1["nodes"]) <= 3
        assert len(page2["nodes"]) <= 3
        page1_ids = {n["id"] for n in page1["nodes"]}
        page2_ids = {n["id"] for n in page2["nodes"]}
        assert page1_ids.isdisjoint(page2_ids)

        # 4. Nonexistent entity detail query should return 404
        not_found_res = await client.get(f"/api/v1/projects/{project_id}/knowledge/entity/non_existent_id")
        assert not_found_res.status_code == 404

