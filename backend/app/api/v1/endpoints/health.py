from fastapi import APIRouter
from backend.app.schemas.system import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the overall operational health of the DocPilot AI service.",
)
def get_health() -> HealthResponse:
    return HealthResponse(status="healthy", service="docpilot-ai")
