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


def test_fastapi_api_discovery(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "FastAPI Discovery Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "backend/app/main.py": (
            "from fastapi import FastAPI\n"
            "from backend.app.api.users import router as user_router\n\n"
            "app = FastAPI(title='Test API')\n"
            "@app.get('/health', summary='Health check')\n"
            "def health_check():\n"
            "    return {'status': 'ok'}\n"
        ),
        "backend/app/api/users.py": (
            "from fastapi import APIRouter, Depends, status\n"
            "from typing import List, Optional\n"
            "from pydantic import BaseModel\n\n"
            "class UserResponse(BaseModel):\n"
            "    id: int\n"
            "    email: str\n\n"
            "class UserCreate(BaseModel):\n"
            "    email: str\n"
            "    password: str\n\n"
            "router = APIRouter(prefix='/api/v1/users', tags=['Users'])\n\n"
            "@router.get('/{user_id}', response_model=UserResponse, summary='Get user by ID')\n"
            "def get_user(user_id: int, current_user = Depends(get_current_user)):\n"
            "    '''Fetch a single user by primary ID.'''\n"
            "    return {'id': user_id, 'email': 'user@example.com'}\n\n"
            "@router.post('/', response_model=UserResponse, status_code=status.HTTP_201_CREATED)\n"
            "def create_user(payload: UserCreate):\n"
            "    return {'id': 1, 'email': payload.email}\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("fastapi.zip", zip_buf, "application/zip")})

    # 1. Trigger API Analysis
    analyze_res = client.post(f"/api/v1/projects/{proj_id}/apis/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["status"] == "ANALYZED"
    assert data["total_apis"] >= 3
    assert data["apis_by_method"].get("GET", 0) >= 2
    assert data["apis_by_method"].get("POST", 0) >= 1
    assert data["apis_by_framework"].get("FastAPI", 0) >= 3

    # 2. Get API List
    apis_res = client.get(f"/api/v1/projects/{proj_id}/apis")
    assert apis_res.status_code == 200
    apis_data = apis_res.json()
    apis = apis_data["apis"]

    paths = [a["path"] for a in apis]
    assert "/health" in paths
    assert "/api/v1/users/{user_id}" in paths
    assert "/api/v1/users" in paths

    # Verify /api/v1/users/{user_id} details
    user_get = next(a for a in apis if a["path"] == "/api/v1/users/{user_id}")
    assert user_get["method"] == "GET"
    assert user_get["handler_name"] == "get_user"
    assert user_get["authentication_required"] is True
    assert "Users" in user_get["tags"]
    assert user_get["response_schema"]["response_model"] == "UserResponse"

    # Verify parameters
    params = user_get["request_schema"]["parameters"]
    assert any(p["name"] == "user_id" and p["in_location"] == "path" for p in params)
    assert any(p["name"] == "current_user" and p["in_location"] == "dependency" for p in params)

    # 3. Verify single endpoint GET /apis/{id}
    single_res = client.get(f"/api/v1/projects/{proj_id}/apis/{user_get['id']}")
    assert single_res.status_code == 200
    assert single_res.json()["handler_name"] == "get_user"

    # 4. Filter by method
    get_only = client.get(f"/api/v1/projects/{proj_id}/apis", params={"method": "POST"}).json()
    assert all(a["method"] == "POST" for a in get_only["apis"])

    client.delete(f"/api/v1/projects/{proj_id}")


def test_flask_and_express_api_discovery(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Flask Express Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "app.py": (
            "from flask import Flask, request\n"
            "app = Flask(__name__)\n\n"
            "@app.route('/login', methods=['POST'])\n"
            "@jwt_required()\n"
            "def login():\n"
            "    return {'token': 'jwt-token'}\n"
        ),
        "src/routes/products.js": (
            "const express = require('express');\n"
            "const router = express.Router();\n"
            "router.get('/products', authMiddleware, getProducts);\n"
            "router.delete('/products/:id', adminAuth, deleteProduct);\n"
            "module.exports = router;\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("mixed_apis.zip", zip_buf, "application/zip")})

    apis_res = client.get(f"/api/v1/projects/{proj_id}/apis")
    assert apis_res.status_code == 200
    apis = apis_res.json()["apis"]

    assert len(apis) >= 3

    # Check Flask endpoint
    flask_ep = next(a for a in apis if a["framework"] == "Flask")
    assert flask_ep["path"] == "/login"
    assert flask_ep["method"] == "POST"
    assert flask_ep["authentication_required"] is True

    # Check Express endpoints
    express_eps = [a for a in apis if a["framework"] == "Express"]
    assert len(express_eps) >= 2
    paths = [e["path"] for e in express_eps]
    assert "/products" in paths
    assert "/products/{id}" in paths

    client.delete(f"/api/v1/projects/{proj_id}")
