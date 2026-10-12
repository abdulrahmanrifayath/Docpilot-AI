import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "DocPilot AI" in data["app"]


@pytest.mark.asyncio
async def test_settings_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "llm_provider" in data
        assert "available_providers" in data


@pytest.mark.asyncio
async def test_repositories_list():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/repositories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
