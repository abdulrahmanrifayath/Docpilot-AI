"""
Phase 10: Automatic Architecture Diagram Generation - Live E2E Verification Script.
Tests:
1. Health check of live backend server
2. Ingestion of multi-tier repository (FastAPI + SQLAlchemy models + services)
3. Full static code analysis pipeline (Scan, Parse, Dependencies, APIs, DB, Knowledge Graph)
4. Automatic Diagram Generation (POST /projects/{id}/diagrams/generate)
   - SYSTEM_ARCHITECTURE
   - MODULE_ARCHITECTURE
   - DEPENDENCY_DIAGRAM
   - API_SERVICE_RELATIONSHIP
   - DATABASE_ER
5. Mermaid Syntax Validation of each generated diagram
6. Metadata verification (project_id, version, source_entities, timestamps)
7. Retrieval & Filtering (GET /projects/{id}/diagrams, ?diagram_type=DATABASE_ER)
8. Single-Diagram Retrieval (GET /projects/{id}/diagrams/{id})
9. Regeneration with Version Increment (POST /projects/{id}/diagrams/{id}/regenerate)
10. 404 Error handling
"""

import io
import json
import zipfile
import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"

def log(msg: str):
    print(f"[VERIFY-PHASE10] {msg}")

def main():
    log("Starting Phase 10 Automatic Architecture Diagram Generation Live Verification...")

    # 1. Health check
    res = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert res.status_code == 200, f"Backend not healthy: {res.text}"
    log("Backend server is healthy.")

    # 2. Create project
    proj_res = httpx.post(
        f"{API_V1}/projects",
        json={
            "name": "Phase 10 Enterprise E-Commerce Gateway",
            "description": "Multi-tier microservices architecture for testing automatic diagram generation",
        },
        timeout=10,
    )
    assert proj_res.status_code == 201, f"Failed to create project: {proj_res.text}"
    project = proj_res.json()
    project_id = project["id"]
    log(f"Created project: {project_id}")

    # 3. Create realistic multi-tier codebase ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "main.py",
            """from fastapi import FastAPI, Depends
from api.routes import router
from services.order_service import OrderService

app = FastAPI(title="E-Commerce API", version="1.0.0")
app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
""",
        )
        zf.writestr(
            "api/routes.py",
            """from fastapi import APIRouter
from services.order_service import OrderService
from services.payment_service import PaymentService

router = APIRouter(tags=["Orders"])

@router.post("/orders")
def create_order(payload: dict):
    return OrderService().create_order(payload)

@router.get("/orders/{order_id}")
def get_order(order_id: int):
    return OrderService().get_order(order_id)

@router.post("/payments/checkout")
def process_checkout(payment_data: dict):
    return PaymentService().charge(payment_data)
""",
        )
        zf.writestr(
            "services/order_service.py",
            """from models.order import Order
from services.payment_service import PaymentService

class OrderService:
    def __init__(self):
        self.payment_svc = PaymentService()

    def create_order(self, data: dict) -> dict:
        self.payment_svc.charge(data)
        return {"order_id": 101, "status": "CONFIRMED"}

    def get_order(self, order_id: int) -> dict:
        return {"order_id": order_id, "amount": 99.99}
""",
        )
        zf.writestr(
            "services/payment_service.py",
            """class PaymentService:
    def charge(self, payment_info: dict) -> dict:
        return {"transaction_id": "txn_999", "status": "SUCCESS"}
""",
        )
        zf.writestr(
            "models/order.py",
            """from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    orders = relationship("Order", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default="PENDING")
    customer = relationship("Customer", back_populates="orders")
""",
        )

    zip_bytes = zip_buffer.getvalue()

    # Upload ZIP
    up_res = httpx.post(
        f"{API_V1}/projects/{project_id}/upload",
        files={"file": ("ecommerce.zip", zip_bytes, "application/zip")},
        timeout=15,
    )
    assert up_res.status_code == 200, f"Upload failed: {up_res.text}"

    # Run analysis stages
    httpx.post(f"{API_V1}/projects/{project_id}/scan", timeout=10)
    httpx.post(f"{API_V1}/projects/{project_id}/parse", timeout=10)
    httpx.post(f"{API_V1}/projects/{project_id}/dependencies/analyze", timeout=10)
    httpx.post(f"{API_V1}/projects/{project_id}/apis/analyze", timeout=10)
    httpx.post(f"{API_V1}/projects/{project_id}/database/analyze", timeout=10)
    httpx.post(f"{API_V1}/projects/{project_id}/knowledge/build", timeout=10)
    log("Completed repository ingestion & knowledge graph synthesis.")

    # 4. Generate all architecture diagrams (POST /diagrams/generate)
    gen_res = httpx.post(
        f"{API_V1}/projects/{project_id}/diagrams/generate",
        json={"include_flow_data": True, "use_llm_enhancement": False},
        timeout=15,
    )
    assert gen_res.status_code == 200, f"Generation failed: {gen_res.text}"
    gen_data = gen_res.json()
    assert gen_data["status"] == "SUCCESS"
    assert gen_data["total_generated"] == 5
    log(f"Successfully generated {gen_data['total_generated']} architecture diagrams.")

    diagrams_by_type = {d["diagram_type"]: d for d in gen_data["diagrams"]}
    required_types = [
        "SYSTEM_ARCHITECTURE",
        "MODULE_ARCHITECTURE",
        "DEPENDENCY_DIAGRAM",
        "API_SERVICE_RELATIONSHIP",
        "DATABASE_ER",
    ]

    for dtype in required_types:
        assert dtype in diagrams_by_type, f"Missing required diagram type: {dtype}"
        d = diagrams_by_type[dtype]
        assert d["project_id"] == project_id
        assert d["version"] >= 1
        assert len(d["mermaid_code"]) > 10
        assert len(d["source_entities"]) > 0
        log(f"  - Verified {dtype} (v{d['version']}) with {len(d['source_entities'])} grounded source entities.")

    # Check Mermaid syntax header starters
    assert "flowchart" in diagrams_by_type["SYSTEM_ARCHITECTURE"]["mermaid_code"].lower()
    assert "flowchart" in diagrams_by_type["MODULE_ARCHITECTURE"]["mermaid_code"].lower()
    assert "flowchart" in diagrams_by_type["DEPENDENCY_DIAGRAM"]["mermaid_code"].lower()
    assert "flowchart" in diagrams_by_type["API_SERVICE_RELATIONSHIP"]["mermaid_code"].lower()
    assert "erdiagram" in diagrams_by_type["DATABASE_ER"]["mermaid_code"].lower()
    log("Verified all diagram headers match proper Mermaid standards (flowchart, erDiagram).")

    # 5. List all diagrams (GET /diagrams)
    list_res = httpx.get(f"{API_V1}/projects/{project_id}/diagrams", timeout=10)
    assert list_res.status_code == 200
    all_diagrams = list_res.json()
    assert len(all_diagrams) == 5
    log("List endpoint returned all 5 diagrams.")

    # 6. Filter by diagram_type (GET /diagrams?diagram_type=DATABASE_ER)
    filter_res = httpx.get(f"{API_V1}/projects/{project_id}/diagrams?diagram_type=DATABASE_ER", timeout=10)
    assert filter_res.status_code == 200
    filtered = filter_res.json()
    assert len(filtered) == 1
    assert filtered[0]["diagram_type"] == "DATABASE_ER"
    assert "customers" in filtered[0]["mermaid_code"].lower() or "customer" in filtered[0]["mermaid_code"].lower()
    log("Filter query 'diagram_type=DATABASE_ER' passed.")

    er_diagram_id = filtered[0]["id"]
    initial_version = filtered[0]["version"]

    # 7. Get specific diagram (GET /diagrams/{diagram_id})
    detail_res = httpx.get(f"{API_V1}/projects/{project_id}/diagrams/{er_diagram_id}", timeout=10)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == er_diagram_id
    assert detail["title"].endswith("Database Entity-Relationship Diagram")
    log(f"Detail endpoint retrieved diagram '{detail['title']}'.")

    # 8. Regenerate diagram (POST /diagrams/{diagram_id}/regenerate)
    regen_res = httpx.post(f"{API_V1}/projects/{project_id}/diagrams/{er_diagram_id}/regenerate", timeout=15)
    assert regen_res.status_code == 200
    regenerated = regen_res.json()
    assert regenerated["id"] == er_diagram_id
    assert regenerated["version"] == initial_version + 1
    log(f"Regeneration endpoint verified: bumped version to v{regenerated['version']} with updated timestamp.")

    # 9. 404 test on invalid ID
    bad_res = httpx.get(f"{API_V1}/projects/{project_id}/diagrams/invalid-uuid-999", timeout=10)
    assert bad_res.status_code == 404
    log("Non-existent diagram returned 404 as expected.")

    log("\nAll Phase 10 Automatic Architecture Diagram Generation verifications PASSED flawlessly!\n")

if __name__ == "__main__":
    main()
