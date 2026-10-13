import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_project_crud_and_zip_uploads():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Project
        create_resp = await ac.post(
            "/api/v1/projects",
            json={
                "name": "Python Microservice",
                "description": "Test Python service for Phase 2",
                "source_type": "zip",
            },
        )
        assert create_resp.status_code == 201
        project_data = create_resp.json()
        project_id = project_data["id"]
        assert project_data["name"] == "Python Microservice"
        assert project_data["status"] == "CREATED"

        # 2. Get Project
        get_resp = await ac.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == project_id

        # 3. List Projects
        list_resp = await ac.get("/api/v1/projects")
        assert list_resp.status_code == 200
        projects = list_resp.json()
        assert any(p["id"] == project_id for p in projects)

        # 4. Upload valid Python project ZIP
        py_zip_buffer = io.BytesIO()
        with zipfile.ZipFile(py_zip_buffer, "w") as zf:
            zf.writestr("app/main.py", "print('hello world')\n")
            zf.writestr("app/utils.py", "def add(a, b): return a + b\n")
            zf.writestr("requirements.txt", "fastapi\n")
            # Ignored folder should be skipped
            zf.writestr(".venv/pyvenv.cfg", "home = /usr/bin\n")
            zf.writestr("node_modules/dummy.js", "console.log('skip');\n")

        py_zip_buffer.seek(0)
        upload_resp = await ac.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("python_project.zip", py_zip_buffer.getvalue(), "application/zip")},
        )
        assert upload_resp.status_code == 200
        uploaded_data = upload_resp.json()
        assert uploaded_data["status"] == "READY"
        assert uploaded_data["source_type"] == "zip"

        # 5. List Files
        files_resp = await ac.get(f"/api/v1/projects/{project_id}/files")
        assert files_resp.status_code == 200
        files_data = files_resp.json()
        assert files_data["total_files"] >= 2
        # Ensure node_modules and .venv were not included
        all_paths_str = str(files_data["files"])
        assert "node_modules" not in all_paths_str
        assert ".venv" not in all_paths_str

        # 6. Delete Project
        del_resp = await ac.delete(f"/api/v1/projects/{project_id}")
        assert del_resp.status_code == 204

        # Verify project is gone
        verify_del = await ac.get(f"/api/v1/projects/{project_id}")
        assert verify_del.status_code == 404


@pytest.mark.asyncio
async def test_javascript_project_zip_upload():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create JS Project
        create_resp = await ac.post(
            "/api/v1/projects",
            json={"name": "React Web App", "source_type": "zip"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # Upload TS project ZIP
        ts_zip_buffer = io.BytesIO()
        with zipfile.ZipFile(ts_zip_buffer, "w") as zf:
            zf.writestr("src/App.tsx", "export const App = () => <div>Hello</div>;\n")
            zf.writestr("package.json", '{"name": "test-app", "version": "1.0.0"}\n')
            zf.writestr("dist/bundle.js", "// compiled code\n")

        ts_zip_buffer.seek(0)
        upload_resp = await ac.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("react_app.zip", ts_zip_buffer.getvalue(), "application/zip")},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["status"] == "READY"

        files_resp = await ac.get(f"/api/v1/projects/{project_id}/files")
        assert files_resp.status_code == 200
        assert "dist" not in str(files_resp.json()["files"])

        # Clean up
        await ac.delete(f"/api/v1/projects/{project_id}")


@pytest.mark.asyncio
async def test_invalid_zip_upload():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post("/api/v1/projects", json={"name": "Invalid Zip Test"})
        project_id = create_resp.json()["id"]

        # Upload plain text file instead of zip
        bad_file = b"This is just plain text, not a zip file."
        upload_resp = await ac.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("test.zip", bad_file, "application/zip")},
        )
        assert upload_resp.status_code == 400
        data = upload_resp.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

        # Non .zip extension
        upload_resp2 = await ac.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("test.tar.gz", b"PK123", "application/gzip")},
        )
        assert upload_resp2.status_code == 400

        await ac.delete(f"/api/v1/projects/{project_id}")


@pytest.mark.asyncio
async def test_zip_slip_security_prevention():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post("/api/v1/projects", json={"name": "Zip Slip Security Test"})
        project_id = create_resp.json()["id"]

        # Craft malicious zip with directory traversal entry
        malicious_zip = io.BytesIO()
        with zipfile.ZipFile(malicious_zip, "w") as zf:
            zf.writestr("../../evil.sh", "echo 'pwned'")

        malicious_zip.seek(0)
        upload_resp = await ac.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("malicious.zip", malicious_zip.getvalue(), "application/zip")},
        )
        assert upload_resp.status_code == 400
        data = upload_resp.json()
        assert data["error"]["code"] == "SECURITY_VIOLATION"
        assert "traversal" in data["error"]["message"].lower()

        await ac.delete(f"/api/v1/projects/{project_id}")


@pytest.mark.asyncio
async def test_invalid_github_url():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post("/api/v1/projects", json={"name": "Invalid Git Test"})
        project_id = create_resp.json()["id"]

        # Invalid URL
        clone_resp = await ac.post(
            f"/api/v1/projects/{project_id}/clone",
            json={"source_url": "https://malicious-site.com/repo.git"},
        )
        assert clone_resp.status_code == 400
        data = clone_resp.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "Invalid GitHub repository URL" in data["error"]["message"]

        await ac.delete(f"/api/v1/projects/{project_id}")
