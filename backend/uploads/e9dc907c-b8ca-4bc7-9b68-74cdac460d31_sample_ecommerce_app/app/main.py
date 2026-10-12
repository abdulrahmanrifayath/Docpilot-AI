from fastapi import FastAPI, Depends, HTTPException
from app.models.user import User
from app.models.order import Order
from app.services.auth import AuthService
from app.services.payment import PaymentService

app = FastAPI(title="ECommerce Engine", version="2.0.0")

@app.post("/api/auth/login")
async def login(username: str, password: str):
    """Authenticate user and return JWT bearer token."""
    return {"token": "jwt_sample_token", "user": username}

@app.get("/api/products")
async def list_products(category: str = "all", limit: int = 20):
    """Retrieve catalog of available products."""
    return [{"id": 1, "name": "Laptop Pro", "price": 1299.99}]

@app.post("/api/orders")
async def create_order(product_id: int, quantity: int, user: str = Depends(AuthService.get_current_user)):
    """Submit and process a customer order."""
    result = PaymentService.process_charge(user, 1299.99 * quantity)
    return {"order_id": 101, "status": "confirmed"}
