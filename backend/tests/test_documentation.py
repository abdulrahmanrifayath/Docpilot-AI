import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from backend.app.llm.mock_client import MockLLMClient
from backend.app.llm.base import LLMMessage


def make_test_zip(files_dict: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files_dict.items():
            zf.writestr(path, content)
    buf.seek(0)
    return buf


@pytest.mark.asyncio
async def test_llm_mock_client_direct():
    client = MockLLMClient()
    assert client.is_configured() is True
    assert client.get_provider_name() == "mock"

    res = await client.generate([
        LLMMessage(role="system", content="System prompt"),
        LLMMessage(role="user", content="DOCUMENT TYPE: PROJECT_OVERVIEW\nPROJECT NAME: TestApp\nDetails..."),
    ])
    assert res.content.startswith("# TestApp")
    assert "Executive Summary" in res.content
    assert res.tokens_used > 0


def test_documentation_generation_and_retrieval(client: TestClient):
    # 1. Create project
    proj = client.post(
        "/api/v1/projects",
        json={"name": "DocPilot AI Core Demo", "source_type": "zip"},
    ).json()
    proj_id = proj["id"]

    zip_buf = make_test_zip({
        "backend/app/main.py": (
            'from fastapi import FastAPI\n'
            'from backend.app.routers import users\n\n'
            'app = FastAPI(title="DocPilot AI Core")\n'
            'app.include_router(users.router)\n'
        ),
        "backend/app/routers/users.py": (
            'from fastapi import APIRouter, Depends\n'
            'from backend.app.services.user_service import UserService\n'
            'from backend.app.models.user import User\n\n'
            'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
            '@router.get("", summary="List all registered users")\n'
            'def list_users(service: UserService = Depends()):\n'
            '    return service.get_all()\n'
        ),
        "backend/app/services/user_service.py": (
            'from backend.app.models.user import User\n\n'
            'class UserService:\n'
            '    """Service managing user operations."""\n'
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

    client.post(f"/api/v1/projects/{proj_id}/upload", files={"file": ("repo.zip", zip_buf, "application/zip")})

    # Run underlying scans
    client.post(f"/api/v1/projects/{proj_id}/scan")
    client.post(f"/api/v1/projects/{proj_id}/parse")
    client.post(f"/api/v1/projects/{proj_id}/dependencies/analyze")
    client.post(f"/api/v1/projects/{proj_id}/apis/analyze")
    client.post(f"/api/v1/projects/{proj_id}/database/analyze")

    # 2. Check Documentation Status
    status_res = client.get(f"/api/v1/projects/{proj_id}/documentation/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "available_doc_types" in status_data
    assert len(status_data["available_doc_types"]) == 9

    # 3. Generate All Documentation with mock provider
    gen_res = client.post(
        f"/api/v1/projects/{proj_id}/documentation/generate",
        json={"provider": "mock"},
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["status"] == "GENERATED"
    assert gen_data["generated_count"] == 9
    assert len(gen_data["documents"]) == 9

    doc_types = {d["document_type"] for d in gen_data["documents"]}
    assert "PROJECT_OVERVIEW" in doc_types
    assert "README" in doc_types
    assert "ARCHITECTURE_OVERVIEW" in doc_types
    assert "API_DOCUMENTATION" in doc_types
    assert "DATABASE_DOCUMENTATION" in doc_types
    assert "FOLDER_DOC" in doc_types
    assert "FILE_DOC" in doc_types
    assert "CLASS_DOC" in doc_types
    assert "FUNCTION_DOC" in doc_types

    # 4. List Documentation
    list_res = client.get(f"/api/v1/projects/{proj_id}/documentation")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_documents"] == 9

    # 5. Filter Documentation by type
    api_doc_res = client.get(f"/api/v1/projects/{proj_id}/documentation", params={"document_type": "API_DOCUMENTATION"})
    assert api_doc_res.status_code == 200
    api_docs = api_doc_res.json()
    assert api_docs["total_documents"] == 1
    api_doc = api_docs["documents"][0]
    assert api_doc["document_type"] == "API_DOCUMENTATION"
    assert len(api_doc["source_entities"]) > 0

    # 6. Retrieve single document
    doc_detail_res = client.get(f"/api/v1/projects/{proj_id}/documentation/{api_doc['id']}")
    assert doc_detail_res.status_code == 200
    doc_detail = doc_detail_res.json()
    assert doc_detail["id"] == api_doc["id"]
    assert doc_detail["version"] == 1

    # 7. Regenerate document
    regen_res = client.post(f"/api/v1/projects/{proj_id}/documentation/{api_doc['id']}/regenerate")
    assert regen_res.status_code == 200
    regen_data = regen_res.json()
    assert regen_data["id"] == api_doc["id"]
    assert regen_data["version"] == 2

    # Cleanup
    client.delete(f"/api/v1/projects/{proj_id}")
