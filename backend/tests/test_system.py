from fastapi.testclient import TestClient


def test_system_status(client: TestClient):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "environment" in data
    assert "version" in data
    assert "timestamp" in data
    
    # Check Database
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert "engine" in data["database"]
    
    # Check AI Provider status
    assert "ai_provider" in data
    assert "configured" in data["ai_provider"]
    assert "model" in data["ai_provider"]
    # Ensure no secret keys leaked
    assert "api_key" not in data["ai_provider"]
    
    # Check Vector DB
    assert "vector_db" in data
    assert data["vector_db"]["status"] in ["ready", "uninitialized"]
