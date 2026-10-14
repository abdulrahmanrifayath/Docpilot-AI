import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_phase13_developer_onboarding_guide_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Prepare Realistic Multi-Tier Project with Full Setup Evidence
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # README
            zf.writestr(
                "README.md",
                """# Enterprise Microservice Platform

A distributed, asynchronous service for managing users, transactions, and fulfillment.

## Prerequisites
- Python 3.12+
- Node.js 20+
- Docker and Docker Compose

## Quick Start
```bash
cp .env.example .env
docker compose up -d
npm install
pytest
```
""",
            )

            # package.json
            zf.writestr(
                "package.json",
                """{
  "name": "enterprise-platform",
  "version": "1.0.0",
  "engines": {
    "node": ">=20.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "^18.2.0"
  }
}
""",
            )

            # requirements.txt
            zf.writestr(
                "requirements.txt",
                """fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlalchemy>=2.0.0
pytest>=7.4.0
pydantic>=2.0.0
""",
            )

            # Dockerfile
            zf.writestr(
                "Dockerfile",
                """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
            )

            # docker-compose.yml
            zf.writestr(
                "docker-compose.yml",
                """version: '3.8'
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: app_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5432:5432"
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
""",
            )

            # Makefile
            zf.writestr(
                "Makefile",
                """install:
	pip install -r requirements.txt
	npm install

test:
	pytest
	npm test

run:
	uvicorn main:app --reload

lint:
	flake8 .
	npm run lint
""",
            )

            # .env.example
            zf.writestr(
                ".env.example",
                """DATABASE_URL=postgresql://postgres:secretpassword@localhost:5432/app_db
JWT_SECRET=super_secret_jwt_key_2026
PORT=8000
DEBUG=True
API_KEY=sample_live_key_99
""",
            )

            # alembic.ini
            zf.writestr("alembic.ini", "[alembic]\nscript_location = alembic\n")

            # Source files
            zf.writestr(
                "main.py",
                """from fastapi import FastAPI
from routers.auth import auth_router
from routers.orders import order_router

app = FastAPI(title="Enterprise Platform", version="1.0.0")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(order_router, prefix="/orders", tags=["orders"])

@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
""",
            )
            zf.writestr(
                "routers/auth.py",
                """from fastapi import APIRouter
from services.auth_service import AuthService

auth_router = APIRouter()

@auth_router.post("/login")
def login(creds: dict):
    return AuthService().authenticate(creds.get("username"), creds.get("password"))

@auth_router.post("/register")
def register(user_data: dict):
    return AuthService().register_user(user_data)
""",
            )
            zf.writestr(
                "routers/orders.py",
                """from fastapi import APIRouter
from services.order_service import OrderService

order_router = APIRouter()

@order_router.post("/checkout")
def checkout(payload: dict):
    return OrderService().checkout(payload)
""",
            )
            zf.writestr(
                "services/auth_service.py",
                """class AuthService:
    def authenticate(self, username, password):
        return {"token": "jwt_sample", "type": "bearer"}

    def register_user(self, data):
        return {"id": 1, "username": data.get("username")}
""",
            )
            zf.writestr(
                "services/order_service.py",
                """class OrderService:
    def checkout(self, payload):
        return {"order_id": 999, "status": "CONFIRMED"}
""",
            )
            zf.writestr(
                "models/models.py",
                """from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
""",
            )

        zip_bytes = zip_buffer.getvalue()

        # 2. Create Project and upload zip
        create_res = await client.post(
            "/api/v1/projects",
            json={"name": "Enterprise Platform", "source_type": "zip"},
        )
        assert create_res.status_code == 201
        project_data = create_res.json()
        proj_id = project_data["id"]

        upload_res = await client.post(
            f"/api/v1/projects/{proj_id}/upload",
            files={"file": ("repo.zip", zip_bytes, "application/zip")},
        )
        assert upload_res.status_code == 200

        # Run analysis pipeline stages
        await client.post(f"/api/v1/projects/{proj_id}/scan")
        await client.post(f"/api/v1/projects/{proj_id}/parse")
        await client.post(f"/api/v1/projects/{proj_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{proj_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{proj_id}/database/analyze")
        await client.post(f"/api/v1/projects/{proj_id}/knowledge/build")
        await client.post(f"/api/v1/projects/{proj_id}/sequences/generate")

        # 3. Generate Onboarding Guide: POST /api/v1/projects/{project_id}/onboarding/generate
        gen_res = await client.post(f"/api/v1/projects/{proj_id}/onboarding/generate")
        assert gen_res.status_code == 200, gen_res.text
        guide = gen_res.json()

        assert guide["project_id"] == proj_id
        assert guide["title"] == "Developer Onboarding Guide: Enterprise Platform"
        assert len(guide["markdown_content"]) > 500

        # 4. Verify all 15 required sections are present
        sections = guide["sections"]
        assert len(sections) == 15
        section_keys = [s["key"] for s in sections]

        expected_keys = [
            "overview",
            "tech_stack",
            "repo_structure",
            "prerequisites",
            "env_setup",
            "installation",
            "database_setup",
            "backend_startup",
            "frontend_startup",
            "important_modules",
            "auth_flow",
            "important_apis",
            "dev_workflow",
            "testing",
            "deployment",
        ]
        for key in expected_keys:
            assert key in section_keys, f"Missing required section key: {key}"

        # 5. Verify Command Detection and Verification
        # Check environment setup command (cp .env.example .env)
        env_section = next(s for s in sections if s["key"] == "env_setup")
        assert env_section["status"] == "DETECTED"
        assert len(env_section["detected_commands"]) > 0
        env_cmd = env_section["detected_commands"][0]
        assert "cp .env.example .env" in env_cmd["command"]
        assert env_cmd["source_file"] == ".env.example"
        assert env_cmd["verified"] is True

        # Check installation commands
        install_section = next(s for s in sections if s["key"] == "installation")
        assert install_section["status"] == "DETECTED"
        assert any("pip install -r requirements.txt" in c["command"] for c in install_section["detected_commands"])
        assert any("npm install" in c["command"] for c in install_section["detected_commands"])
        for cmd in install_section["detected_commands"]:
            assert cmd["verified"] is True

        # Check database setup (docker compose up -d db, alembic upgrade head)
        db_section = next(s for s in sections if s["key"] == "database_setup")
        assert db_section["status"] == "DETECTED"
        assert any("docker compose up -d db" in c["command"] for c in db_section["detected_commands"])
        assert any("alembic upgrade head" in c["command"] for c in db_section["detected_commands"])

        # Check backend startup
        be_section = next(s for s in sections if s["key"] == "backend_startup")
        assert be_section["status"] == "DETECTED"
        assert any("uvicorn main:app" in c["command"] for c in be_section["detected_commands"])

        # Check testing
        test_section = next(s for s in sections if s["key"] == "testing")
        assert test_section["status"] == "DETECTED"
        assert any("pytest" in c["command"] for c in test_section["detected_commands"])

        # Check deployment
        deploy_section = next(s for s in sections if s["key"] == "deployment")
        assert deploy_section["status"] == "DETECTED"
        assert any("docker build" in c["command"] for c in deploy_section["detected_commands"])
        assert any("docker compose up -d" in c["command"] for c in deploy_section["detected_commands"])

        # 6. Test GET Onboarding Guide: GET /api/v1/projects/{project_id}/onboarding
        get_res = await client.get(f"/api/v1/projects/{proj_id}/onboarding")
        assert get_res.status_code == 200
        get_guide = get_res.json()
        assert get_guide["id"] == guide["id"]
        assert get_guide["markdown_content"] == guide["markdown_content"]

        # 7. Test Missing Section Detection on Minimal Repo
        # Minimal repository without .env.example, without docker, without db
        min_buf = io.BytesIO()
        with zipfile.ZipFile(min_buf, "w") as zf:
            zf.writestr("script.py", "print('hello world')")

        min_create = await client.post(
            "/api/v1/projects",
            json={"name": "Minimal Script Repo", "source_type": "zip"},
        )
        min_proj_id = min_create.json()["id"]

        await client.post(
            f"/api/v1/projects/{min_proj_id}/upload",
            files={"file": ("repo.zip", min_buf.getvalue(), "application/zip")},
        )
        await client.post(f"/api/v1/projects/{min_proj_id}/scan")
        await client.post(f"/api/v1/projects/{min_proj_id}/parse")

        min_guide_res = await client.post(f"/api/v1/projects/{min_proj_id}/onboarding/generate")
        assert min_guide_res.status_code == 200
        min_guide = min_guide_res.json()

        # Should have missing sections clearly marked
        assert len(min_guide["missing_sections"]) > 0
        min_sections = min_guide["sections"]
        min_env = next(s for s in min_sections if s["key"] == "env_setup")
        assert min_env["is_missing"] is True
        assert min_env["status"] == "NOT_DETECTED"
        assert "Not detected automatically. Manual configuration may be required." in min_env["content"]

        min_deploy = next(s for s in min_sections if s["key"] == "deployment")
        assert min_deploy["is_missing"] is True
        assert "Not detected automatically. Manual configuration may be required." in min_deploy["content"]
