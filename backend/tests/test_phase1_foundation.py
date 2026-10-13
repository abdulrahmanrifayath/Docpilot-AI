import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_health_check_contract():
    """Verify GET /health returns the exact contract required by Phase 1."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "status": "healthy",
            "service": "docpilot-ai",
        }


@pytest.mark.asyncio
async def test_system_status_endpoint():
    """Verify GET /api/v1/system/status returns required subsystem statuses without secrets."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ("operational", "degraded")

        # Application status
        assert "application" in data
        assert data["application"]["status"] == "running"
        assert "version" in data["application"]

        # Database status
        assert "database" in data
        assert data["database"]["status"] == "connected"
        assert data["database"]["type"] in ("sqlite", "postgresql")

        # AI Provider configuration status (no secrets!)
        assert "ai_provider" in data
        assert "provider" in data["ai_provider"]
        assert "model" in data["ai_provider"]
        assert "is_configured" in data["ai_provider"]
        # Ensure secret keys are NOT exposed
        assert "api_key" not in data["ai_provider"]
        assert "LLM_API_KEY" not in str(data)

        # Vector Database status
        assert "vector_database" in data
        assert "type" in data["vector_database"]
        assert "status" in data["vector_database"]


@pytest.mark.asyncio
async def test_centralized_exception_handling_not_found():
    """Verify centralized exception handler catches not found errors and returns standard JSON."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/projects/non-existent-uuid-12345")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "non-existent-uuid-12345" in data["error"]["message"]
