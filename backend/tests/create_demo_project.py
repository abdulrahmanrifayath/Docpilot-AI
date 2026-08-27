import io
import zipfile
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000")
p = client.post(
    "/api/v1/projects",
    json={
        "name": "DocPilot AI Core",
        "description": "Intelligent Software Documentation and Repo Knowledge Platform",
        "source_type": "zip",
    },
).json()

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("backend/requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\nsqlalchemy>=2.0.0\npydantic>=2.6.0\n")
    zf.writestr("backend/app/main.py", "from fastapi import FastAPI\napp = FastAPI(title='DocPilot API')\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n")
    zf.writestr("backend/app/services/scanner.py", "class Scanner:\n    def scan(self):\n        pass\n")
    zf.writestr("frontend/package.json", '{\n  "name": "docpilot-frontend",\n  "dependencies": {\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0",\n    "next": "^14.0.0"\n  }\n}\n')
    zf.writestr("frontend/next.config.js", "module.exports = {};\n")
    zf.writestr("frontend/pages/index.tsx", 'import React from "react";\nexport default function Home() {\n  return <div>DocPilot AI</div>;\n}\n')
    zf.writestr("docker-compose.yml", "version: '3.8'\nservices:\n  backend:\n    build: ./backend\n  frontend:\n    build: ./frontend\n")
    zf.writestr(".github/workflows/ci.yml", "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")
    zf.writestr("infra/main.tf", "terraform {\n  required_version = '>= 1.0'\n}\n")
    zf.writestr("k8s/deployment.yaml", "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: docpilot\n")
    zf.writestr(".env.example", "PORT=8000\nDATABASE_URL=sqlite:///./docpilot.db\n")
    zf.writestr("README.md", "# DocPilot AI\n\nAutomatic documentation platform.\n")

buf.seek(0)
client.post(f"/api/v1/projects/{p['id']}/upload", files={"file": ("repo.zip", buf, "application/zip")})
client.post(f"/api/v1/projects/{p['id']}/scan")
print(f"Created and scanned demo project with ID: {p['id']}")
