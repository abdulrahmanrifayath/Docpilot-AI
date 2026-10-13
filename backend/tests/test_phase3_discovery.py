import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.repository_scanner import repository_scanner


@pytest.mark.asyncio
async def test_python_fastapi_project_detection(tmp_path):
    """Scenario 1: Python FastAPI project scan and technology detection."""
    # Build a sample Python FastAPI project directory
    project_dir = tmp_path / "fastapi_app"
    project_dir.mkdir()

    (project_dir / "main.py").write_text(
        'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef index():\n    return {"hello": "world"}\n',
        encoding="utf-8",
    )
    (project_dir / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn>=0.23.0\npydantic>=2.0.0\n")
    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /app\nCMD [\"uvicorn\", \"main:app\"]\n")
    (project_dir / ".env.example").write_text("APP_ENV=production\nPORT=8000\n")

    wf_dir = project_dir / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "test.yml").write_text("name: Test\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

    # Run direct scanner
    scan = repository_scanner.scan_repository(project_dir)

    # Verify Language detection
    assert "Python" in scan["languages"]
    assert scan["languages"]["Python"]["files"] == 1
    assert scan["languages"]["Python"]["lines"] == 7
    assert "YAML" in scan["languages"]
    assert scan["languages"]["YAML"]["files"] == 1

    # Verify Framework detection
    assert "FastAPI" in scan["frameworks"]

    # Verify Infrastructure detection
    assert "Dockerfile" in scan["infrastructure"]
    assert "GitHub Actions" in scan["infrastructure"]
    assert "environment files" in scan["infrastructure"]

    # Verify Categories
    assert scan["categories"].get("code", 0) >= 1
    assert scan["categories"].get("infrastructure", 0) >= 2


@pytest.mark.asyncio
async def test_react_project_detection(tmp_path):
    """Scenario 2: React project scan and technology detection."""
    project_dir = tmp_path / "react_app"
    project_dir.mkdir()

    (project_dir / "package.json").write_text(
        '{\n  "name": "my-react-app",\n  "version": "1.0.0",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  },\n  "devDependencies": {\n    "typescript": "^5.0.0"\n  }\n}\n'
    )
    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "App.tsx").write_text(
        'import React from "react";\n\nexport const App: React.FC = () => {\n  return <div>Hello World</div>;\n};\n'
    )
    (src_dir / "styles.css").write_text("body {\n  margin: 0;\n  padding: 0;\n}\n")
    (project_dir / "index.html").write_text(
        '<!DOCTYPE html>\n<html>\n  <head><title>App</title></head>\n  <body><div id="root"></div></body>\n</html>\n'
    )

    scan = repository_scanner.scan_repository(project_dir)

    # Verify Languages
    assert "TypeScript" in scan["languages"]
    assert "HTML" in scan["languages"]
    assert "CSS" in scan["languages"]
    assert "JSON" in scan["languages"]

    # Verify Frameworks
    assert "React" in scan["frameworks"]
    assert "Node.js" in scan["frameworks"]


@pytest.mark.asyncio
async def test_fullstack_project_detection(tmp_path):
    """Scenario 3: Full-stack project with FastAPI, React, Node, Docker, Compose, K8s, Terraform."""
    fs_dir = tmp_path / "fullstack"
    fs_dir.mkdir()

    # Backend
    be_dir = fs_dir / "backend"
    be_dir.mkdir()
    (be_dir / "main.py").write_text("import fastapi\napp = fastapi.FastAPI()\n")
    (be_dir / "requirements.txt").write_text("fastapi\nsqlalchemy\n")
    (be_dir / "Dockerfile").write_text("FROM python:3.11\n")

    # Frontend
    fe_dir = fs_dir / "frontend"
    fe_dir.mkdir()
    (fe_dir / "package.json").write_text('{"name": "fe", "dependencies": {"react": "^18.0.0", "next": "13.0.0"}}\n')
    (fe_dir / "index.js").write_text('import React from "react";\n')

    # Infrastructure
    (fs_dir / "docker-compose.yml").write_text("version: '3.8'\nservices:\n  web:\n    build: .\n")
    (fs_dir / ".env").write_text("SECRET_KEY=dev\n")

    k8s_dir = fs_dir / "k8s"
    k8s_dir.mkdir()
    (k8s_dir / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\n")

    tf_dir = fs_dir / "terraform"
    tf_dir.mkdir()
    (tf_dir / "main.tf").write_text('provider "aws" {\n  region = "us-east-1"\n}\n')

    scan = repository_scanner.scan_repository(fs_dir)

    # Verify Languages
    assert "Python" in scan["languages"]
    assert "JavaScript" in scan["languages"]
    assert "JSON" in scan["languages"]
    assert "YAML" in scan["languages"]

    # Verify Frameworks
    assert "FastAPI" in scan["frameworks"]
    assert "React" in scan["frameworks"]
    assert "Next.js" in scan["frameworks"]
    assert "Node.js" in scan["frameworks"]

    # Verify Infrastructure
    assert "Dockerfile" in scan["infrastructure"]
    assert "docker-compose.yml" in scan["infrastructure"]
    assert "Kubernetes manifests" in scan["infrastructure"]
    assert "Terraform" in scan["infrastructure"]
    assert "environment files" in scan["infrastructure"]


@pytest.mark.asyncio
async def test_phase3_api_endpoints():
    """Verify POST /scan, GET /structure, GET /technologies, GET /statistics."""
    from app.database.session import init_db
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        # 1. Create a Project
        res = await client.post(
            "/api/v1/projects",
            json={"name": "Phase3-APITest", "source_type": "zip"},
        )
        assert res.status_code == 201
        project_id = res.json()["id"]

        # 2. Upload sample ZIP with Python + requirements
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("app/server.py", "from fastapi import FastAPI\napp = FastAPI()\n")
            zf.writestr("requirements.txt", "fastapi\n")
            zf.writestr("Dockerfile", "FROM python:3.11\n")
            zf.writestr(".env", "DATABASE_URL=sqlite:///./db.sqlite3\n")
        buf.seek(0)

        upload_res = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("test.zip", buf.getvalue(), "application/zip")},
        )
        assert upload_res.status_code == 200

        # 3. Test POST /api/v1/projects/{project_id}/scan
        scan_res = await client.post(f"/api/v1/projects/{project_id}/scan")
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["project_id"] == project_id
        assert scan_data["status"] == "ANALYZED"
        assert "Python" in scan_data["languages"]
        assert "FastAPI" in scan_data["frameworks"]
        assert "Dockerfile" in scan_data["infrastructure"]
        assert "environment files" in scan_data["infrastructure"]

        # 4. Test GET /api/v1/projects/{project_id}/structure
        struct_res = await client.get(f"/api/v1/projects/{project_id}/structure")
        assert struct_res.status_code == 200
        struct_data = struct_res.json()
        assert struct_data["total_files"] >= 3
        assert struct_data["tree"]["type"] == "directory"

        # 5. Test GET /api/v1/projects/{project_id}/technologies
        tech_res = await client.get(f"/api/v1/projects/{project_id}/technologies")
        assert tech_res.status_code == 200
        tech_data = tech_res.json()
        assert "FastAPI" in tech_data["frameworks"]
        assert "Python" in tech_data["languages"]
        assert "Dockerfile" in tech_data["infrastructure"]

        # 6. Test GET /api/v1/projects/{project_id}/statistics
        stats_res = await client.get(f"/api/v1/projects/{project_id}/statistics")
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert stats_data["total_files"] >= 3
        assert stats_data["total_lines"] > 0
        assert "Python" in stats_data["languages"]
        assert "FastAPI" in stats_data["frameworks"]

        # Clean up
        del_res = await client.delete(f"/api/v1/projects/{project_id}")
        assert del_res.status_code == 204
