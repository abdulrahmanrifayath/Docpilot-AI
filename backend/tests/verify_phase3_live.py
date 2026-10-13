import io
import zipfile
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
client = httpx.Client(timeout=30.0)

print("=================================================================")
print("=== VERIFYING PHASE 3 LIVE REST API & SCANNER TECHNOLOGY ACCURACY")
print("=================================================================")

# -------------------------------------------------------------
# 1. Python FastAPI Project Test
# -------------------------------------------------------------
print("\n[TEST 1] Testing Python FastAPI Project...")
p1 = client.post(f"{BASE_URL}/projects", json={"name": "Live-FastAPI-Project", "source_type": "zip"}).json()
p1_id = p1["id"]

buf1 = io.BytesIO()
with zipfile.ZipFile(buf1, "w") as zf:
    zf.writestr("app/main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'status': 'ok'}\n")
    zf.writestr("requirements.txt", "fastapi>=0.100.0\nuvicorn>=0.20.0\npydantic>=2.0.0\n")
    zf.writestr("Dockerfile", "FROM python:3.11\nWORKDIR /app\nCMD [\"uvicorn\", \"app.main:app\"]\n")
    zf.writestr(".env.example", "PORT=8000\nENV=production\n")
    zf.writestr(".github/workflows/deploy.yml", "name: Deploy\non: push\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n")
    zf.writestr("node_modules/ignored.js", "console.log('should be ignored');\n")
buf1.seek(0)

upload1 = client.post(f"{BASE_URL}/projects/{p1_id}/upload", files={"file": ("fastapi.zip", buf1.getvalue(), "application/zip")})
assert upload1.status_code == 200, f"Upload failed: {upload1.text}"

# Test POST /scan
scan1 = client.post(f"{BASE_URL}/projects/{p1_id}/scan")
assert scan1.status_code == 200
s1_data = scan1.json()
print("Scan Status:", s1_data["status"])
print("Languages:", s1_data["languages"])
print("Frameworks:", s1_data["frameworks"])
print("Infrastructure:", s1_data["infrastructure"])

assert "Python" in s1_data["languages"], "Python was not detected!"
assert s1_data["languages"]["Python"]["files"] == 1
assert "FastAPI" in s1_data["frameworks"], "FastAPI was not detected!"
assert "Dockerfile" in s1_data["infrastructure"], "Dockerfile was not detected!"
assert "GitHub Actions" in s1_data["infrastructure"], "GitHub Actions was not detected!"
assert "environment files" in s1_data["infrastructure"], "Environment files was not detected!"

# Test GET /technologies
tech1 = client.get(f"{BASE_URL}/projects/{p1_id}/technologies").json()
assert "FastAPI" in tech1["frameworks"]
assert "Python" in tech1["languages"]

# Test GET /statistics
stats1 = client.get(f"{BASE_URL}/projects/{p1_id}/statistics").json()
assert stats1["total_files"] == 5
assert stats1["total_lines"] > 0

# Test GET /structure
struct1 = client.get(f"{BASE_URL}/projects/{p1_id}/structure").json()
assert struct1["total_files"] == 5
assert struct1["tree"]["type"] == "directory"
print("[TEST 1 PASSED] Python FastAPI detected with 100% accuracy!\n")

# -------------------------------------------------------------
# 2. React Project Test
# -------------------------------------------------------------
print("[TEST 2] Testing React (TypeScript + CSS + HTML) Project...")
p2 = client.post(f"{BASE_URL}/projects", json={"name": "Live-React-Project", "source_type": "zip"}).json()
p2_id = p2["id"]

buf2 = io.BytesIO()
with zipfile.ZipFile(buf2, "w") as zf:
    zf.writestr("package.json", '{"name": "react-web", "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"}}\n')
    zf.writestr("src/App.tsx", 'import React from "react";\n\nexport const App = () => <h1>DocPilot</h1>;\n')
    zf.writestr("src/index.css", "body { margin: 0; background: #000; }\n")
    zf.writestr("index.html", "<!DOCTYPE html><html><body><div id='root'></div></body></html>\n")
    zf.writestr("README.md", "# React Project\nDocumentation in Markdown\n")
buf2.seek(0)

upload2 = client.post(f"{BASE_URL}/projects/{p2_id}/upload", files={"file": ("react.zip", buf2.getvalue(), "application/zip")})
assert upload2.status_code == 200

scan2 = client.post(f"{BASE_URL}/projects/{p2_id}/scan").json()
print("Languages:", scan2["languages"])
print("Frameworks:", scan2["frameworks"])

assert "TypeScript" in scan2["languages"]
assert "HTML" in scan2["languages"]
assert "CSS" in scan2["languages"]
assert "JSON" in scan2["languages"]
assert "Markdown" in scan2["languages"]
assert "React" in scan2["frameworks"]
assert "Node.js" in scan2["frameworks"]
print("[TEST 2 PASSED] React & TypeScript detected with 100% accuracy!\n")

# -------------------------------------------------------------
# 3. Full-Stack Project Test
# -------------------------------------------------------------
print("[TEST 3] Testing Full-Stack Project (FastAPI + React + Compose + K8s + Terraform)...")
p3 = client.post(f"{BASE_URL}/projects", json={"name": "Live-Fullstack-Project", "source_type": "zip"}).json()
p3_id = p3["id"]

buf3 = io.BytesIO()
with zipfile.ZipFile(buf3, "w") as zf:
    # Backend
    zf.writestr("backend/server.py", "import fastapi\napp = fastapi.FastAPI()\n")
    zf.writestr("backend/requirements.txt", "fastapi\nsqlalchemy\n")
    zf.writestr("backend/Dockerfile", "FROM python:3.11\n")
    # Frontend
    zf.writestr("frontend/package.json", '{"name": "frontend-ui", "dependencies": {"react": "^18.0.0", "next": "13.0.0"}}\n')
    zf.writestr("frontend/src/index.jsx", 'import React from "react";\n')
    # Infrastructure
    zf.writestr("docker-compose.yml", "version: '3.8'\nservices:\n  app:\n    build: .\n")
    zf.writestr(".env", "DB_PASS=secret\n")
    zf.writestr("k8s/deployment.yaml", "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: fullstack\n")
    zf.writestr("terraform/main.tf", 'resource "aws_s3_bucket" "b" {}\n')
buf3.seek(0)

upload3 = client.post(f"{BASE_URL}/projects/{p3_id}/upload", files={"file": ("fullstack.zip", buf3.getvalue(), "application/zip")})
assert upload3.status_code == 200

scan3 = client.post(f"{BASE_URL}/projects/{p3_id}/scan").json()
print("Languages:", scan3["languages"])
print("Frameworks:", scan3["frameworks"])
print("Infrastructure:", scan3["infrastructure"])

assert "Python" in scan3["languages"]
assert "JavaScript" in scan3["languages"]
assert "FastAPI" in scan3["frameworks"]
assert "React" in scan3["frameworks"]
assert "Next.js" in scan3["frameworks"]
assert "Node.js" in scan3["frameworks"]

assert "Dockerfile" in scan3["infrastructure"]
assert "docker-compose.yml" in scan3["infrastructure"]
assert "Kubernetes manifests" in scan3["infrastructure"]
assert "Terraform" in scan3["infrastructure"]
assert "environment files" in scan3["infrastructure"]

print("[TEST 3 PASSED] Full-Stack Project detected with 100% accuracy!\n")

# Clean up test projects
for pid in [p1_id, p2_id, p3_id]:
    client.delete(f"{BASE_URL}/projects/{pid}")

print("=================================================================")
print("=== ALL 3 LIVE VERIFICATION SCENARIOS PASSED WITH ZERO ERRORS ===")
print("=================================================================")
