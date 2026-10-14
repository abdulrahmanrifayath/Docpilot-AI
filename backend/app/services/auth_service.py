"""
Authentication and User Management Service
Handles registration, login credentials verification, JWT token issuance, and user lookup.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationException, ValidationException
from app.core.security import create_access_token, hash_password, verify_password
from app.models.project import User, generate_uuid
from app.schemas.user import AuthResponse, UserLoginRequest, UserRegisterRequest, UserResponse


class AuthService:
    """Service class for user registration, authentication, and JWT lifecycle."""

    async def register(
        self,
        payload: UserRegisterRequest,
        db: AsyncSession,
    ) -> AuthResponse:
        """Register a new user account with hashed password and return access token."""
        email = payload.email.strip().lower()
        if not email or "@" not in email:
            raise ValidationException("Please provide a valid email address.")

        if len(payload.password) < 6:
            raise ValidationException("Password must be at least 6 characters long.")

        # Check existing user
        existing_result = await db.execute(select(User).where(User.email == email))
        if existing_result.scalar_one_or_none():
            raise ValidationException(f"Email '{payload.email}' is already registered.")

        # Hash password and create user
        hashed_pw = hash_password(payload.password)
        new_user = User(
            id=generate_uuid(),
            email=email,
            password_hash=hashed_pw,
            full_name=payload.full_name.strip() if payload.full_name else None,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Generate JWT access token
        access_token = create_access_token(
            subject=new_user.id,
            email=new_user.email,
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(new_user),
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(
        self,
        payload: UserLoginRequest,
        db: AsyncSession,
    ) -> AuthResponse:
        """Verify user credentials and issue signed JWT access token."""
        email = payload.email.strip().lower()

        # Query user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationException("Invalid email or password.")

        # Verify password hash
        if not verify_password(payload.password, user.password_hash):
            raise AuthenticationException("Invalid email or password.")

        # Issue token
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_user_by_id(
        self,
        user_id: str,
        db: AsyncSession,
    ) -> Optional[User]:
        """Fetch user by primary key ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self,
        email: str,
        db: AsyncSession,
    ) -> Optional[User]:
        """Fetch user by unique email."""
        norm_email = email.strip().lower()
        result = await db.execute(select(User).where(User.email == norm_email))
        return result.scalar_one_or_none()


auth_service = AuthService()
