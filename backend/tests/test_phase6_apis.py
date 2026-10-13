import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_fastapi_and_flask_and_express_api_discovery():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 6 API Discovery Demo",
                "description": "Multi-framework API route detection test project",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Build multi-framework project zip (FastAPI, Flask, Express)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # FastAPI file
            zf.writestr(
                "backend/api/users.py",
                "from typing import List, Optional\n"
                "from fastapi import APIRouter, Depends, HTTPException, Query, status\n"
                "from pydantic import BaseModel\n"
                "\n"
                "router = APIRouter(prefix='/api/v1/users', tags=['Users'])\n"
                "\n"
                "class UserCreate(BaseModel):\n"
                "    email: str\n"
                "    password: str\n"
                "\n"
                "class UserResponse(BaseModel):\n"
                "    id: str\n"
                "    email: str\n"
                "\n"
                "def get_db():\n"
                "    yield None\n"
                "\n"
                "def get_current_user():\n"
                "    return {'id': '123', 'email': 'admin@test.com'}\n"
                "\n"
                "@router.get('', response_model=List[UserResponse])\n"
                "def list_users(limit: int = 10, search: Optional[str] = None, db = Depends(get_db)):\n"
                "    \"\"\"Retrieve paginated list of registered users.\"\"\"\n"
                "    return []\n"
                "\n"
                "@router.post('', response_model=UserResponse, status_code=status.HTTP_201_CREATED)\n"
                "def create_user(user: UserCreate, current_user = Depends(get_current_user)):\n"
                "    \"\"\"Register a new user account with administrative authorization.\"\"\"\n"
                "    return {'id': 'new', 'email': user.email}\n"
                "\n"
                "@router.get('/{user_id}', response_model=UserResponse)\n"
                "def get_user_by_id(user_id: str, db = Depends(get_db)):\n"
                "    \"\"\"Fetch user details by ID.\"\"\"\n"
                "    return {'id': user_id, 'email': 'found@test.com'}\n"
            )

            # Flask file
            zf.writestr(
                "backend/flask_app/auth.py",
                "from flask import Blueprint, request, jsonify\n"
                "\n"
                "bp = Blueprint('auth_bp', __name__, url_prefix='/auth')\n"
                "\n"
                "def login_required(f):\n"
                "    return f\n"
                "\n"
                "@bp.route('/login', methods=['POST'])\n"
                "def login_post():\n"
                "    \"\"\"Login endpoint.\"\"\"\n"
                "    return jsonify({'token': 'jwt_xyz'})\n"
                "\n"
                "@bp.route('/profile', methods=['GET'])\n"
                "@login_required\n"
                "def get_profile():\n"
                "    \"\"\"Protected user profile.\"\"\"\n"
                "    return jsonify({'user': 'me'})\n"
            )

            # Express (JS/TS) file
            zf.writestr(
                "frontend/server/routes.ts",
                "import express, { Request, Response } from 'express';\n"
                "const router = express.Router();\n"
                "\n"
                "const verifyToken = (req: Request, res: Response, next: any) => next();\n"
                "\n"
                "router.get('/api/health', (req: Request, res: Response) => {\n"
                "  res.json({ status: 'ok' });\n"
                "});\n"
                "\n"
                "router.post('/api/orders', verifyToken, (req: Request, res: Response) => {\n"
                "  res.status(201).json({ id: 'order_1' });\n"
                "});\n"
            )

        # 3. Upload Zip
        upload_res = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert upload_res.status_code == 200

        # 4. Analyze APIs: POST /projects/{project_id}/apis/analyze
        analyze_res = await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        assert analyze_res.status_code == 200
        analysis_data = analyze_res.json()
        assert analysis_data["status"] == "ANALYZED"
        assert analysis_data["total_endpoints"] >= 6
        assert analysis_data["authenticated_endpoints"] >= 3  # create_user (FastAPI), get_profile (Flask), /api/orders (Express)
        assert analysis_data["public_endpoints"] >= 2
        assert "GET" in analysis_data["method_breakdown"]
        assert "POST" in analysis_data["method_breakdown"]
        assert "FastAPI" in analysis_data["framework_breakdown"]

        # 5. List APIs: GET /projects/{project_id}/apis
        list_res = await client.get(f"/api/v1/projects/{project_id}/apis")
        assert list_res.status_code == 200
        apis = list_res.json()
        assert len(apis) == analysis_data["total_endpoints"]

        # Verify FastAPI route details
        create_user_api = next((a for a in apis if a["path"] == "/api/v1/users" and a["method"] == "POST"), None)
        assert create_user_api is not None
        assert create_user_api["handler_name"] == "create_user"
        assert create_user_api["authentication_required"] is True
        assert create_user_api["response_schema"]["status_code"] == 201
        assert "UserResponse" in create_user_api["response_schema"]["model"]
        assert create_user_api["request_schema"]["body_model"] == "UserCreate"
        assert "Users" in create_user_api["tags"]

        # Verify Path param route
        get_user_api = next((a for a in apis if "/{user_id}" in a["path"]), None)
        assert get_user_api is not None
        path_param_names = [p["name"] for p in get_user_api["request_schema"]["parameters"] if p["in"] == "path"]
        assert "user_id" in path_param_names

        # Verify Flask route
        flask_profile = next((a for a in apis if a["path"] == "/auth/profile"), None)
        assert flask_profile is not None
        assert flask_profile["authentication_required"] is True
        assert flask_profile["metadata"]["framework"] == "Flask"

        # Verify Express route
        express_orders = next((a for a in apis if a["path"] == "/api/orders"), None)
        assert express_orders is not None
        assert express_orders["method"] == "POST"
        assert express_orders["authentication_required"] is True
        assert express_orders["metadata"]["framework"] == "Express"

        # 6. Filter by method
        get_res = await client.get(f"/api/v1/projects/{project_id}/apis?method=GET")
        assert get_res.status_code == 200
        get_apis = get_res.json()
        assert all(a["method"] == "GET" for a in get_apis)

        # 7. Filter by auth_required
        auth_res = await client.get(f"/api/v1/projects/{project_id}/apis?auth_required=true")
        assert auth_res.status_code == 200
        auth_apis = auth_res.json()
        assert all(a["authentication_required"] is True for a in auth_apis)

        # 8. Single API Endpoint: GET /projects/{project_id}/apis/{api_id}
        single_res = await client.get(f"/api/v1/projects/{project_id}/apis/{create_user_api['id']}")
        assert single_res.status_code == 200
        detail = single_res.json()
        assert detail["id"] == create_user_api["id"]
        assert detail["handler_name"] == "create_user"
        assert "related_components" in detail
