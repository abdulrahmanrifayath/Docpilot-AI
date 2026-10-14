import os
from pathlib import Path
import yaml
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.database.session import check_db_health, init_db

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_docker_compose_structure():
    compose_path = REPO_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml is missing in repo root"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    assert "services" in compose, "docker-compose.yml must define services"
    services = compose["services"]

    # 1. Required services
    assert "backend" in services, "Missing backend service in docker-compose.yml"
    assert "frontend" in services, "Missing frontend service in docker-compose.yml"
    assert "postgres" in services, "Missing postgres service in docker-compose.yml"
    assert "qdrant" in services, "Missing qdrant vector store in docker-compose.yml"

    # 2. Port mappings
    backend_ports = services["backend"].get("ports", [])
    assert any("8000:8000" in p for p in backend_ports), "Backend must expose 8000:8000"

    frontend_ports = services["frontend"].get("ports", [])
    assert any("3000:80" in p or "80:80" in p for p in frontend_ports), "Frontend must expose port 3000 or 80"

    postgres_ports = services["postgres"].get("ports", [])
    assert any("5432:5432" in str(p) for p in postgres_ports), "PostgreSQL must expose 5432"

    qdrant_ports = services["qdrant"].get("ports", [])
    assert any("6333:6333" in p for p in qdrant_ports), "Qdrant must expose 6333"

    # 3. Environment variables in backend
    backend_env = services["backend"].get("environment", [])
    backend_env_str = str(backend_env)
    assert "DATABASE_URL" in backend_env_str, "Backend must configure DATABASE_URL in docker-compose"
    assert "JWT_SECRET_KEY" in backend_env_str, "Backend must configure JWT_SECRET_KEY in docker-compose"
    assert "CORS_ORIGINS" in backend_env_str, "Backend must configure CORS_ORIGINS in docker-compose"

    # 4. Service dependencies & healthchecks
    assert "depends_on" in services["backend"], "Backend must declare depends_on"
    assert "postgres" in services["backend"]["depends_on"], "Backend must depend on postgres"
    assert "healthcheck" in services["postgres"], "Postgres must define a healthcheck"
    assert "healthcheck" in services["backend"], "Backend must define a healthcheck"
    assert "healthcheck" in services["frontend"], "Frontend must define a healthcheck"

    # 5. Persistent volumes
    assert "volumes" in compose, "docker-compose.yml must define named persistent volumes"
    volumes = compose["volumes"]
    assert "docpilot-pgdata" in volumes, "Missing docpilot-pgdata volume"
    assert "docpilot-data" in volumes, "Missing docpilot-data volume"
    assert "docpilot-uploads" in volumes, "Missing docpilot-uploads volume"

    # 6. Networks
    assert "networks" in compose, "docker-compose.yml must define networks"
    assert "docpilot-network" in compose["networks"], "Missing docpilot-network definition"


def test_backend_dockerfile():
    dockerfile_path = REPO_ROOT / "backend" / "Dockerfile"
    assert dockerfile_path.exists(), "backend/Dockerfile is missing"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in content, "Backend Dockerfile must use Python 3.12"
    assert "requirements.txt" in content, "Backend Dockerfile must install requirements.txt"
    assert "docpilot" in content, "Backend Dockerfile should configure an unprivileged user"
    assert "EXPOSE 8000" in content, "Backend Dockerfile must EXPOSE 8000"
    assert "HEALTHCHECK" in content, "Backend Dockerfile must declare HEALTHCHECK"
    assert "/health" in content, "Backend Dockerfile healthcheck must verify /health"

    # Check .dockerignore
    ignore_path = REPO_ROOT / "backend" / ".dockerignore"
    assert ignore_path.exists(), "backend/.dockerignore is missing"
    ignore_content = ignore_path.read_text(encoding="utf-8")
    assert "__pycache__" in ignore_content
    assert ".venv" in ignore_content or "venv" in ignore_content


def test_frontend_dockerfile_and_nginx():
    dockerfile_path = REPO_ROOT / "frontend" / "Dockerfile"
    assert dockerfile_path.exists(), "frontend/Dockerfile is missing"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM node:20-alpine" in content, "Frontend Dockerfile must build with node:20"
    assert "FROM nginx" in content, "Frontend Dockerfile must use nginx runtime"
    assert "npm run build" in content, "Frontend Dockerfile must execute npm run build"
    assert "EXPOSE 80" in content, "Frontend Dockerfile must EXPOSE 80"

    # Check nginx.conf
    nginx_path = REPO_ROOT / "frontend" / "nginx.conf"
    assert nginx_path.exists(), "frontend/nginx.conf is missing"
    nginx_content = nginx_path.read_text(encoding="utf-8")
    assert "proxy_pass http://backend:8000/api/;" in nginx_content, "nginx.conf must reverse-proxy /api/ to backend:8000"
    assert "try_files $uri $uri/ /index.html;" in nginx_content, "nginx.conf must handle client-side SPA routing"
    assert "gzip on;" in nginx_content, "nginx.conf should enable gzip compression"

    # Check .dockerignore
    ignore_path = REPO_ROOT / "frontend" / ".dockerignore"
    assert ignore_path.exists(), "frontend/.dockerignore is missing"
    ignore_content = ignore_path.read_text(encoding="utf-8")
    assert "node_modules" in ignore_content
    assert "dist" in ignore_content


def test_env_example_completeness_and_security():
    env_example_path = REPO_ROOT / ".env.example"
    assert env_example_path.exists(), ".env.example is missing in repo root"

    content = env_example_path.read_text(encoding="utf-8")
    required_vars = [
        "APP_NAME",
        "APP_ENV",
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "JWT_SECRET_KEY",
        "CORS_ORIGINS",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "VECTOR_STORE_TYPE",
        "MAX_UPLOAD_SIZE_MB",
    ]
    for var in required_vars:
        assert var in content, f".env.example is missing required variable: {var}"

    # Verify no real secrets or live API keys are committed in .env.example
    assert "sk-" not in content, "Do not commit live OpenAI secret keys"
    assert "AIzaSy" not in content, "Do not commit live Google Gemini secret keys"


@pytest.mark.asyncio
async def test_health_and_database_initialization():
    await init_db()
    health_status = await check_db_health()
    assert health_status["status"] == "connected", f"Database health check failed: {health_status}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        assert res.json()["service"] == "docpilot-ai"
