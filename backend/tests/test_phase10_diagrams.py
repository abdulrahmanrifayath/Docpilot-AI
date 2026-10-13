import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import init_db
from app.services.diagram_service import validate_mermaid_syntax


def test_mermaid_syntax_validation():
    """Verify robust Mermaid syntax validation logic."""
    # 1. Valid flowchart
    valid_flow = """flowchart TB
    subgraph Client["Client Tier"]
        User["Browser"]
    end
    subgraph API["Backend API"]
        GW["Gateway"]
    end
    User --> GW
"""
    is_valid, err = validate_mermaid_syntax(valid_flow)
    assert is_valid is True
    assert err is None

    # 2. Valid ER diagram
    valid_er = """erDiagram
    USER ||--o{ ORDER : "places"
    USER {
        int id PK
        string email
    }
    ORDER {
        int id PK
        int user_id FK
    }
"""
    is_valid, err = validate_mermaid_syntax(valid_er)
    assert is_valid is True

    # 3. Invalid: Unbalanced brackets
    invalid_brackets = """flowchart TB
    A["Unclosed label --> B["Target"]
"""
    is_valid, err = validate_mermaid_syntax(invalid_brackets)
    assert is_valid is False
    assert "square brackets" in err.lower()

    # 4. Invalid: Unbalanced subgraphs
    invalid_subgraph = """flowchart TB
    subgraph A["Module A"]
        Node1["Item 1"]
"""
    is_valid, err = validate_mermaid_syntax(invalid_subgraph)
    assert is_valid is False
    assert "unbalanced subgraphs" in err.lower()

    # 5. Invalid: Empty content
    is_valid, err = validate_mermaid_syntax("   ")
    assert is_valid is False
    assert "empty" in err.lower()


@pytest.mark.asyncio
async def test_diagram_generation_pipeline_e2e():
    """Verify full end-to-end architecture diagram generation pipeline across all 5 diagram types."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 10 E2E Microservices",
                "description": "Multi-tier test project for architecture diagrams",
            },
        )
        assert create_res.status_code == 201
        proj = create_res.json()
        project_id = proj["id"]

        # 2. Create in-memory sample repository ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "main.py",
                """from fastapi import FastAPI, Depends
from services.order_service import OrderService
from models.order import Order

app = FastAPI(title="Payment API")

@app.post("/orders")
def create_order(order: dict):
    return OrderService().process_order(order)

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    return OrderService().get_order(order_id)
""",
            )
            zf.writestr(
                "services/order_service.py",
                """from models.order import Order

class OrderService:
    def process_order(self, order_data: dict) -> dict:
        return {"status": "created"}

    def get_order(self, order_id: int) -> dict:
        return {"id": order_id}
""",
            )
            zf.writestr(
                "models/order.py",
                """from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
""",
            )

        zip_bytes = zip_buffer.getvalue()

        # Upload and analyze
        files = {"file": ("repo.zip", zip_bytes, "application/zip")}
        up_res = await client.post(f"/api/v1/projects/{project_id}/upload", files=files)
        assert up_res.status_code == 200

        # Run Scan, Parse, Dependencies, APIs, DB, Knowledge Graph
        await client.post(f"/api/v1/projects/{project_id}/scan")
        await client.post(f"/api/v1/projects/{project_id}/parse")
        await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{project_id}/database/analyze")
        await client.post(f"/api/v1/projects/{project_id}/knowledge/build")

        # 3. Generate Diagrams (POST /api/v1/projects/{project_id}/diagrams/generate)
        gen_res = await client.post(
            f"/api/v1/projects/{project_id}/diagrams/generate",
            json={"include_flow_data": True, "use_llm_enhancement": False},
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["status"] == "SUCCESS"
        assert gen_data["total_generated"] == 5

        diagram_types = {d["diagram_type"] for d in gen_data["diagrams"]}
        expected_types = {
            "SYSTEM_ARCHITECTURE",
            "MODULE_ARCHITECTURE",
            "DEPENDENCY_DIAGRAM",
            "API_SERVICE_RELATIONSHIP",
            "DATABASE_ER",
        }
        assert expected_types == diagram_types

        # Verify each generated diagram
        for diag in gen_data["diagrams"]:
            assert diag["project_id"] == project_id
            assert diag["version"] >= 1
            assert len(diag["mermaid_code"]) > 0
            # Validate Mermaid syntax
            is_valid, val_err = validate_mermaid_syntax(diag["mermaid_code"])
            assert is_valid is True, f"Diagram {diag['diagram_type']} failed syntax validation: {val_err}"
            # Grounding check: source_entities should be populated
            assert len(diag["source_entities"]) > 0

        # 4. List diagrams (GET /api/v1/projects/{project_id}/diagrams)
        list_res = await client.get(f"/api/v1/projects/{project_id}/diagrams")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 5

        # 5. Filter by diagram_type (GET /api/v1/projects/{project_id}/diagrams?diagram_type=DATABASE_ER)
        filter_res = await client.get(f"/api/v1/projects/{project_id}/diagrams?diagram_type=DATABASE_ER")
        assert filter_res.status_code == 200
        filtered_items = filter_res.json()
        assert len(filtered_items) == 1
        assert filtered_items[0]["diagram_type"] == "DATABASE_ER"
        assert "erDiagram" in filtered_items[0]["mermaid_code"]

        target_diagram_id = filtered_items[0]["id"]
        initial_ver = filtered_items[0]["version"]

        # 6. Get single diagram (GET /api/v1/projects/{project_id}/diagrams/{diagram_id})
        get_res = await client.get(f"/api/v1/projects/{project_id}/diagrams/{target_diagram_id}")
        assert get_res.status_code == 200
        detail = get_res.json()
        assert detail["id"] == target_diagram_id
        assert detail["diagram_type"] == "DATABASE_ER"

        # 7. Regenerate diagram (POST /api/v1/projects/{project_id}/diagrams/{diagram_id}/regenerate)
        regen_res = await client.post(f"/api/v1/projects/{project_id}/diagrams/{target_diagram_id}/regenerate")
        assert regen_res.status_code == 200
        regenerated = regen_res.json()
        assert regenerated["id"] == target_diagram_id
        assert regenerated["version"] == initial_ver + 1  # Bumping version upon regeneration

        # 8. 404 on non-existent diagram
        bad_res = await client.get(f"/api/v1/projects/{project_id}/diagrams/non-existent-id")
        assert bad_res.status_code == 404
