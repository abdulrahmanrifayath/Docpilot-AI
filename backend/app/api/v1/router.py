from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, system, projects

api_router = APIRouter()

# Include health at both root /health and /api/v1/health for convenience
api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(projects.router)
