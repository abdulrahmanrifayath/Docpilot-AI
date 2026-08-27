import io
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


def run_phase4_live_tests():
    print("==================================================")
    print("PHASE 4 LIVE VERIFICATION: STATIC CODE PARSING ENGINE")
    print("==================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live Static Code Parse Test",
            "description": "Validating Python AST and TS/JS Tree-sitter parsers",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "backend/services/auth_service.py": (
            '"""Authentication service module."""\n'
            'from typing import Optional, List\n'
            'from backend.models import User\n\n'
            'class AuthService:\n'
            '    """Handles user credential validation."""\n\n'
            '    def __init__(self, secret: str = "secret"):\n'
            '        self.secret = secret\n\n'
            '    async def authenticate(self, email: str, password: str) -> Optional[User]:\n'
            '        """Authenticate user by email and password."""\n'
            '        return User(email=email)\n\n'
            'def hash_password(plain: str) -> str:\n'
            '    """Return SHA-256 hash."""\n'
            '    return plain\n'
        ),
        "frontend/src/UserProfile.tsx": (
            'import React, { useState } from "react";\n\n'
            'export interface UserProfileProps {\n'
            '    userId: string;\n'
            '    displayName?: string;\n'
            '}\n\n'
            'export class UserAnalyticsClient {\n'
            '    async trackLogin(userId: string): Promise<void> {\n'
            '        console.log("Logged in:", userId);\n'
            '    }\n'
            '}\n\n'
            'export const UserProfileCard: React.FC<UserProfileProps> = ({ userId, displayName }) => {\n'
            '    const [active, setActive] = useState(true);\n'
            '    return <div className="user-profile">{displayName || userId}</div>;\n'
            '};\n\n'
            'export function formatUserHandle(name: string): string {\n'
            '    return `@${name.toLowerCase()}`;\n'
            '}\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("code.zip", sample_zip, "application/zip")})

    # 2. Trigger POST /parse
    print("\n--- 1. Testing POST /parse ---")
    parse_res = client.post(f"/api/v1/projects/{p_id}/parse")
    assert parse_res.status_code == 200, f"Parse failed: {parse_res.text}"
    parse_data = parse_res.json()

    print(f"Status: {parse_data['status']}")
    print(f"Files Parsed: {parse_data['files_parsed']}")
    print(f"Total Entities: {parse_data['total_entities']}")
    print(f"Entities by Type: {parse_data['entities_by_type']}")
    print(f"Duration: {parse_data['duration_ms']}ms")

    assert parse_data["status"] == "PARSED"
    assert parse_data["files_parsed"] == 2
    assert parse_data["entities_by_type"].get("CLASS", 0) >= 2
    assert parse_data["entities_by_type"].get("FUNCTION", 0) >= 2
    assert parse_data["entities_by_type"].get("METHOD", 0) >= 3
    assert parse_data["entities_by_type"].get("INTERFACE", 0) >= 1
    assert parse_data["entities_by_type"].get("COMPONENT", 0) >= 1

    # 3. Query GET /entities
    print("\n--- 2. Testing GET /entities ---")
    entities_res = client.get(f"/api/v1/projects/{p_id}/entities")
    assert entities_res.status_code == 200
    all_ents = entities_res.json()
    print(f"Retrieved {all_ents['total_entities']} total entities")

    # 4. Query GET /entities?entity_type=CLASS
    print("\n--- 3. Testing GET /entities?entity_type=CLASS ---")
    class_res = client.get(f"/api/v1/projects/{p_id}/entities", params={"entity_type": "CLASS"})
    assert class_res.status_code == 200
    classes = class_res.json()["entities"]
    class_names = [c["name"] for c in classes]
    print(f"Found Classes: {class_names}")
    assert "AuthService" in class_names
    assert "UserAnalyticsClient" in class_names

    # 5. Query GET /entities/{entity_id}
    print("\n--- 4. Testing GET /entities/{entity_id} ---")
    first_ent = all_ents["entities"][0]
    detail_res = client.get(f"/api/v1/projects/{p_id}/entities/{first_ent['id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == first_ent["name"]
    print(f"Entity detail verified: {detail_res.json()['name']} ({detail_res.json()['entity_type']})")

    # 6. Query GET /files/{file_path}/entities
    print("\n--- 5. Testing GET /files/backend/services/auth_service.py/entities ---")
    file_res = client.get(f"/api/v1/projects/{p_id}/files/backend/services/auth_service.py/entities")
    assert file_res.status_code == 200
    file_ents = file_res.json()
    print(f"File entities count: {file_ents['total_entities']}")
    print(f"Entity types breakdown: {file_ents['entity_counts']}")
    assert any(e["name"] == "AuthService" for e in file_ents["entities"])
    assert any(e["name"] == "authenticate" for e in file_ents["entities"])
    assert any(e["name"] == "hash_password" for e in file_ents["entities"])

    print("\n--- 6. Testing GET /files/frontend/src/UserProfile.tsx/entities ---")
    ts_res = client.get(f"/api/v1/projects/{p_id}/files/frontend/src/UserProfile.tsx/entities")
    assert ts_res.status_code == 200
    ts_ents = ts_res.json()
    print(f"TS file entities: {[e['name'] + ' (' + e['entity_type'] + ')' for e in ts_ents['entities']]}")
    assert any(e["name"] == "UserProfileProps" and e["entity_type"] == "INTERFACE" for e in ts_ents["entities"])
    assert any(e["name"] == "UserProfileCard" and e["entity_type"] == "COMPONENT" for e in ts_ents["entities"])

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n==================================================")
    print("ALL PHASE 4 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_phase4_live_tests()
