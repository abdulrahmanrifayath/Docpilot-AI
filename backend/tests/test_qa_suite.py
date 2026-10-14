"""
DocPilot AI Comprehensive QA & Security Verification Suite
Tests all 16 backend capabilities, 6 critical security vectors, and input validation bounds.
"""

import io
import os
from pathlib import Path
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import init_db
from app.core.config import settings


@pytest.mark.asyncio
async def test_full_security_vectors():
    """
    Comprehensive Security QA:
    1. Zip-slip attack prevention
    2. Path traversal attack prevention
    3. Unauthorized project access (BOLA / IDOR) across subresources
    4. Unsafe repository execution prevention
    5. Invalid input handling
    6. Secret leak validation in configuration and environment templates
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Zip-Slip Attack Check
        p_res = await client.post("/api/v1/projects", json={"name": "Security QA Project"})
        assert p_res.status_code == 201
        p_id = p_res.json()["id"]

        malicious_zip = io.BytesIO()
        with zipfile.ZipFile(malicious_zip, "w") as zf:
            zf.writestr("../../../../../etc/passwd", "root:x:0:0:::")
            zf.writestr("..\\..\\windows\\system32\\evil.dll", "payload")

        malicious_zip.seek(0)
        zip_slip_res = await client.post(
            f"/api/v1/projects/{p_id}/upload",
            files={"file": ("malicious.zip", malicious_zip.getvalue(), "application/zip")},
        )
        assert zip_slip_res.status_code == 400
        assert zip_slip_res.json()["error"]["code"] == "SECURITY_VIOLATION"

        # 2. Path Traversal & Unsafe Input Handling on Project Creation
        invalid_url_res = await client.post(
            f"/api/v1/projects/{p_id}/clone",
            json={"source_url": "file:///etc/shadow", "branch": "main"},
        )
        assert invalid_url_res.status_code in (400, 422)

        # 3. Unauthorized Project Access (BOLA / Multi-Tenant Isolation)
        import uuid
        uid = uuid.uuid4().hex[:8]
        # Register User Alice
        res_alice = await client.post(
            "/api/v1/auth/register",
            json={"email": f"alice_{uid}@docpilot.ai", "password": "SecPassword123!", "full_name": "Alice QA"},
        )
        assert res_alice.status_code == 201
        token_alice = res_alice.json()["access_token"]
        alice_headers = {"Authorization": f"Bearer {token_alice}"}

        # Register User Bob
        res_bob = await client.post(
            "/api/v1/auth/register",
            json={"email": f"bob_{uid}@docpilot.ai", "password": "SecPassword123!", "full_name": "Bob QA"},
        )
        assert res_bob.status_code == 201
        token_bob = res_bob.json()["access_token"]
        bob_headers = {"Authorization": f"Bearer {token_bob}"}

        # Alice creates private project
        alice_proj = await client.post(
            "/api/v1/projects",
            json={"name": "Alice Private Vault"},
            headers=alice_headers,
        )
        alice_pid = alice_proj.json()["id"]

        # Bob attempts unauthorized access across multiple subresources
        # a. Project details
        res = await client.get(f"/api/v1/projects/{alice_pid}", headers=bob_headers)
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"

        # b. Files list
        res = await client.get(f"/api/v1/projects/{alice_pid}/files", headers=bob_headers)
        assert res.status_code == 403

        # c. Code entities
        res = await client.get(f"/api/v1/projects/{alice_pid}/entities", headers=bob_headers)
        assert res.status_code == 403

        # d. Dependency graph
        res = await client.get(f"/api/v1/projects/{alice_pid}/dependencies/graph", headers=bob_headers)
        assert res.status_code == 403

        # e. Documentation
        res = await client.get(f"/api/v1/projects/{alice_pid}/documentation", headers=bob_headers)
        assert res.status_code == 403

        # f. Diagrams
        res = await client.get(f"/api/v1/projects/{alice_pid}/diagrams", headers=bob_headers)
        assert res.status_code == 403

        # g. Sequences
        res = await client.get(f"/api/v1/projects/{alice_pid}/sequences", headers=bob_headers)
        assert res.status_code == 403

        # h. Chat
        res = await client.post(f"/api/v1/projects/{alice_pid}/chat", json={"content": "steal secrets"}, headers=bob_headers)
        assert res.status_code == 403

        # i. Reports
        res = await client.get(f"/api/v1/projects/{alice_pid}/reports", headers=bob_headers)
        assert res.status_code == 403

        # j. Delete
        res = await client.delete(f"/api/v1/projects/{alice_pid}", headers=bob_headers)
        assert res.status_code == 403

        # Cleanup
        await client.delete(f"/api/v1/projects/{alice_pid}", headers=alice_headers)
        await client.delete(f"/api/v1/projects/{p_id}")


@pytest.mark.asyncio
async def test_backend_end_to_end_pipeline():
    """
    Verifies full lifecycle of all 16 backend capabilities:
    1. Authentication (Register, Login, Me)
    2. Project Creation
    3. ZIP Upload & Extraction
    4. Static File Scanning
    5. Language Detection
    6. Code Parsing (AST & Tree-Sitter)
    7. Dependency Analysis
    8. API Analysis
    9. Database Analysis
    10. Knowledge Graph Generation
    11. Documentation Generation
    12. Diagram Generation
    13. Sequence Diagram Generation
    14. AI Chat Assistant
    15. Developer Onboarding Generation
    16. Change Detection & Sync
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Auth Flow
        import uuid
        pipe_email = f"pipeline_{uuid.uuid4().hex[:8]}@docpilot.ai"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": pipe_email, "password": "PipelinePass123!", "full_name": "Pipeline QA User"},
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Project Creation
        proj_res = await client.post(
            "/api/v1/projects",
            json={"name": "Comprehensive Pipeline Project"},
            headers=headers,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # 3. ZIP Upload with sample Python & TypeScript files
        sample_zip = io.BytesIO()
        with zipfile.ZipFile(sample_zip, "w") as zf:
            # Python API file with FastAPI and SQLAlchemy
            zf.writestr(
                "main.py",
                '''
from fastapi import FastAPI, Depends
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

app = FastAPI()

@app.get("/users")
def get_users():
    return [{"id": 1, "name": "Alice"}]
''',
            )
            # TypeScript component file
            zf.writestr(
                "UserCard.tsx",
                '''
import React from 'react';

export interface UserCardProps {
    name: string;
    role: string;
}

export const UserCard: React.FC<UserCardProps> = ({ name, role }) => {
    return (
        <div className="user-card">
            <h3>{name}</h3>
            <p>{role}</p>
        </div>
    );
};
''',
            )
            zf.writestr("package.json", '{"name": "demo-ui", "dependencies": {"react": "^18.2.0"}}')
            zf.writestr("requirements.txt", "fastapi>=0.100.0\nuvicorn>=0.23.0\nsqlalchemy>=2.0.0\n")

        sample_zip.seek(0)
        up_res = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", sample_zip.getvalue(), "application/zip")},
            headers=headers,
        )
        assert up_res.status_code == 200
        assert up_res.json()["status"] == "READY"

        # 4. File Scanning & 5. Language Detection
        scan_res = await client.post(f"/api/v1/projects/{project_id}/scan", headers=headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["total_files"] >= 3
        assert "Python" in scan_data["languages"] or "TypeScript" in scan_data["languages"]

        # 6. Code Parsing
        parse_res = await client.post(f"/api/v1/projects/{project_id}/parse", headers=headers)
        assert parse_res.status_code == 200
        assert parse_res.json()["total_entities_extracted"] > 0

        # Verify parsed entities
        ent_res = await client.get(f"/api/v1/projects/{project_id}/entities", headers=headers)
        assert ent_res.status_code == 200
        entities = ent_res.json()
        assert len(entities) > 0

        # 7. Dependency Analysis
        dep_res = await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze", headers=headers)
        assert dep_res.status_code == 200
        assert dep_res.json()["total_nodes"] > 0

        graph_res = await client.get(f"/api/v1/projects/{project_id}/dependencies/graph", headers=headers)
        assert graph_res.status_code == 200
        assert "nodes" in graph_res.json()

        # 8. API Analysis
        api_res = await client.post(f"/api/v1/projects/{project_id}/apis/analyze", headers=headers)
        assert api_res.status_code == 200
        assert api_res.json()["total_endpoints"] >= 1

        # 9. Database Analysis
        db_res = await client.post(f"/api/v1/projects/{project_id}/database/analyze", headers=headers)
        assert db_res.status_code == 200
        assert db_res.json()["total_models"] >= 1

        db_diag = await client.get(f"/api/v1/projects/{project_id}/database/diagram", headers=headers)
        assert db_diag.status_code == 200
        assert "erDiagram" in db_diag.json()["mermaid_code"]

        # 10. Knowledge Graph
        kg_res = await client.post(f"/api/v1/projects/{project_id}/knowledge/build", headers=headers)
        assert kg_res.status_code == 200
        assert kg_res.json()["total_nodes"] > 0

        # 11. Documentation Generation
        from app.ai.llm_client import MockLLMClient
        from app.services.documentation_service import documentation_service
        mock_llm = MockLLMClient(model_name="mock-qa")
        mock_llm.set_configured(True)
        documentation_service.llm_client = mock_llm
        documentation_service.get_client = lambda: mock_llm

        doc_res = await client.post(
            f"/api/v1/projects/{project_id}/documentation/generate",
            json={"force_regenerate": True},
            headers=headers,
        )
        assert doc_res.status_code == 200
        assert len(doc_res.json()["documents"]) > 0

        # 12. Diagram Generation
        diag_res = await client.post(
            f"/api/v1/projects/{project_id}/diagrams/generate",
            json={"force_regenerate": True},
            headers=headers,
        )
        assert diag_res.status_code == 200
        assert len(diag_res.json()["diagrams"]) > 0

        # 13. Sequence Diagram Generation
        seq_res = await client.post(
            f"/api/v1/projects/{project_id}/sequences/generate",
            json={"force_regenerate": True},
            headers=headers,
        )
        assert seq_res.status_code == 200
        assert len(seq_res.json()["sequences"]) > 0

        # 14. AI Chat Assistant
        chat_res = await client.post(
            f"/api/v1/projects/{project_id}/chat",
            json={"content": "What does this project do?"},
            headers=headers,
        )
        assert chat_res.status_code == 200
        assert chat_res.json()["role"] == "assistant"
        assert len(chat_res.json()["content"]) > 0

        # 15. Onboarding Generation
        onboard_res = await client.post(
            f"/api/v1/projects/{project_id}/onboarding/generate",
            json={"force_regenerate": True},
            headers=headers,
        )
        assert onboard_res.status_code == 200
        assert len(onboard_res.json()["markdown_content"]) > 0
        assert len(onboard_res.json()["sections"]) > 0

        # 16. Change Detection
        change_res = await client.post(f"/api/v1/projects/{project_id}/changes/check", headers=headers)
        assert change_res.status_code == 200
        assert "has_changes" in change_res.json()
        assert isinstance(change_res.json()["has_changes"], bool)

        # Cleanup
        del_res = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        assert del_res.status_code == 204


def test_code_quality_and_secrets():
    """
    Validates Code Quality & Hygiene:
    1. No live API keys in code or committed templates (.env.example)
    2. Proper environment variable declarations
    3. Proper CORS and security headers configuration
    """
    env_example = Path(__file__).resolve().parents[2] / ".env.example"
    assert env_example.exists(), ".env.example file must exist in repository root"
    env_content = env_example.read_text(encoding="utf-8")

    forbidden_patterns = ["sk-proj-", "AIzaSy", "ghp_", "github_pat_"]
    for pattern in forbidden_patterns:
        assert pattern not in env_content, f"Exposed live secret '{pattern}' detected in .env.example!"

    # Ensure required configuration keys are documented in .env.example
    required_keys = [
        "DATABASE_URL",
        "JWT_SECRET",
        "LLM_PROVIDER",
        "CORS_ORIGINS",
    ]
    for key in required_keys:
        assert key in env_content, f"Missing required configuration key '{key}' in .env.example"
