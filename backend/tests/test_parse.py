import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from backend.app.analyzers.python_parser import PythonParser
from backend.app.analyzers.js_ts_parser import JsTsParser


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


def test_python_ast_parser_direct():
    code = '''"""User management module for DocPilot."""
import os
from typing import List, Optional
from backend.base import BaseService

@decorator_one
class UserService(BaseService):
    """Handles user operations."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url

    @classmethod
    def create_default(cls) -> "UserService":
        """Factory method."""
        return cls("sqlite:///default.db")

    async def get_user_by_id(self, user_id: str, include_deleted: bool = False) -> Optional[dict]:
        """Fetch single user."""
        return {"id": user_id}

async def calculate_metrics(values: List[int], multiplier: float = 1.5) -> float:
    """Calculate aggregate score."""
    return sum(values) * multiplier
'''
    entities = PythonParser.parse_source(code, "services/user_service.py")
    entities_by_name = {e.name: e for e in entities}

    # 1. Module
    assert "user_service" in entities_by_name
    mod = entities_by_name["user_service"]
    assert mod.entity_type == "MODULE"
    assert mod.docstring == "User management module for DocPilot."
    assert len(mod.metadata_json["imports"]) == 4

    # 2. Class
    assert "UserService" in entities_by_name
    cls_entity = entities_by_name["UserService"]
    assert cls_entity.entity_type == "CLASS"
    assert "BaseService" in cls_entity.metadata_json["bases"]
    assert cls_entity.docstring == "Handles user operations."

    # 3. Methods
    assert "__init__" in entities_by_name
    assert entities_by_name["__init__"].parent_entity == "UserService"
    assert entities_by_name["__init__"].entity_type == "METHOD"

    assert "create_default" in entities_by_name
    create_def = entities_by_name["create_default"]
    assert create_def.parent_entity == "UserService"
    assert create_def.metadata_json["is_classmethod"] is True

    assert "get_user_by_id" in entities_by_name
    get_user = entities_by_name["get_user_by_id"]
    assert get_user.parent_entity == "UserService"
    assert get_user.metadata_json["is_async"] is True
    assert "user_id" in [p["name"] for p in get_user.metadata_json["parameters"]]

    # 4. Top-level function
    assert "calculate_metrics" in entities_by_name
    calc = entities_by_name["calculate_metrics"]
    assert calc.entity_type == "FUNCTION"
    assert calc.parent_entity is None
    assert calc.metadata_json["is_async"] is True
    assert calc.metadata_json["return_type"] == "float"


def test_typescript_treesitter_parser_direct():
    code = '''import React, { useState } from 'react';

export interface UserProfile {
    id: string;
    username: string;
    avatarUrl?: string;
}

export class AuthClient extends BaseClient {
    private token: string;

    constructor(token: string) {
        super();
        this.token = token;
    }

    async validateSession(sessionId: string): Promise<boolean> {
        return sessionId.length > 0;
    }
}

export const UserBadge: React.FC<UserProfile> = ({ id, username }) => {
    const [badgeActive, setBadgeActive] = useState(true);
    return <span className="badge">{username}</span>;
};

export function formatUsername(raw: string): string {
    return raw.trim().toLowerCase();
}
'''
    entities = JsTsParser.parse_source(code, "src/components/UserBadge.tsx")
    entities_by_name = {e.name: e for e in entities}

    # 1. Module
    assert "UserBadge" in entities_by_name or any(e.entity_type == "MODULE" for e in entities)

    # 2. Interface
    assert "UserProfile" in entities_by_name
    iface = entities_by_name["UserProfile"]
    assert iface.entity_type == "INTERFACE"

    # 3. Class & Methods
    assert "AuthClient" in entities_by_name
    auth_cls = entities_by_name["AuthClient"]
    assert auth_cls.entity_type == "CLASS"

    assert "constructor" in entities_by_name
    assert entities_by_name["constructor"].parent_entity == "AuthClient"

    assert "validateSession" in entities_by_name
    val_sess = entities_by_name["validateSession"]
    assert val_sess.parent_entity == "AuthClient"
    assert val_sess.metadata_json["is_async"] is True

    # 4. React Component
    assert "UserBadge" in entities_by_name
    badge_comp = [e for e in entities if e.name == "UserBadge" and e.entity_type == "COMPONENT"][0]
    assert badge_comp.entity_type == "COMPONENT"
    assert badge_comp.metadata_json["has_jsx"] is True

    # 5. Helper Function
    assert "formatUsername" in entities_by_name
    fmt = entities_by_name["formatUsername"]
    assert fmt.entity_type == "FUNCTION"


def test_parse_project_api_endpoints(client: TestClient):
    proj = client.post("/api/v1/projects", json={"name": "Parse Test Project", "source_type": "zip"}).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "backend/main.py": (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            "class ItemService:\n"
            "    def get_items(self):\n"
            "        return []\n\n"
            "def init_app():\n"
            "    return app\n"
        ),
        "frontend/src/Card.tsx": (
            "import React from 'react';\n\n"
            "export interface CardProps {\n"
            "    title: string;\n"
            "}\n\n"
            "export const Card: React.FC<CardProps> = ({ title }) => {\n"
            "    return <div className='card'>{title}</div>;\n"
            "};\n"
        ),
    })

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("project.zip", zip_buf, "application/zip")})

    # 1. Trigger POST /parse
    parse_res = client.post(f"/api/v1/projects/{proj_id}/parse")
    assert parse_res.status_code == 200
    parse_data = parse_res.json()

    assert parse_data["status"] == "PARSED"
    assert parse_data["files_parsed"] == 2
    assert parse_data["total_entities"] >= 6
    assert "CLASS" in parse_data["entities_by_type"]
    assert "FUNCTION" in parse_data["entities_by_type"]
    assert "INTERFACE" in parse_data["entities_by_type"]
    assert "COMPONENT" in parse_data["entities_by_type"]

    # 2. Query GET /entities
    entities_res = client.get(f"/api/v1/projects/{proj_id}/entities")
    assert entities_res.status_code == 200
    all_ents = entities_res.json()
    assert all_ents["total_entities"] >= 6

    # 3. Query with filter GET /entities?entity_type=CLASS
    class_res = client.get(f"/api/v1/projects/{proj_id}/entities", params={"entity_type": "CLASS"})
    assert class_res.status_code == 200
    classes = class_res.json()["entities"]
    assert any(c["name"] == "ItemService" for c in classes)

    # 4. Query entity by ID GET /entities/{entity_id}
    first_ent = all_ents["entities"][0]
    ent_detail_res = client.get(f"/api/v1/projects/{proj_id}/entities/{first_ent['id']}")
    assert ent_detail_res.status_code == 200
    assert ent_detail_res.json()["name"] == first_ent["name"]

    # 5. Query file entities GET /files/{file_path}/entities
    file_ent_res = client.get(f"/api/v1/projects/{proj_id}/files/backend/main.py/entities")
    assert file_ent_res.status_code == 200
    file_ents = file_ent_res.json()
    assert file_ents["file_path"] == "backend/main.py"
    assert any(e["name"] == "ItemService" for e in file_ents["entities"])

    client.delete(f"/api/v1/projects/{proj_id}")
