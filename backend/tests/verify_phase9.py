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


def run_phase9_live_tests():
    print("=========================================================")
    print("PHASE 9 LIVE VERIFICATION: AI DOCUMENTATION GENERATION")
    print("=========================================================")

    # 1. Create project
    p = client.post(
        "/api/v1/projects",
        json={
            "name": "Live Doc Generation Project",
            "description": "Validation of AI Documentation Generation Engine",
            "source_type": "zip",
        },
    ).json()
    p_id = p["id"]

    sample_zip = make_zip({
        "backend/app/main.py": (
            'from fastapi import FastAPI\n'
            'from backend.app.routers import users\n\n'
            'app = FastAPI(title="Live Demo App")\n'
            'app.include_router(users.router)\n'
        ),
        "backend/app/routers/users.py": (
            'from fastapi import APIRouter, Depends\n'
            'from backend.app.services.user_service import UserService\n'
            'from backend.app.models.user import User\n\n'
            'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
            '@router.get("", summary="List all users")\n'
            'def list_users(service: UserService = Depends()):\n'
            '    return service.get_all()\n'
        ),
        "backend/app/services/user_service.py": (
            'from backend.app.models.user import User\n\n'
            'class UserService:\n'
            '    def get_all(self):\n'
            '        return []\n'
        ),
        "backend/app/models/user.py": (
            'from sqlalchemy import String, Integer\n'
            'from sqlalchemy.orm import Mapped, mapped_column\n'
            'from backend.app.database.base import Base\n\n'
            'class User(Base):\n'
            '    __tablename__ = "users"\n'
            '    id: Mapped[int] = mapped_column(primary_key=True)\n'
            '    email: Mapped[str] = mapped_column(String(255), unique=True)\n'
        ),
    })

    client.post(f"/api/v1/projects/{p_id}/upload", files={"file": ("doc_project.zip", sample_zip, "application/zip")})

    # Run analysis
    client.post(f"/api/v1/projects/{p_id}/scan")
    client.post(f"/api/v1/projects/{p_id}/parse")
    client.post(f"/api/v1/projects/{p_id}/dependencies/analyze")
    client.post(f"/api/v1/projects/{p_id}/apis/analyze")
    client.post(f"/api/v1/projects/{p_id}/database/analyze")

    # 2. Check Documentation Status
    print("\n--- 1. Testing GET /documentation/status ---")
    status_res = client.get(f"/api/v1/projects/{p_id}/documentation/status")
    assert status_res.status_code == 200, f"Status failed: {status_res.text}"
    status_data = status_res.json()
    print(f"Provider: {status_data['provider']} | Model: {status_data['model']}")
    print(f"Available Doc Types ({len(status_data['available_doc_types'])}): {status_data['available_doc_types']}")
    assert len(status_data["available_doc_types"]) == 9

    # 3. Generate Documentation (Using Mock Provider for offline live validation)
    print("\n--- 2. Testing POST /documentation/generate ---")
    gen_res = client.post(f"/api/v1/projects/{p_id}/documentation/generate", json={"provider": "mock"})
    assert gen_res.status_code == 200, f"Doc generation failed: {gen_res.text}"
    gen_data = gen_res.json()
    print(f"Status: {gen_data['status']}")
    print(f"Generated Count: {gen_data['generated_count']} in {gen_data['duration_ms']}ms")
    assert gen_data["generated_count"] == 9

    for d in gen_data["documents"]:
        print(f"  • Doc: [{d['document_type']}] '{d['title']}' (v{d['version']}, {len(d['source_entities'])} sources)")

    # 4. Query Documentation List
    print("\n--- 3. Testing GET /documentation ---")
    list_res = client.get(f"/api/v1/projects/{p_id}/documentation")
    assert list_res.status_code == 200
    list_data = list_res.json()
    print(f"Total Documents: {list_data['total_documents']}")
    print(f"Counts By Type: {list_data['counts_by_type']}")
    assert list_data["total_documents"] == 9

    # 5. Filter Documentation
    print("\n--- 4. Testing GET /documentation?document_type=API_DOCUMENTATION ---")
    api_doc_res = client.get(f"/api/v1/projects/{p_id}/documentation", params={"document_type": "API_DOCUMENTATION"})
    assert api_doc_res.status_code == 200
    api_docs = api_doc_res.json()
    api_doc = api_docs["documents"][0]
    print(f"Retrieved Doc ID: {api_doc['id']}")
    print(f"Title: {api_doc['title']}")
    print(f"Source Entities: {api_doc['source_entities']}")

    # 6. Regenerate Documentation
    print("\n--- 5. Testing POST /documentation/{id}/regenerate ---")
    regen_res = client.post(f"/api/v1/projects/{p_id}/documentation/{api_doc['id']}/regenerate")
    assert regen_res.status_code == 200, f"Regeneration failed: {regen_res.text}"
    regen_data = regen_res.json()
    print(f"Regenerated Doc: v{regen_data['version']}")
    assert regen_data["version"] == 2

    # Cleanup
    client.delete(f"/api/v1/projects/{p_id}")

    print("\n=========================================================")
    print("ALL PHASE 9 AI DOCUMENTATION TESTS PASSED SUCCESSFULLY!")
    print("=========================================================")


if __name__ == "__main__":
    run_phase9_live_tests()
