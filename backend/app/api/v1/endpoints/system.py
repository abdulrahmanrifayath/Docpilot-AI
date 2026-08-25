from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.system import SystemStatusResponse
from backend.app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Get system and dependencies status",
    description="Returns detailed status for database, AI provider, and vector store without exposing credentials.",
)
def get_system_status(db: Session = Depends(get_db)) -> SystemStatusResponse:
    return SystemService.get_system_status(db)
