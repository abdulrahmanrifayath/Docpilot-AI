import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.parsers.code_extractor import code_parsing_engine, PythonCodeExtractor, JsTsCodeExtractor


def test_python_ast_extractor_comprehensive():
    """Verify Python AST extractor detects all required elements."""
    py_code = '''"""Module docstring for auth service."""
import os
import sys
from typing import Optional, List
from datetime import datetime

class BaseEntity:
    pass

class UserModel(BaseEntity):
    """User representation model."""
    def __init__(self, username: str, email: Optional[str] = None):
        self.username = username
        self.email = email

    def get_display_name(self) -> str:
        """Returns the user's display name."""
        return self.username

@decorator_one
@decorator_two(option=True)
async def authenticate_user(username: str, token: str) -> bool:
    """Authenticates a user against secure token."""
    return True

def sync_helper(count: int = 10) -> List[str]:
    return []
'''
    extractor = PythonCodeExtractor()
    entities = extractor.extract("services/auth.py", py_code)

    by_name = {e.name: e for e in entities}
    by_type = {}
    for e in entities:
        by_type.setdefault(e.entity_type, []).append(e)

    # 1. Module
    assert "auth" in by_name
    assert by_name["auth"].entity_type == "MODULE"
    assert "Module docstring" in by_name["auth"].metadata.get("docstring", "")
    assert len(by_name["auth"].metadata.get("imports", [])) >= 4

    # 2. Classes and Inheritance
    assert "BaseEntity" in by_name
    assert by_name["BaseEntity"].entity_type == "CLASS"

    assert "UserModel" in by_name
    user_cls = by_name["UserModel"]
    assert user_cls.entity_type == "CLASS"
    assert "BaseEntity" in user_cls.metadata.get("bases", [])
    assert "User representation model" in user_cls.metadata.get("docstring", "")

    # 3. Methods
    assert "__init__" in by_name
    init_method = by_name["__init__"]
    assert init_method.entity_type == "METHOD"
    assert init_method.parent_entity == "UserModel"
    assert "username" in init_method.signature

    assert "get_display_name" in by_name
    get_disp = by_name["get_display_name"]
    assert get_disp.entity_type == "METHOD"
    assert get_disp.parent_entity == "UserModel"
    assert get_disp.metadata.get("return_type") == "str"

    # 4. Async Function with decorators and parameters
    assert "authenticate_user" in by_name
    auth_fn = by_name["authenticate_user"]
    assert auth_fn.entity_type == "FUNCTION"
    assert auth_fn.metadata.get("is_async") is True
    assert auth_fn.metadata.get("return_type") == "bool"
    assert "decorator_one" in auth_fn.metadata.get("decorators", [])
    assert any("decorator_two" in d for d in auth_fn.metadata.get("decorators", []))
    assert "Authenticates a user" in auth_fn.metadata.get("docstring", "")

    # 5. Sync Function
    assert "sync_helper" in by_name
    sync_fn = by_name["sync_helper"]
    assert sync_fn.entity_type == "FUNCTION"
    assert sync_fn.metadata.get("is_async") is False


def test_jsts_extractor_comprehensive():
    """Verify JavaScript / TypeScript parser detects interfaces, classes, components, functions."""
    ts_code = '''import React, { useState } from 'react';
import axios from 'axios';

export interface UserProfileProps {
    userId: string;
    isActive?: boolean;
}

export class SessionManager {
    private token: string;

    constructor(token: string) {
        this.token = token;
    }

    public refreshSession(): Promise<boolean> {
        return Promise.resolve(true);
    }
}

export const UserCard: React.FC<UserProfileProps> = ({ userId, isActive }) => {
    return (
        <div className="user-card">
            <h3>{userId}</h3>
        </div>
    );
};

export async function fetchUserData(id: string): Promise<any> {
    return null;
}
'''
    extractor = JsTsCodeExtractor()
    entities = extractor.extract("src/components/UserCard.tsx", ts_code)

    by_name = {e.name: e for e in entities}

    # 1. Interface
    assert "UserProfileProps" in by_name
    assert by_name["UserProfileProps"].entity_type == "INTERFACE"

    # 2. Class and Method
    assert "SessionManager" in by_name
    assert by_name["SessionManager"].entity_type == "CLASS"

    # Methods
    method_names = [e.name for e in entities if e.entity_type == "METHOD"]
    assert "refreshSession" in method_names or "constructor" in method_names

    # 3. Detectable React Component
    assert "UserCard" in by_name
    assert by_name["UserCard"].entity_type == "COMPONENT"

    # 4. Function
    assert "fetchUserData" in by_name
    assert by_name["fetchUserData"].entity_type == "FUNCTION"

    # 5. Imports & Exports in module metadata
    module_entity = by_name.get("UserCard.tsx") or by_name.get("UserCard")
    modules = [e for e in entities if e.entity_type == "MODULE"]
    assert len(modules) >= 1
    mod = modules[0]
    assert len(mod.metadata.get("imports", [])) >= 1


@pytest.mark.asyncio
async def test_static_code_parsing_engine_api_e2e(tmp_path):
    """Scenario 3: Full API workflow for Phase 4 code parsing and entity queries."""
    from app.database.session import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # 1. Create a project
        create_resp = await client.post(
            "/api/v1/projects",
            json={"name": "Static Analysis Test Project", "source_type": "zip"},
        )
        assert create_resp.status_code == 201
        project_id = create_resp.json()["id"]

        # 2. Build a ZIP archive containing Python and TypeScript files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "backend/models.py",
                '''"""Database models module."""
class Base:
    id: int

class Customer(Base):
    """Customer entity."""
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name

def helper():
    pass
''',
            )
            zf.writestr(
                "frontend/Button.tsx",
                '''import React from "react";

export interface ButtonProps {
    label: string;
}

export const PrimaryButton = ({ label }: ButtonProps) => {
    return <button>{label}</button>;
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

        # 3. Trigger Parse: POST /api/v1/projects/{project_id}/parse
        parse_resp = await client.post(f"/api/v1/projects/{project_id}/parse")
        assert parse_resp.status_code == 200
        parse_data = parse_resp.json()
        assert parse_data["project_id"] == project_id
        assert parse_data["status"] == "PARSED"
        assert parse_data["total_files_parsed"] >= 2
        assert parse_data["total_entities_extracted"] >= 5
        assert "CLASS" in parse_data["entity_breakdown"]
        assert "FUNCTION" in parse_data["entity_breakdown"] or "COMPONENT" in parse_data["entity_breakdown"]

        # 4. List all Entities: GET /api/v1/projects/{project_id}/entities
        entities_resp = await client.get(f"/api/v1/projects/{project_id}/entities")
        assert entities_resp.status_code == 200
        entities = entities_resp.json()
        assert len(entities) == parse_data["total_entities_extracted"]

        # Check entity structure
        first = entities[0]
        assert "id" in first
        assert "project_id" in first
        assert "file_path" in first
        assert "name" in first
        assert "entity_type" in first
        assert "start_line" in first
        assert "end_line" in first
        assert "signature" in first
        assert "parent_entity" in first
        assert "metadata" in first

        # 5. Filter entities by entity_type: GET /api/v1/projects/{project_id}/entities?entity_type=CLASS
        class_resp = await client.get(f"/api/v1/projects/{project_id}/entities?entity_type=CLASS")
        assert class_resp.status_code == 200
        class_entities = class_resp.json()
        assert len(class_entities) >= 2
        assert all(e["entity_type"] == "CLASS" for e in class_entities)
        class_names = [e["name"] for e in class_entities]
        assert "Customer" in class_names
        assert "Base" in class_names

        # 6. Retrieve single entity by ID: GET /api/v1/projects/{project_id}/entities/{entity_id}
        customer_entity = next(e for e in class_entities if e["name"] == "Customer")
        entity_id = customer_entity["id"]

        single_resp = await client.get(f"/api/v1/projects/{project_id}/entities/{entity_id}")
        assert single_resp.status_code == 200
        single_data = single_resp.json()
        assert single_data["id"] == entity_id
        assert single_data["name"] == "Customer"
        assert single_data["metadata"]["bases"] == ["Base"]

        # 7. File entities: GET /api/v1/projects/{project_id}/files/{file_id}/entities
        file_resp = await client.get(f"/api/v1/projects/{project_id}/files/backend/models.py/entities")
        assert file_resp.status_code == 200
        file_entities = file_resp.json()
        assert len(file_entities) >= 3
        assert all("models.py" in e["file_path"] for e in file_entities)

        # Also test with component file
        comp_file_resp = await client.get(f"/api/v1/projects/{project_id}/files/frontend/Button.tsx/entities")
        assert comp_file_resp.status_code == 200
        comp_entities = comp_file_resp.json()
        assert any(e["entity_type"] in {"COMPONENT", "FUNCTION"} for e in comp_entities)
