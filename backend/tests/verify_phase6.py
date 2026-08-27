import io
import zipfile
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


def make_zip(files_dict):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p, c in files_dict.items():
            zf.writestr(p, c)
    buf.seek(0)
    return buf


def run_phase6_live_tests():
    print("==================================================")
    print("PHASE 6 LIVE VERIFICATION: AUTOMATIC API DISCOVERY")
    print("==================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live API Discovery Project",
            "description": "FastAPI and Flask route discovery validation",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "app/main.py": (
            'from fastapi import FastAPI\n'
            'from app.routers import users, auth\n\n'
            'app = FastAPI(title="Demo SaaS")\n'
            '@app.get("/health", summary="Health check endpoint")\n'
            'def health():\n'
            '    return {"status": "ok"}\n'
        ),
        "app/routers/users.py": (
            'from fastapi import APIRouter, Depends, status\n'
            'from typing import List, Optional\n'
            'from pydantic import BaseModel\n\n'
            'class UserResponse(BaseModel):\n'
            '    id: int\n'
            '    username: str\n'
            '    email: str\n\n'
            'class UserCreate(BaseModel):\n'
            '    username: str\n'
            '    email: str\n'
            '    password: str\n\n'
            'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
            '@router.get("", response_model=List[UserResponse], summary="List all users")\n'
            'def list_users(skip: int = 0, limit: int = 100, current_user = Depends(get_current_user)):\n'
            '    """Returns paginated list of active users."""\n'
            '    return []\n\n'
            '@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")\n'
            'def get_user(user_id: int, current_user = Depends(get_current_user)):\n'
            '    """Returns single user by identifier."""\n'
            '    return {"id": user_id, "username": "admin", "email": "admin@example.com"}\n\n'
            '@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user")\n'
            'def create_user(payload: UserCreate):\n'
            '    """Registers a new user."""\n'
            '    return {"id": 1, "username": payload.username, "email": payload.email}\n'
        ),
        "app/routers/auth.py": (
            'from fastapi import APIRouter\n'
            'from pydantic import BaseModel\n\n'
            'class LoginRequest(BaseModel):\n'
            '    username: str\n'
            '    password: str\n\n'
            'class TokenResponse(BaseModel):\n'
            '    access_token: str\n'
            '    token_type: str\n\n'
            'router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])\n\n'
            '@router.post("/login", response_model=TokenResponse, summary="User authentication")\n'
            'def login(credentials: LoginRequest):\n'
            '    return {"access_token": "token123", "token_type": "bearer"}\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("api_project.zip", sample_zip, "application/zip")})

    # 2. Trigger API Analysis
    print("\n--- 1. Testing POST /apis/analyze ---")
    analyze_res = client.post(f"/api/v1/projects/{p_id}/apis/analyze")
    assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
    analyze_data = analyze_res.json()

    print(f"Status: {analyze_data['status']}")
    print(f"Total APIs: {analyze_data['total_apis']}")
    print(f"APIs by Method: {analyze_data['apis_by_method']}")
    print(f"APIs by Framework: {analyze_data['apis_by_framework']}")
    print(f"Duration: {analyze_data['duration_ms']}ms")

    assert analyze_data["status"] == "ANALYZED"
    assert analyze_data["total_apis"] >= 5
    assert analyze_data["apis_by_method"]["GET"] >= 3
    assert analyze_data["apis_by_method"]["POST"] >= 2
    assert analyze_data["apis_by_framework"]["FastAPI"] >= 5

    # 3. Query GET /apis
    print("\n--- 2. Testing GET /apis ---")
    apis_res = client.get(f"/api/v1/projects/{p_id}/apis")
    assert apis_res.status_code == 200
    all_apis = apis_res.json()
    print(f"Retrieved {all_apis['total_apis']} endpoints")

    for api in all_apis["apis"]:
        print(f"  • [{api['method']}] {api['path']} -> {api['handler_name']} (Auth: {api['authentication_required']}, Tags: {api['tags']})")

    # 4. Filter by Auth
    print("\n--- 3. Testing GET /apis?auth_required=true ---")
    auth_res = client.get(f"/api/v1/projects/{p_id}/apis", params={"auth_required": True})
    assert auth_res.status_code == 200
    secured = auth_res.json()["apis"]
    print(f"Secured endpoints count: {len(secured)}")
    assert all(a["authentication_required"] for a in secured)
    assert any("/api/v1/users" in a["path"] for a in secured)

    # 5. Query GET /apis/{api_id}
    print("\n--- 4. Testing GET /apis/{api_id} ---")
    first_api = all_apis["apis"][0]
    detail_res = client.get(f"/api/v1/projects/{p_id}/apis/{first_api['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    print(f"Endpoint detail verified: [{detail['method']}] {detail['path']}")
    print(f"  Handler: {detail['handler_name']} in {detail['file_path']}")
    print(f"  Parameters: {[p['name'] + ' (' + p['in_location'] + ')' for p in (detail['request_schema']['parameters'] if detail['request_schema'] else [])]}")
    print(f"  Response Model: {detail['response_schema']['response_model'] if detail['response_schema'] else None}")

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n==================================================")
    print("ALL PHASE 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_phase6_live_tests()
