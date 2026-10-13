from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import DocPilotException
from app.core.logging import logger
from app.database.session import init_db

# Routers
from app.api.v1.system import router as v1_system_router
from app.api.v1.projects import router as v1_projects_router
from app.api.repositories import router as repositories_router
from app.api.documentation import router as documentation_router
from app.api.diagrams import router as diagrams_router
from app.api.chat import router as chat_router
from app.api.sync import router as sync_router
from app.api.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DocPilot AI Database...")
    await init_db()
    logger.info("DocPilot AI Database tables initialized.")
    logger.info(f"DocPilot AI Application '{settings.APP_NAME}' ({settings.APP_ENV}) started.")
    yield
    logger.info("DocPilot AI Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent Software Documentation and Repository Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(DocPilotException)
async def docpilot_exception_handler(request: Request, exc: DocPilotException) -> JSONResponse:
    logger.warning(f"DocPilotException [{exc.code}] on {request.method} {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload or query parameters.",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.info(f"HTTP exception {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    **exc.detail,
                }
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing the request.",
            }
        },
    )


# Health Check Endpoint (as required in prompt)
@app.get("/health", tags=["Health"])
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": "docpilot-ai",
    }


# API Version 1 Routers
app.include_router(v1_system_router, prefix="/api/v1")
app.include_router(v1_projects_router, prefix="/api/v1")

# Additional modules under /api/v1 and /api
app.include_router(documentation_router, prefix="/api/v1")
app.include_router(diagrams_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")

# Legacy/compat routes
app.include_router(repositories_router, prefix="/api")
app.include_router(documentation_router, prefix="/api")
app.include_router(diagrams_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "docpilot-ai",
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "documentation_url": "/docs",
        "health_url": "/health",
        "api_v1_status": "/api/v1/system/status",
    }
