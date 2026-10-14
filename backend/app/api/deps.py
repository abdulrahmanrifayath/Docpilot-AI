"""
DocPilot AI API Dependencies
Provides database session and JWT authentication dependencies.
"""

from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationException
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.project import User

# Optional HTTPBearer so we can inspect headers without auto-raising 403
bearer_scheme = HTTPBearer(auto_error=False)

DEFAULT_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Strict authentication dependency.
    Requires a valid Bearer JWT token in the Authorization header.
    Used for /auth/me and strictly protected endpoints.
    """
    if not auth or not auth.credentials:
        raise AuthenticationException("Authentication credentials were not provided.")

    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        raise AuthenticationException("Invalid or expired authentication token.")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException("User account not found or has been deactivated.")

    return user


async def get_current_user_or_default(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    User dependency with automatic fallback to system demo user.
    If a valid Bearer token is provided, returns the authenticated user (enforcing user isolation).
    If no token is provided, safely falls back to the default demo user so that existing
    project workflows, automated pipeline steps, and legacy test suites continue uninterrupted.
    """
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if not payload or not payload.get("sub"):
            raise AuthenticationException("Invalid or expired authentication token.")

        user_id = payload["sub"]
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthenticationException("User account not found or has been deactivated.")
        return user

    # No token provided: resolve to default demo user
    result = await db.execute(select(User).where(User.id == DEFAULT_DEMO_USER_ID))
    demo_user = result.scalar_one_or_none()
    if demo_user:
        return demo_user

    # Fallback to any user or first user if demo ID was modified
    any_user_res = await db.execute(select(User).limit(1))
    first_user = any_user_res.scalar_one_or_none()
    if first_user:
        return first_user

    raise AuthenticationException("Authentication required and no default user found.")


async def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Returns authenticated user if token present, else None without raising error."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or not payload.get("sub"):
        return None

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
