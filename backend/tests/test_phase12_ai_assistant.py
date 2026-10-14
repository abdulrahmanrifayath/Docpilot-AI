import io
import os
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import init_db


@pytest.mark.asyncio
async def test_phase12_repository_aware_ai_assistant_e2e():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a rich sample FastAPI project with Auth, UserService, OrderService, and Payment
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "main.py",
                """from fastapi import FastAPI, Depends, HTTPException
from routers.auth import auth_router
from routers.orders import order_router
from routers.payments import payment_router

app = FastAPI(title="E-Commerce Core API", version="1.0.0")

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(payment_router, prefix="/api/v1/payments", tags=["Payments"])

@app.get("/health")
def health():
    return {"status": "healthy"}
""",
            )
            zf.writestr(
                "routers/auth.py",
                """from fastapi import APIRouter
from services.auth_service import AuthService
from models.models import User

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

@payment_router.post("/charge")
def process_payment(charge_data: dict):
    return PaymentService().charge(charge_data)
""",
            )
            zf.writestr(
                "services/auth_service.py",
                """from models.models import User

class AuthService:
    def authenticate(self, username: str, password: str):
        # Authenticate user credentials and issue JWT token
        return {"access_token": "jwt_sample_token", "token_type": "bearer"}

    def register_user(self, data: dict):
        # Register a new user in database
        return {"id": 1, "username": data["username"]}
""",
            )
            zf.writestr(
                "services/order_service.py",
                """from models.models import Order
from services.payment_service import PaymentService

class OrderService:
    def checkout(self, payload: dict):
        # Coordinates order creation and triggers payment charge
        PaymentService().charge(payload)
        return {"order_id": 501, "status": "CONFIRMED"}
""",
            )
            zf.writestr(
                "services/payment_service.py",
                """from models.models import PaymentTransaction

class PaymentService:
    def charge(self, payment_info: dict):
        # Connects to payment gateway and records transaction
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

        # 2. Create Project A
        create_res = await client.post(
            "/api/v1/projects",
            json={"name": "E-Commerce Microservice", "source_type": "zip"},
        )
        assert create_res.status_code == 201
        project_a = create_res.json()
        proj_a_id = project_a["id"]

        # Upload and analyze
        files = {"file": ("repo.zip", zip_bytes, "application/zip")}
        up_res = await client.post(f"/api/v1/projects/{proj_a_id}/upload", files=files)
        assert up_res.status_code == 200

        # Run pipeline stages
        await client.post(f"/api/v1/projects/{proj_a_id}/scan")
        await client.post(f"/api/v1/projects/{proj_a_id}/parse")
        await client.post(f"/api/v1/projects/{proj_a_id}/dependencies/analyze")
        await client.post(f"/api/v1/projects/{proj_a_id}/apis/analyze")
        await client.post(f"/api/v1/projects/{proj_a_id}/database/analyze")
        await client.post(f"/api/v1/projects/{proj_a_id}/knowledge/build")
        await client.post(f"/api/v1/projects/{proj_a_id}/sequences/generate")

        # 3. Test Question 1: "Explain authentication."
        q1_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "Explain authentication."},
        )
        assert q1_res.status_code == 200, q1_res.text
        q1_data = q1_res.json()
        assert q1_data["role"] == "assistant"
        assert q1_data["project_id"] == proj_a_id
        assert q1_data["intent"] == "AUTHENTICATION"
        assert len(q1_data["sources"]) > 0
        assert any("auth" in s["file"].lower() or "models" in s["file"].lower() for s in q1_data["sources"])
        assert "High Confidence" in q1_data["confidence"] or "Confidence" in q1_data["confidence"]
        assert len(q1_data["relevant_components"]) > 0

        # 4. Test Question 2: "How does login work?"
        q2_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "How does login work?"},
        )
        assert q2_res.status_code == 200
        q2_data = q2_res.json()
        assert "login" in q2_data["content"].lower() or "auth" in q2_data["content"].lower()
        assert len(q2_data["sources"]) > 0

        # 5. Test Question 3: "Where is payment processing implemented?"
        q3_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "Where is payment processing implemented?"},
        )
        assert q3_res.status_code == 200
        q3_data = q3_res.json()
        assert any("payment" in s["file"].lower() for s in q3_data["sources"])

        # 6. Test Question 4: "What happens when an order is created?"
        q4_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "What happens when an order is created?"},
        )
        assert q4_res.status_code == 200
        q4_data = q4_res.json()
        assert any("order" in s["file"].lower() for s in q4_data["sources"])

        # 7. Test Question 5: "Explain the project architecture."
        q5_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "Explain the project architecture."},
        )
        assert q5_res.status_code == 200
        q5_data = q5_res.json()
        assert "architecture" in q5_data["content"].lower() or "component" in q5_data["content"].lower()

        # 8. Test Question 6: Negative Knowledge Constraint Test
        # Asking about a technology or feature that DOES NOT EXIST in the repo (e.g. Stripe webhook handler)
        q6_res = await client.post(
            f"/api/v1/projects/{proj_a_id}/chat",
            json={"content": "Where is the Stripe webhook handler and webhook signature verification implemented?"},
        )
        assert q6_res.status_code == 200
        q6_data = q6_res.json()
        # Must clearly state insufficient evidence / not found, and not invent false code
        assert (
            "insufficient" in q6_data["content"].lower()
            or "not found" in q6_data["content"].lower()
            or "does not appear to implement" in q6_data["content"].lower()
        )

        # 9. Test Chat History retrieval: GET /api/v1/projects/{project_id}/chat/history
        hist_res = await client.get(f"/api/v1/projects/{proj_a_id}/chat/history")
        assert hist_res.status_code == 200
        history = hist_res.json()
        # We sent 6 questions, so 6 user messages + 6 assistant messages = 12 total messages
        assert len(history) == 12
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

        # 10. Test Cross-Project Isolation: Project B must have 0 messages and cannot access Project A's history
        create_b = await client.post(
            "/api/v1/projects",
            json={"name": "Separate Project B", "source_type": "zip"},
        )
        proj_b_id = create_b.json()["id"]
        hist_b = await client.get(f"/api/v1/projects/{proj_b_id}/chat/history")
        assert hist_b.status_code == 200
        assert len(hist_b.json()) == 0, "Cross-project leakage: Project B should have empty chat history!"

        # 11. Test Clear History: DELETE /api/v1/projects/{project_id}/chat/history
        del_res = await client.delete(f"/api/v1/projects/{proj_a_id}/chat/history")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["status"] == "cleared"
        assert del_data["deleted_count"] >= 12

        # Verify history is now empty for Project A
        hist_a_cleared = await client.get(f"/api/v1/projects/{proj_a_id}/chat/history")
        assert len(hist_a_cleared.json()) == 0
