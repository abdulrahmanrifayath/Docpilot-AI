from fastapi import APIRouter
from app.core.config import settings
from app.database.session import check_db_health
from app.ai.llm_provider import llm_provider
from app.schemas.project import SystemStatusResponse

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """
    Returns application status, database status, AI provider configuration,
    and vector database status without exposing secrets.
    """
    db_health = await check_db_health()

    return SystemStatusResponse(
        status="operational" if db_health.get("status") == "connected" else "degraded",
        application={
            "status": "running",
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        },
        database=db_health,
        ai_provider={
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "is_configured": llm_provider.is_configured(),
        },
        vector_database={
            "type": settings.VECTOR_STORE_TYPE,
            "status": "ready" if settings.VECTOR_STORE_DIR.exists() else "uninitialized",
        },
    )
