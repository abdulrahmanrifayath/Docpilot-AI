from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.exceptions import (
    DocPilotException,
    docpilot_exception_handler,
    generic_exception_handler,
)
from backend.app.database.session import init_db
from backend.app.api.v1.router import api_router
from backend.app.schemas.system import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode...")
    
    # Initialize Database tables
    init_db()
    
    yield
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="DocPilot AI — Intelligent Software Documentation Platform",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Centralized Exception Handlers
    app.add_exception_handler(DocPilotException, docpilot_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Root health endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Root Health Check",
    )
    def root_health() -> HealthResponse:
        return HealthResponse(status="healthy", service="docpilot-ai")

    # API v1 Router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
