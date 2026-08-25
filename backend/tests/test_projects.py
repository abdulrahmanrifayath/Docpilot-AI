from fastapi.testclient import TestClient


def test_create_and_get_project(client: TestClient):
    payload = {
        "name": "FastAPI Repo",
        "description": "A high-performance modern web framework",
        "source_type": "github",
        "source_url": "https://github.com/fastapi/fastapi",
    }
    
    # Create project
    create_res = client.post("/api/v1/projects", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "FastAPI Repo"
    assert created_data["status"] == "pending"
    assert "id" in created_data
    project_id = created_data["id"]
    
    # Get by ID
    get_res = client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id
    
    # List projects
    list_res = client.get("/api/v1/projects")
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) >= 1
    assert any(p["id"] == project_id for p in projects)
    
    # Update project
    update_res = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "FastAPI Web Framework", "status": "ready"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "FastAPI Web Framework"
    assert update_res.json()["status"] == "ready"
    
    # Delete project
    delete_res = client.delete(f"/api/v1/projects/{project_id}")
    assert delete_res.status_code == 204
    
    # Ensure deleted
    not_found_res = client.get(f"/api/v1/projects/{project_id}")
    assert not_found_res.status_code == 404
