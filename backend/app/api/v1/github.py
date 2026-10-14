"""
GitHub Integration API Routes (Phase 15).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.project import (
    GitHubValidateRequest,
    GitHubValidateResponse,
    GitHubStatusResponse,
    GitHubRefreshRequest,
    GitHubRefreshResponse,
)
from app.services.github_service import github_service

router = APIRouter(prefix="/github", tags=["GitHub"])


@router.post("/validate", response_model=GitHubValidateResponse)
async def validate_github_repository(
    payload: GitHubValidateRequest,
) -> GitHubValidateResponse:
    """
    Validate public or private GitHub repository access and retrieve metadata.
    Supports branch detection, branch verification, commit tracking, and rate limit reporting.
    Tokens are accepted optionally and used strictly in memory (never logged or stored in plain text).
    """
    return await github_service.validate_repository(
        url=payload.url,
        token=payload.token,
        branch=payload.branch,
    )
