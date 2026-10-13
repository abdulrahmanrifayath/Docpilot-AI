import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_phase5_dependency_analysis_api_e2e(tmp_path):
    """Scenario: Full API workflow for Phase 5 Dependency and Relationship Analysis."""
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Dependency Analysis Architecture Repo", "source_type": "zip"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # 2. Build ZIP archive with an architecture chain:
        # Authentication API -> UserService -> JWTService -> UserRepository -> Database
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "backend/database.py",
                '''"""Database connection provider."""
class Database:
    def connect(self):
        pass
''',
            )
            zf.writestr(
                "backend/repositories.py",
                '''"""Persistence repository layer."""
from backend.database import Database

class BaseRepository:
    def __init__(self, db: Database):
        self.db = db

class UserRepository(BaseRepository):
    """User persistence repository."""
    def find_by_id(self, user_id: str):
        return {"id": user_id}
''',
            )
            zf.writestr(
                "backend/services.py",
                '''"""Business service layer."""
from backend.repositories import UserRepository
import jwt

class JWTService:
    def encode_token(self, payload: dict) -> str:
        return "sample_token"

class UserService:
    def __init__(self, repo: UserRepository, jwt_svc: JWTService):
        self.repo = repo
        self.jwt_svc = jwt_svc

    def authenticate(self, username: str) -> dict:
        user = self.repo.find_by_id(username)
        token = self.jwt_svc.encode_token(user)
        return {"user": user, "token": token}
''',
            )
            zf.writestr(
                "backend/api.py",
                '''"""FastAPI route handlers."""
from fastapi import FastAPI, Depends
from backend.services import UserService

app = FastAPI()

@app.post("/auth/login")
async def login(user_service: UserService = Depends()):
    """Authentication API endpoint."""
    return user_service.authenticate("admin")
''',
            )
            zf.writestr(
                "frontend/AuthCard.tsx",
                '''import React, { useState } from 'react';
import axios from 'axios';

export interface AuthCardProps {
    title: string;
}

export class BaseComponent {}

export class AuthCardManager extends BaseComponent {
    refresh() {}
}

export const AuthCard: React.FC<AuthCardProps> = ({ title }) => {
    return <div>{title}</div>;
};
''',
            )

        zip_bytes = zip_buffer.getvalue()

        # Upload ZIP
        upload_resp = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_bytes, "application/zip")},
        )
        assert upload_resp.status_code == 200

        # Parse project code first
        parse_resp = await client.post(f"/api/v1/projects/{project_id}/parse")
        assert parse_resp.status_code == 200

        # 3. Analyze Dependencies: POST /api/v1/projects/{project_id}/dependencies/analyze
        analyze_resp = await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        assert analyze_resp.status_code == 200
        analysis_data = analyze_resp.json()
        assert analysis_data["project_id"] == project_id
        assert analysis_data["status"] == "ANALYZED"
        assert analysis_data["total_nodes"] >= 10
        assert analysis_data["total_edges"] >= 8
        assert analysis_data["internal_dependencies"] >= 5
        assert analysis_data["external_dependencies"] >= 2  # jwt, fastapi, axios, react

        # Check breakdown contains required edge types
        breakdown = analysis_data["breakdown"]
        assert "IMPORTS" in breakdown
        assert "EXTENDS" in breakdown
        assert breakdown["EXTENDS"] >= 2  # UserRepository extends BaseRepository, AuthCardManager extends BaseComponent

        # 4. List Dependencies: GET /api/v1/projects/{project_id}/dependencies
        deps_resp = await client.get(f"/api/v1/projects/{project_id}/dependencies")
        assert deps_resp.status_code == 200
        all_deps = deps_resp.json()
        assert len(all_deps) == analysis_data["total_edges"]

        # Validate edge properties
        first_edge = all_deps[0]
        assert "id" in first_edge
        assert "source" in first_edge
        assert "target" in first_edge
        assert "relationship_type" in first_edge
        assert "confidence" in first_edge
        assert first_edge["confidence"] > 0.0
        assert "metadata" in first_edge
        assert "description" in first_edge["metadata"]
        assert "static analysis detected" in first_edge["metadata"]["description"]

        # 5. Filter Dependencies by relationship_type: EXTENDS
        extends_resp = await client.get(f"/api/v1/projects/{project_id}/dependencies?relationship_type=EXTENDS")
        assert extends_resp.status_code == 200
        extends_edges = extends_resp.json()
        assert len(extends_edges) >= 2
        assert all(e["relationship_type"] == "EXTENDS" for e in extends_edges)
        extends_pairs = [(e["source"], e["target"]) for e in extends_edges]
        assert ("UserRepository", "BaseRepository") in extends_pairs

        # 6. Filter Dependencies by is_external
        external_resp = await client.get(f"/api/v1/projects/{project_id}/dependencies?is_external=true")
        assert external_resp.status_code == 200
        ext_edges = external_resp.json()
        assert len(ext_edges) >= 2
        ext_targets = {e["target"] for e in ext_edges}
        assert "jwt" in ext_targets or "fastapi" in ext_targets or "axios" in ext_targets or "react" in ext_targets

        # 7. Get Full Graph: GET /api/v1/projects/{project_id}/dependencies/graph
        graph_resp = await client.get(f"/api/v1/projects/{project_id}/dependencies/graph")
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert "stats" in graph_data
        assert len(graph_data["nodes"]) == analysis_data["total_nodes"]
        assert len(graph_data["edges"]) == analysis_data["total_edges"]

        # Verify node types
        node_names = {n["name"] for n in graph_data["nodes"]}
        assert "UserRepository" in node_names
        assert "UserService" in node_names
        assert "JWTService" in node_names
        assert "Database" in node_names

        # 8. Get Entity Dependencies: GET /api/v1/projects/{project_id}/dependencies/entity/{entity_id}
        entity_resp = await client.get(f"/api/v1/projects/{project_id}/dependencies/entity/UserRepository")
        assert entity_resp.status_code == 200
        entity_data = entity_resp.json()
        assert entity_data["entity_name"] == "UserRepository"
        assert "incoming" in entity_data
        assert "outgoing" in entity_data
        assert "neighbors" in entity_data

        # Verify outgoing extends BaseRepository or incoming from UserService/login
        out_targets = [e["target"] for e in entity_data["outgoing"]]
        assert "BaseRepository" in out_targets or any(e["source"] == "UserRepository" for e in entity_data["outgoing"])
