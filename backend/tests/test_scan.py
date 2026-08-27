import io
import zipfile
import pytest
from fastapi.testclient import TestClient


def make_test_zip(files_dict: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(path, content)
            else:
                zf.writestr(path, content)
    buf.seek(0)
    return buf


def test_scan_fastapi_python_project(client: TestClient):
    # Create project
    proj = client.post("/api/v1/projects", json={"name": "FastAPI Scan Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "requirements.txt": "fastapi==0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\n",
        "app/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI(title='Test API')\n\n"
            "@app.get('/items')\n"
            "def read_items():\n"
            "    return [{'id': 1, 'name': 'item'}]\n"
        ),
        "app/models.py": "class Item:\n    id: int\n    name: str\n",
        "Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD ['uvicorn', 'app.main:app']\n",
        "README.md": "# FastAPI Microservice\n\nProduction API.\n",
    })

    # Upload
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/upload",
        files={"file": ("fastapi_app.zip", zip_buf, "application/zip")},
    )
    assert upload_res.status_code == 200

    # 1. Trigger /scan
    scan_res = client.post(f"/api/v1/projects/{proj_id}/scan")
    assert scan_res.status_code == 200
    scan_data = scan_res.json()

    assert scan_data["status"] == "ANALYZED"
    assert scan_data["summary"]["total_files"] == 5
    assert "Python" in scan_data["summary"]["languages"]
    assert scan_data["summary"]["languages"]["Python"]["files"] == 2
    assert scan_data["summary"]["languages"]["Python"]["lines"] > 5

    # 2. Check /technologies
    tech_res = client.get(f"/api/v1/projects/{proj_id}/technologies")
    assert tech_res.status_code == 200
    tech_data = tech_res.json()

    framework_names = [f["name"] for f in tech_data["frameworks"]]
    assert "FastAPI" in framework_names

    infra_names = [i["name"] for i in tech_data["infrastructure"]]
    assert "Docker" in infra_names

    # 3. Check /structure
    struct_res = client.get(f"/api/v1/projects/{proj_id}/structure")
    assert struct_res.status_code == 200
    struct_data = struct_res.json()
    assert struct_data["total_files"] == 5

    # 4. Check /statistics
    stats_res = client.get(f"/api/v1/projects/{proj_id}/statistics")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["total_lines"] > 10
    assert "source_code" in stats_data["categories"]

    # Cleanup
    client.delete(f"/api/v1/projects/{proj_id}")


def test_scan_react_typescript_project(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "React TS Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "package.json": '{\n  "name": "react-frontend",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  }\n}\n',
        "src/App.tsx": (
            "import React, { useState } from 'react';\n"
            "export const App = () => {\n"
            "  const [count, setCount] = useState(0);\n"
            "  return <div>{count}</div>;\n"
            "};\n"
        ),
        "src/index.ts": "import { App } from './App';\nconsole.log(App);\n",
        "src/styles.css": "body { margin: 0; padding: 0; background: #000; }\n",
        ".env.local": "VITE_API_URL=http://localhost:8000\n",
    })

    client.post(
        f"/api/v1/projects/{proj_id}/upload",
        files={"file": ("react_app.zip", zip_buf, "application/zip")},
    )

    scan_res = client.post(f"/api/v1/projects/{proj_id}/scan")
    assert scan_res.status_code == 200
    scan_data = scan_res.json()

    # Verify frameworks
    frameworks = {f["name"]: f for f in scan_data["technologies"]["frameworks"]}
    assert "React" in frameworks
    assert frameworks["React"]["confidence"] == "HIGH"

    # Verify infrastructure
    infra = {i["name"]: i for i in scan_data["technologies"]["infrastructure"]}
    assert "Environment Config" in infra

    # Verify languages
    languages = scan_data["summary"]["languages"]
    assert "TypeScript" in languages
    assert "CSS" in languages
    assert "JSON" in languages

    client.delete(f"/api/v1/projects/{proj_id}")


def test_scan_fullstack_complex_project(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Fullstack Complex Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        # Backend
        "backend/requirements.txt": "fastapi>=0.100.0\nsqlalchemy>=2.0\n",
        "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        # Frontend
        "frontend/package.json": '{\n  "name": "web",\n  "dependencies": {\n    "next": "^14.0.0",\n    "react": "^18.2.0"\n  }\n}\n',
        "frontend/next.config.js": "module.exports = {};\n",
        "frontend/pages/index.tsx": "export default function Home() { return <h1>DocPilot</h1>; }\n",
        # Infrastructure
        "docker-compose.yml": "version: '3.8'\nservices:\n  backend:\n    build: ./backend\n  frontend:\n    build: ./frontend\n",
        ".github/workflows/ci.yml": "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n",
        "infra/main.tf": "provider 'aws' { region = 'us-east-1' }\n",
        "k8s/deployment.yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: docpilot\n",
        ".env.example": "DATABASE_URL=sqlite:///./test.db\n",
    })

    client.post(
        f"/api/v1/projects/{proj_id}/upload",
        files={"file": ("fullstack.zip", zip_buf, "application/zip")},
    )

    tech_res = client.get(f"/api/v1/projects/{proj_id}/technologies")
    assert tech_res.status_code == 200
    tech = tech_res.json()

    framework_names = {f["name"] for f in tech["frameworks"]}
    assert "FastAPI" in framework_names
    assert "React" in framework_names
    assert "Next.js" in framework_names

    infra_names = {i["name"] for i in tech["infrastructure"]}
    assert "Docker Compose" in infra_names
    assert "GitHub Actions" in infra_names
    assert "Kubernetes" in infra_names
    assert "Terraform" in infra_names
    assert "Environment Config" in infra_names

    client.delete(f"/api/v1/projects/{proj_id}")


def test_binary_file_safety(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Binary Test", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "data.bin": b"\x00\x01\x02\x03\x00\xff",
        "image.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        "script.py": "print('hello')\n",
    })

    client.post(
        f"/api/v1/projects/{proj_id}/upload",
        files={"file": ("binary_test.zip", zip_buf, "application/zip")},
    )

    struct_res = client.get(f"/api/v1/projects/{proj_id}/structure")
    assert struct_res.status_code == 200
    files_by_name = {f["name"]: f for f in struct_res.json()["structure"]}

    assert files_by_name["data.bin"]["lines"] == 0
    assert files_by_name["data.bin"]["category"] == "asset"
    assert files_by_name["image.png"]["lines"] == 0
    assert files_by_name["image.png"]["category"] == "asset"
    assert files_by_name["script.py"]["lines"] == 1
    assert files_by_name["script.py"]["category"] == "source_code"

    client.delete(f"/api/v1/projects/{proj_id}")
