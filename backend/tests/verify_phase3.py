import io
import os
import zipfile
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


def make_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, c in files_dict.items():
            if isinstance(c, str):
                zf.writestr(p, c)
            else:
                zf.writestr(p, c)
    buf.seek(0)
    return buf


def run_phase3_live_tests():
    print("==================================================")
    print("PHASE 3 LIVE VERIFICATION: FILE DISCOVERY & TECH DETECTION")
    print("==================================================")

    # -------------------------------------------------------------
    # Test 1: Python FastAPI Project
    # -------------------------------------------------------------
    print("\n--- TEST 1: Python FastAPI Project Detection ---")
    p1 = client.post("/api/v1/projects", json={"name": "Live FastAPI Microservice", "source_type": "zip"}).json()
    p1_id = p1["id"]

    py_zip = make_zip({
        "requirements.txt": "fastapi>=0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\n",
        "app/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI(title='DocPilot Microservice')\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n"
        ),
        "app/api/router.py": "from fastapi import APIRouter\nrouter = APIRouter()\n",
        "app/models/user.py": "class User:\n    id: int\n    email: str\n",
        "Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD ['uvicorn', 'app.main:app']\n",
        "README.md": "# DocPilot Microservice\n\nFastAPI backend.\n",
    })

    up1 = client.post(f"/api/v1/projects/{p1_id}/upload", files={"file": ("fastapi.zip", py_zip, "application/zip")})
    assert up1.status_code == 200

    # 1. Trigger POST /scan
    scan1 = client.post(f"/api/v1/projects/{p1_id}/scan")
    assert scan1.status_code == 200, f"Scan failed: {scan1.text}"
    scan1_data = scan1.json()

    print(f"Status: {scan1_data['status']}")
    print(f"Total files: {scan1_data['summary']['total_files']}, LOC: {scan1_data['summary']['total_lines']}")
    print(f"Languages: {list(scan1_data['summary']['languages'].keys())}")
    print(f"Frameworks: {[f['name'] for f in scan1_data['technologies']['frameworks']]}")
    print(f"Infrastructure: {[i['name'] for i in scan1_data['technologies']['infrastructure']]}")

    assert scan1_data["summary"]["total_files"] == 6
    assert "Python" in scan1_data["summary"]["languages"]
    assert any(f["name"] == "FastAPI" for f in scan1_data["technologies"]["frameworks"])
    assert any(i["name"] == "Docker" for i in scan1_data["technologies"]["infrastructure"])

    # 2. Check GET /structure
    struct1 = client.get(f"/api/v1/projects/{p1_id}/structure")
    assert struct1.status_code == 200
    assert struct1.json()["total_files"] == 6

    # 3. Check GET /technologies
    tech1 = client.get(f"/api/v1/projects/{p1_id}/technologies")
    assert tech1.status_code == 200
    assert tech1.json()["primary_language"] == "Python"

    # 4. Check GET /statistics
    stats1 = client.get(f"/api/v1/projects/{p1_id}/statistics")
    assert stats1.status_code == 200
    assert "source_code" in stats1.json()["categories"]

    print("-> TEST 1 PASSED: Python FastAPI & Docker detected accurately!")

    # -------------------------------------------------------------
    # Test 2: React TypeScript Project
    # -------------------------------------------------------------
    print("\n--- TEST 2: React TypeScript Project Detection ---")
    p2 = client.post("/api/v1/projects", json={"name": "Live React TS Frontend", "source_type": "zip"}).json()
    p2_id = p2["id"]

    react_zip = make_zip({
        "package.json": '{\n  "name": "react-spa",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0"\n  },\n  "devDependencies": {\n    "@types/react": "^18.2.0"\n  }\n}\n',
        "src/App.tsx": "import React from 'react';\nexport const App = () => <h1>Hello React</h1>;\n",
        "src/index.tsx": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\n",
        "src/components/Header.tsx": "export const Header = () => <header>DocPilot</header>;\n",
        "src/theme.css": "body { background: #0b0f17; color: #fff; }\n",
        ".env.production": "VITE_API_URL=https://api.docpilot.ai\n",
    })

    client.post(f"/api/v1/projects/{p2_id}/upload", files={"file": ("react.zip", react_zip, "application/zip")})
    scan2 = client.post(f"/api/v1/projects/{p2_id}/scan").json()

    print(f"Total files: {scan2['summary']['total_files']}, LOC: {scan2['summary']['total_lines']}")
    print(f"Languages: {list(scan2['summary']['languages'].keys())}")
    print(f"Frameworks: {[f['name'] for f in scan2['technologies']['frameworks']]}")
    print(f"Infrastructure: {[i['name'] for i in scan2['technologies']['infrastructure']]}")

    assert any(f["name"] == "React" for f in scan2["technologies"]["frameworks"])
    assert "TypeScript" in scan2["summary"]["languages"]
    assert "CSS" in scan2["summary"]["languages"]
    assert any(i["name"] == "Environment Config" for i in scan2["technologies"]["infrastructure"])

    print("-> TEST 2 PASSED: React, TypeScript, and Environment Config detected!")

    # -------------------------------------------------------------
    # Test 3: Full-Stack Multi-Technology Project
    # -------------------------------------------------------------
    print("\n--- TEST 3: Full-Stack Project Detection ---")
    p3 = client.post("/api/v1/projects", json={"name": "Fullstack Cloud Native", "source_type": "zip"}).json()
    p3_id = p3["id"]

    fullstack_zip = make_zip({
        "backend/requirements.txt": "fastapi>=0.100.0\nsqlalchemy>=2.0\n",
        "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "frontend/package.json": '{\n  "name": "fullstack-app",\n  "dependencies": {\n    "next": "^14.0.0",\n    "react": "^18.2.0"\n  }\n}\n',
        "frontend/next.config.js": "module.exports = {};\n",
        "frontend/pages/index.tsx": "export default function Home() { return <div>Home</div>; }\n",
        "docker-compose.yml": "version: '3.8'\nservices:\n  backend:\n    build: ./backend\n  frontend:\n    build: ./frontend\n",
        ".github/workflows/ci.yml": "name: CI/CD\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
        "infra/main.tf": "terraform {\n  required_version = '>= 1.0'\n}\n",
        "k8s/deployment.yaml": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: fullstack\n",
        ".env.example": "PORT=8000\nDATABASE_URL=sqlite:///./app.db\n",
    })

    client.post(f"/api/v1/projects/{p3_id}/upload", files={"file": ("fullstack.zip", fullstack_zip, "application/zip")})
    scan3 = client.post(f"/api/v1/projects/{p3_id}/scan").json()

    frameworks3 = {f["name"] for f in scan3["technologies"]["frameworks"]}
    infra3 = {i["name"] for i in scan3["technologies"]["infrastructure"]}

    print(f"Detected Frameworks: {frameworks3}")
    print(f"Detected Infrastructure: {infra3}")

    assert "FastAPI" in frameworks3
    assert "React" in frameworks3
    assert "Next.js" in frameworks3
    assert "Docker Compose" in infra3
    assert "GitHub Actions" in infra3
    assert "Kubernetes" in infra3
    assert "Terraform" in infra3
    assert "Environment Config" in infra3

    print("-> TEST 3 PASSED: Full-stack frameworks and 5 infrastructure layers verified!")

    # -------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------
    client.delete(f"/api/v1/projects/{p1_id}")
    client.delete(f"/api/v1/projects/{p2_id}")
    client.delete(f"/api/v1/projects/{p3_id}")

    print("\n==================================================")
    print("ALL PHASE 3 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_phase3_live_tests()
