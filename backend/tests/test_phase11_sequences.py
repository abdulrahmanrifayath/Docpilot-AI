import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import init_db
from app.services.diagram_service import validate_mermaid_syntax


@pytest.mark.asyncio
async def test_sequence_diagram_generation_pipeline_e2e():
    """Verify end-to-end automatic sequence diagram generation for key application flows (auth, registration, orders, payments)."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 11 FastAPI Auth & E-Commerce Flow",
                "description": "Comprehensive test project for sequence diagram flows",
            },
        )
        assert create_res.status_code == 201
        proj = create_res.json()
        project_id = proj["id"]

        # 2. Build multi-flow repository ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "main.py",
                """from fastapi import FastAPI, Depends
from routers.auth import auth_router
from routers.orders import order_router
from routers.payments import payment_router

app = FastAPI(title="Sequence Flow API")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(order_router, prefix="/api/v1/orders")
app.include_router(payment_router, prefix="/api/v1/payments")
""",
            )
            zf.writestr(
                "routers/auth.py",
                """from fastapi import APIRouter
from services.auth_service import AuthService

auth_router = APIRouter()

@auth_router.post("/login")
def login(credentials: dict):
    return AuthService().authenticate(credentials["username"], credentials["password"])

@auth_router.post("/register")
def register(user_data: dict):
    return AuthService().register_user(user_data)
""",
            )
            zf.writestr(
                "routers/orders.py",
                """from fastapi import APIRouter
from services.order_service import OrderService

order_router = APIRouter()

@order_router.post("")
def create_order(order_payload: dict):
    return OrderService().checkout(order_payload)
""",
            )
            zf.writestr(
                "routers/payments.py",
                """from fastapi import APIRouter
from services.payment_service import PaymentService

payment_router = APIRouter()

@payment_router.post("/checkout")
def process_payment(charge_data: dict):
    return PaymentService().charge(charge_data)
""",
            )
            zf.writestr(
                "services/auth_service.py",
                """from models.models import User

class AuthService:
    def authenticate(self, username: str, password: str):
        return {"access_token": "jwt_token_sample", "token_type": "bearer"}

    def register_user(self, data: dict):
        return {"id": 1, "username": data["username"]}
""",
            )
            zf.writestr(
                "services/order_service.py",
                """from models.models import Order
from services.payment_service import PaymentService

class OrderService:
    def checkout(self, payload: dict):
        PaymentService().charge(payload)
        return {"order_id": 501, "status": "CONFIRMED"}
""",
            )
            zf.writestr(
                "services/payment_service.py",
                """from models.models import PaymentTransaction

class PaymentService:
    def charge(self, payment_info: dict):
        return {"transaction_id": "txn_888", "status": "APPROVED"}
""",
            )
            zf.writestr(
                "models/models.py",
                """from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    hashed_password = Column(String(255))

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total = Column(Float)

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(Float)
""",
            )

        zip_bytes = zip_buffer.getvalue()

        # Upload and analyze
        files = {"file": ("repo.zip", zip_bytes, "application/zip")}
        up_res = await client.post(f"/api/v1/projects/{project_id}/upload", files=files)
        assert up_res.status_code == 200

        # Run pipeline stages
        await client.post(f"/api/v1/projects/{project_id}/scan")
        await client.post(f"/api/v1/projects/{project_id}/parse")
        await client.post(f"/api/v1/projects/{project_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{project_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{project_id}/database/analyze")
        await client.post(f"/api/v1/projects/{project_id}/knowledge/build")

        # 3. Generate Sequence Diagrams (POST /api/v1/projects/{project_id}/sequences/generate)
        gen_res = await client.post(f"/api/v1/projects/{project_id}/sequences/generate", json={})
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data["status"] == "SUCCESS"
        assert gen_data["total_generated"] >= 4

        categories = {s["flow_category"] for s in gen_data["sequences"]}
        assert "AUTHENTICATION" in categories
        assert "REGISTRATION" in categories
        assert "ORDER" in categories
        assert "PAYMENT" in categories

        # 4. Verify each generated sequence diagram
        for seq in gen_data["sequences"]:
            assert seq["project_id"] == project_id
            assert seq["version"] == 1
            assert seq["is_guaranteed"] is False
            assert "Static analysis-based interaction flow" in seq["execution_type"]
            assert 0.70 <= seq["overall_confidence"] <= 1.0
            assert len(seq["steps"]) >= 4
            assert len(seq["involved_components"]) >= 3

            # Check Mermaid syntax
            mermaid = seq["mermaid_code"]
            assert mermaid.startswith("sequenceDiagram")
            assert "Static analysis-based interaction flow" in mermaid
            is_valid, err = validate_mermaid_syntax(mermaid)
            assert is_valid is True, f"Sequence {seq['name']} failed Mermaid validation: {err}"

        # 5. List Sequences (GET /api/v1/projects/{project_id}/sequences)
        list_res = await client.get(f"/api/v1/projects/{project_id}/sequences")
        assert list_res.status_code == 200
        all_seqs = list_res.json()
        assert len(all_seqs) >= 4

        # 6. Filter by flow_category (GET /api/v1/projects/{project_id}/sequences?flow_category=AUTHENTICATION)
        filter_res = await client.get(f"/api/v1/projects/{project_id}/sequences?flow_category=AUTHENTICATION")
        assert filter_res.status_code == 200
        filtered = filter_res.json()
        assert len(filtered) == 1
        auth_seq = filtered[0]
        assert auth_seq["flow_category"] == "AUTHENTICATION"
        assert "login" in auth_seq["trigger_endpoint"].lower()

        target_id = auth_seq["id"]

        # 7. Get Sequence Detail (GET /api/v1/projects/{project_id}/sequences/{sequence_id})
        detail_res = await client.get(f"/api/v1/projects/{project_id}/sequences/{target_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == target_id
        assert detail["flow_category"] == "AUTHENTICATION"
        assert len(detail["steps"]) >= 4

        # 8. Regenerate Sequence (POST /api/v1/projects/{project_id}/sequences/{sequence_id}/regenerate)
        regen_res = await client.post(f"/api/v1/projects/{project_id}/sequences/{target_id}/regenerate")
        assert regen_res.status_code == 200
        regenerated = regen_res.json()
        assert regenerated["id"] == target_id
        assert regenerated["version"] == 2  # Version incremented to v2

        # 9. 404 handling
        bad_res = await client.get(f"/api/v1/projects/{project_id}/sequences/invalid-seq-id")
        assert bad_res.status_code == 404
