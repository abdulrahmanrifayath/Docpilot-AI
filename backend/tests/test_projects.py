import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient


def create_sample_zip(files: dict) -> io.BytesIO:
    """Helper to create an in-memory ZIP archive with specified files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath, content in files.items():
            zf.writestr(filepath, content)
    buffer.seek(0)
    return buffer


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
    assert created_data["status"] == "CREATED"
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
    
    # Delete project
    delete_res = client.delete(f"/api/v1/projects/{project_id}")
    assert delete_res.status_code == 204


def test_upload_python_zip_and_file_tree(client: TestClient):
    # 1. Create project
    create_res = client.post("/api/v1/projects", json={
        "name": "Python Sample App",
        "description": "Sample Python project",
        "source_type": "zip"
    })
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # 2. Check files before upload -> should return 422
    files_before = client.get(f"/api/v1/projects/{project_id}/files")
    assert files_before.status_code == 422

    # 3. Create zip with python files and ignored directories
    zip_buffer = create_sample_zip({
        "app/main.py": "print('Hello DocPilot')",
        "app/models/user.py": "class User: pass",
        "app/__pycache__/cache.pyc": "binary cache",
        "node_modules/pkg/index.js": "ignored package",
        "README.md": "# Python Sample App",
    })

    # 4. Upload zip
    upload_res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("project.zip", zip_buffer, "application/zip")},
    )
    assert upload_res.status_code == 200
    project_data = upload_res.json()
    assert project_data["status"] == "READY"

    # 5. Get file tree
    files_res = client.get(f"/api/v1/projects/{project_id}/files")
    assert files_res.status_code == 200
    tree_data = files_res.json()

    assert tree_data["total_files"] >= 3
    assert "Python" in tree_data["language_counts"]
    assert "Markdown" in tree_data["language_counts"]
    
    # Ensure ignored folders (__pycache__, node_modules) were filtered
    all_paths = [f["path"] for f in tree_data["files"]]
    assert not any("__pycache__" in p for p in all_paths)
    assert not any("node_modules" in p for p in all_paths)

    # 6. Delete project and verify cleanup
    del_res = client.delete(f"/api/v1/projects/{project_id}")
    assert del_res.status_code == 204


def test_upload_typescript_zip(client: TestClient):
    create_res = client.post("/api/v1/projects", json={
        "name": "TypeScript React App",
        "source_type": "zip"
    })
    project_id = create_res.json()["id"]

    zip_buffer = create_sample_zip({
        "src/App.tsx": "export const App = () => <div>Hello</div>;",
        "src/index.ts": "import { App } from './App';",
        "package.json": "{\"name\": \"react-app\"}",
    })

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("ts_app.zip", zip_buffer, "application/zip")},
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["status"] == "READY"

    files_res = client.get(f"/api/v1/projects/{project_id}/files")
    assert files_res.status_code == 200
    tree_data = files_res.json()
    assert tree_data["total_files"] == 3
    assert tree_data["language_counts"]["TypeScript"] == 2
    assert tree_data["language_counts"]["JSON"] == 1


def test_invalid_zip_upload(client: TestClient):
    create_res = client.post("/api/v1/projects", json={"name": "Bad Zip App", "source_type": "zip"})
    project_id = create_res.json()["id"]

    # Upload corrupt non-zip file
    corrupt_buffer = io.BytesIO(b"This is not a zip file content.")
    upload_res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("not_a_zip.zip", corrupt_buffer, "application/zip")},
    )
    assert upload_res.status_code == 422

    # Check project status is FAILED
    get_res = client.get(f"/api/v1/projects/{project_id}")
    assert get_res.json()["status"] == "FAILED"


def test_zip_slip_prevention(client: TestClient):
    create_res = client.post("/api/v1/projects", json={"name": "Zip Slip Test", "source_type": "zip"})
    project_id = create_res.json()["id"]

    # Create zip with illegal path traversal
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("../../evil.txt", "Malicious content")
    zip_buffer.seek(0)

    upload_res = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("slip.zip", zip_buffer, "application/zip")},
    )
    assert upload_res.status_code == 422
    assert "traversal" in upload_res.json()["error"]["message"].lower() or "zip-slip" in upload_res.json()["error"]["message"].lower()


def test_invalid_github_url(client: TestClient):
    create_res = client.post("/api/v1/projects", json={"name": "Invalid Git App", "source_type": "github"})
    project_id = create_res.json()["id"]

    clone_res = client.post(
        f"/api/v1/projects/{project_id}/clone",
        json={"url": "https://not-github.com/user/repo"},
    )
    assert clone_res.status_code == 422
    assert "Invalid GitHub URL" in clone_res.json()["error"]["message"]


def test_clone_valid_github_repo(client: TestClient):
    create_res = client.post("/api/v1/projects", json={
        "name": "Octocat Hello World",
        "source_type": "github"
    })
    project_id = create_res.json()["id"]

    # Use small public repo: https://github.com/octocat/Hello-World
    clone_res = client.post(
        f"/api/v1/projects/{project_id}/clone",
        json={"url": "https://github.com/octocat/Hello-World"},
    )
    assert clone_res.status_code == 200
    assert clone_res.json()["status"] == "READY"

    files_res = client.get(f"/api/v1/projects/{project_id}/files")
    assert files_res.status_code == 200
    assert files_res.json()["total_files"] >= 1

    # Cleanup
    client.delete(f"/api/v1/projects/{project_id}")
