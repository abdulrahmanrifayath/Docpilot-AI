import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import init_db
from app.core.config import settings
from app.ai.llm_client import MockLLMClient
from app.services.documentation_service import documentation_service


@pytest.mark.asyncio
async def test_documentation_generation_unconfigured_state():
    """Verify that when LLM is not configured, API returns a clear configuration-required state and does not fake docs."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 9 Unconfigured Test Project",
                "description": "Tests configuration required state when LLM credentials are absent",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # Ensure LLM client is marked as unconfigured
        unconfigured_mock = MockLLMClient()
        unconfigured_mock.set_configured(False)
        documentation_service.llm_client = unconfigured_mock
        documentation_service.get_client = lambda: unconfigured_mock

        # Call generate endpoint
        gen_res = await client.post(
            f"/api/v1/projects/{project_id}/documentation/generate",
            json={"document_types": ["PROJECT_OVERVIEW", "README"]},
        )
        res_body = gen_res.json()
        error_data = res_body.get("error", res_body)
        assert error_data["status"] == "CONFIGURATION_REQUIRED"
        assert error_data["is_configured"] is False
        assert "not configured" in error_data["message"].lower()

        # Check list endpoint returns empty list, not fake documents
        list_res = await client.get(f"/api/v1/projects/{project_id}/documentation")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 0


@pytest.mark.asyncio
async def test_documentation_generation_pipeline_and_metadata():
    """Verify end-to-end documentation generation with structured context, output metadata, filtering, and regeneration."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 9 E-Commerce Hub",
                "description": "A structured project for verifying AI documentation generation engine",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Package sample multi-tier repository
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "models/product.py",
                "from sqlalchemy import Column, Integer, String, Float\n"
                "from sqlalchemy.orm import declarative_base\n"
                "Base = declarative_base()\n"
                "class Product(Base):\n"
                "    __tablename__ = 'products'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    name = Column(String(100), nullable=False)\n"
                "    price = Column(Float, nullable=False)\n"
            )
            zf.writestr(
                "services/product_service.py",
                "from models.product import Product\n"
                "class ProductService:\n"
                "    def calculate_discount(self, product_id: int, percent: float) -> float:\n"
                "        '''Calculate discount for target product.'''\n"
                "        return 100.0 * (1.0 - percent / 100.0)\n"
            )
            zf.writestr(
                "api/products.py",
                "from fastapi import APIRouter, Depends\n"
                "from pydantic import BaseModel\n"
                "from services.product_service import ProductService\n"
                "router = APIRouter(prefix='/api/v1/products')\n"
                "class DiscountRequest(BaseModel):\n"
                "    percent: float\n"
                "@router.post('/{product_id}/discount')\n"
                "def apply_discount(product_id: int, req: DiscountRequest, svc: ProductService = Depends()):\n"
                "    return {'discounted': svc.calculate_discount(product_id, req.percent)}\n"
            )
        zip_buf.seek(0)

        # Upload and analyze
        await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        await client.post(f"/api/v1/projects/{project_id}/scan")
        await client.post(f"/api/v1/projects/{project_id}/parse")
        await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{project_id}/database/analyze")

        # 3. Configure mock LLM client with realistic grounded responses
        configured_mock = MockLLMClient(model_name="mock-gpt4o-mini")
        configured_mock.set_configured(True)
        documentation_service.llm_client = configured_mock
        documentation_service.get_client = lambda: configured_mock

        # 4. Generate documentation suite
        gen_res = await client.post(
            f"/api/v1/projects/{project_id}/documentation/generate",
            json={
                "document_types": [
                    "PROJECT_OVERVIEW",
                    "README",
                    "ARCHITECTURE_OVERVIEW",
                    "API_DOCS",
                    "DATABASE_DOCS",
                    "CLASS_DOCS",
                    "FUNCTION_DOCS",
                ]
            },
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["status"] == "COMPLETED"
        assert gen_data["total_generated"] >= 5
        docs = gen_data["documents"]

        # Verify each document contains required metadata
        for doc in docs:
            assert doc["project_id"] == project_id
            assert doc["document_type"] in [
                "PROJECT_OVERVIEW",
                "README",
                "ARCHITECTURE_OVERVIEW",
                "API_DOCS",
                "DATABASE_DOCS",
                "CLASS_DOCS",
                "FUNCTION_DOCS",
            ]
            assert isinstance(doc["source_entities"], list)
            assert len(doc["source_entities"]) >= 1
            assert doc["model"] == "mock-gpt4o-mini"
            assert doc["version"] == 1
            assert doc["generated_at"] is not None
            assert len(doc["content"]) > 10

        # 5. Test List All Documents (GET /documentation)
        list_res = await client.get(f"/api/v1/projects/{project_id}/documentation")
        assert list_res.status_code == 200
        all_docs = list_res.json()
        assert len(all_docs) == gen_data["total_generated"]

        # 6. Test Filtering by Document Type (GET /documentation?document_type=API_DOCS)
        api_filter_res = await client.get(
            f"/api/v1/projects/{project_id}/documentation?document_type=API_DOCS"
        )
        assert api_filter_res.status_code == 200
        api_docs = api_filter_res.json()
        assert len(api_docs) == 1
        assert api_docs[0]["document_type"] == "API_DOCS"

        # 7. Test Search Filter (GET /documentation?search=README)
        search_res = await client.get(f"/api/v1/projects/{project_id}/documentation?search=README")
        assert search_res.status_code == 200
        search_docs = search_res.json()
        assert len(search_docs) >= 1

        # 8. Test Document Detail Endpoint (GET /documentation/{document_id})
        target_doc = all_docs[0]
        detail_res = await client.get(
            f"/api/v1/projects/{project_id}/documentation/{target_doc['id']}"
        )
        assert detail_res.status_code == 200
        detail_doc = detail_res.json()
        assert detail_doc["id"] == target_doc["id"]
        assert detail_doc["title"] == target_doc["title"]
        assert detail_doc["version"] == 1

        # 9. Test Regeneration (POST /documentation/{document_id}/regenerate)
        regen_res = await client.post(
            f"/api/v1/projects/{project_id}/documentation/{target_doc['id']}/regenerate"
        )
        assert regen_res.status_code == 200
        regen_doc = regen_res.json()
        assert regen_doc["id"] == target_doc["id"]
        assert regen_doc["version"] == 2, "Regenerating should bump version to 2"
        assert regen_doc["generated_at"] is not None

        # 10. Non-existent document 404 test
        not_found_res = await client.get(
            f"/api/v1/projects/{project_id}/documentation/non_existent_doc_id"
        )
        assert not_found_res.status_code == 404
