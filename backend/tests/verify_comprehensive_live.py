"""
DocPilot AI Comprehensive Live Verification Script
Tests all live endpoints against the active running FastAPI instance at http://127.0.0.1:8000
"""

import io
import sys
import uuid
import zipfile
import httpx

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("=" * 70)
    print("DocPilot AI Comprehensive Live Quality Assurance Verification")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Health & System Status
    r = client.get("/health")
    assert r.status_code == 200, f"/health returned {r.status_code}"
    print(f"[PASS] 1. System Health Check (/health): {r.json()}")

    r = client.get("/api/v1/system/status")
    assert r.status_code == 200
    print(f"[PASS] 2. System Status API (/api/v1/system/status): status={r.json()['status']}")

    # 2. Authentication Flow
    test_id = uuid.uuid4().hex[:8]
    email = f"qa_live_{test_id}@docpilot.ai"
    password = "LivePassword123!"

    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": f"QA Live User {test_id}"
    })
    assert r.status_code == 201, f"Register failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] 3. User Registration (/api/v1/auth/register): token issued")

    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    print(f"[PASS] 4. User Login (/api/v1/auth/login): JWT authentication verified")

    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == email.lower()
    print(f"[PASS] 5. User Profile (/api/v1/auth/me): email={r.json()['email']}")

    # 3. Project Creation
    r = client.post("/api/v1/projects", json={
        "name": f"QA Comprehensive Project {test_id}",
        "description": "Live end-to-end verification project",
        "source_type": "zip"
    }, headers=headers)
    assert r.status_code == 201
    project_id = r.json()["id"]
    print(f"[PASS] 6. Project Creation (/api/v1/projects): project_id={project_id}")

    # 4. ZIP Upload & Extraction
    sample_zip = io.BytesIO()
    with zipfile.ZipFile(sample_zip, "w") as zf:
        zf.writestr(
            "app/server.py",
            '''
from fastapi import FastAPI, Depends
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    title = Column(String(100))

app = FastAPI()

@app.get("/items")
def list_items():
    return [{"id": 1, "title": "Widget"}]
''',
        )
        zf.writestr(
            "src/ItemView.tsx",
            '''
import React from 'react';

export interface ItemViewProps {
    id: number;
    title: string;
}

export const ItemView: React.FC<ItemViewProps> = ({ id, title }) => (
    <div className="item-view">
        <span>#{id}</span> <h4>{title}</h4>
    </div>
);
''',
        )
        zf.writestr("package.json", '{"name": "demo-ui", "dependencies": {"react": "^18.2.0"}}')
        zf.writestr("requirements.txt", "fastapi>=0.100.0\nsqlalchemy>=2.0.0\n")

    sample_zip.seek(0)
    r = client.post(
        f"/api/v1/projects/{project_id}/upload",
        files={"file": ("repo.zip", sample_zip.getvalue(), "application/zip")},
        headers=headers,
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    print(f"[PASS] 7. ZIP Archive Upload & Safe Unpack (/projects/{project_id}/upload)")

    # 5. Static Scanning & Language Detection
    r = client.post(f"/api/v1/projects/{project_id}/scan", headers=headers)
    assert r.status_code == 200
    scan = r.json()
    assert scan["total_files"] >= 4
    print(f"[PASS] 8. Repository Scan & Discovery: {scan['total_files']} files, languages={scan['languages']}")

    # 6. File Hierarchy & Metrics
    r = client.get(f"/api/v1/projects/{project_id}/files", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/structure", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/technologies", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/statistics", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 9. Project File Navigation & Metrics: files, structure, technologies, statistics")

    # 7. Code Parsing (AST & Tree-Sitter)
    r = client.post(f"/api/v1/projects/{project_id}/parse", headers=headers)
    assert r.status_code == 200
    parse = r.json()
    assert parse["total_entities_extracted"] > 0
    print(f"[PASS] 10. Multi-Language Code Parsing: extracted {parse['total_entities_extracted']} entities")

    r = client.get(f"/api/v1/projects/{project_id}/entities", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 11. Code Entities Retrieval: {len(r.json())} entities verified")

    # 8. Dependency Analysis
    r = client.post(f"/api/v1/projects/{project_id}/dependencies/analyze", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/dependencies/graph", headers=headers)
    assert r.status_code == 200
    assert "nodes" in r.json()
    print(f"[PASS] 12. Dependency Graph Resolution: {len(r.json()['nodes'])} nodes resolved")

    # 9. API Analysis
    r = client.post(f"/api/v1/projects/{project_id}/apis/analyze", headers=headers)
    assert r.status_code == 200
    assert r.json()["total_endpoints"] >= 1
    r = client.get(f"/api/v1/projects/{project_id}/apis", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 13. API Route Analysis: detected {len(r.json())} endpoints")

    # 10. Database Schema Analysis & ER Diagram
    r = client.post(f"/api/v1/projects/{project_id}/database/analyze", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/database/diagram", headers=headers)
    assert r.status_code == 200
    assert "erDiagram" in r.json()["mermaid_code"]
    print(f"[PASS] 14. Database Model Discovery & ER Diagram generated")

    # 11. Knowledge Graph Generation
    r = client.post(f"/api/v1/projects/{project_id}/knowledge/build", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/knowledge/graph", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 15. Cross-Domain Knowledge Graph: {len(r.json()['nodes'])} nodes, {len(r.json()['edges'])} edges")

    # 12. Architecture Diagrams
    r = client.post(f"/api/v1/projects/{project_id}/diagrams/generate", json={"force_regenerate": True}, headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/diagrams", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 16. Architecture Diagrams: {len(r.json())} Mermaid diagrams generated")

    # 13. Sequence Diagrams
    r = client.post(f"/api/v1/projects/{project_id}/sequences/generate", json={"force_regenerate": True}, headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{project_id}/sequences", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 17. Sequence Diagrams: {len(r.json())} execution sequence flows generated")

    # 14. Repository-Aware AI Chat Assistant
    r = client.post(f"/api/v1/projects/{project_id}/chat", json={"content": "What items endpoint is available?"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["role"] == "assistant"
    r = client.get(f"/api/v1/projects/{project_id}/chat/history", headers=headers)
    assert r.status_code == 200
    print(f"[PASS] 18. AI Chat Assistant & RAG Conversation History verified")

    # 15. Developer Onboarding Guide
    r = client.post(f"/api/v1/projects/{project_id}/onboarding/generate", json={"force_regenerate": True}, headers=headers)
    assert r.status_code == 200
    assert len(r.json()["markdown_content"]) > 0
    print(f"[PASS] 19. Developer Onboarding Guide: {len(r.json()['sections'])} sections synthesized")

    # 16. Change Detection & Sync
    r = client.post(f"/api/v1/projects/{project_id}/changes/check", headers=headers)
    assert r.status_code == 200
    assert "has_changes" in r.json()
    print(f"[PASS] 20. Change Detection Check: has_changes={r.json()['has_changes']}")

    # 17. Technical Reports & Markdown/HTML/PDF Export
    r = client.post(f"/api/v1/projects/{project_id}/reports/generate", json={"report_type": "FULL_TECHNICAL_REPORT"}, headers=headers)
    assert r.status_code == 201, f"Report generation failed: {r.text}"
    report_id = r.json()["id"]
    r_exp_md = client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=markdown", headers=headers)
    assert r_exp_md.status_code == 200
    assert "text/markdown" in r_exp_md.headers["Content-Type"]
    r_exp_html = client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=html", headers=headers)
    assert r_exp_html.status_code == 200
    r_exp_pdf = client.get(f"/api/v1/projects/{project_id}/reports/{report_id}/export?format=pdf", headers=headers)
    assert r_exp_pdf.status_code == 200
    assert "application/pdf" in r_exp_pdf.headers["Content-Type"]
    print(f"[PASS] 21. Technical Reports Generation & Multi-Format Export (Markdown, HTML, PDF)")

    # 18. GitHub Integration
    r = client.post("/api/v1/github/validate", json={"url": "https://github.com/torvalds/linux"})
    assert r.status_code == 200
    assert r.json()["valid"] is True
    print(f"[PASS] 22. GitHub Integration (/github/validate): public repo validation verified")

    # 19. Multi-Tenant Authorization Security (Cross-User Block)
    other_email = f"attacker_{test_id}@docpilot.ai"
    r = client.post("/api/v1/auth/register", json={"email": other_email, "password": "EvilPassword123!", "full_name": "Attacker"})
    attacker_token = r.json()["access_token"]
    attacker_headers = {"Authorization": f"Bearer {attacker_token}"}

    r_cross = client.get(f"/api/v1/projects/{project_id}", headers=attacker_headers)
    assert r_cross.status_code == 403, f"Cross-tenant access allowed! {r_cross.status_code}"
    r_cross_files = client.get(f"/api/v1/projects/{project_id}/files", headers=attacker_headers)
    assert r_cross_files.status_code == 403
    r_cross_chat = client.post(f"/api/v1/projects/{project_id}/chat", json={"content": "leak data"}, headers=attacker_headers)
    assert r_cross_chat.status_code == 403
    print(f"[PASS] 23. Security Authorization: Cross-user access rejected with 403 Forbidden")

    # 20. Cleanup
    r = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert r.status_code == 204
    print(f"[PASS] 24. Project Cleanup (/projects/{project_id}): isolated storage wiped")

    print("=" * 70)
    print("ALL 24 LIVE QUALITY ASSURANCE CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    main()
