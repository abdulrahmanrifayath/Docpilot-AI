"""
DocPilot AI Authentication API Endpoints
Provides registration, login, and profile introspection routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.project import User
from app.schemas.user import AuthResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user account with hashed password and issue JWT token."""
    return await auth_service.register(payload=payload, db=db)


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with email and password and receive a signed JWT access token."""
    return await auth_service.login(payload=payload, db=db)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve profile and identity details of currently authenticated user."""
    return UserResponse.model_validate(current_user)
