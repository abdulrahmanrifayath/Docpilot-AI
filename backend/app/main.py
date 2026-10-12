import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.session import init_db
from app.api.repositories import router as repositories_router
from app.api.documentation import router as documentation_router
from app.api.diagrams import router as diagrams_router
from app.api.chat import router as chat_router
from app.api.sync import router as sync_router
from app.api.settings import router as settings_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("docpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing DocPilot AI Database...")
    await init_db()
    logger.info("DocPilot AI Engine initialized and ready.")
    yield
    logger.info("DocPilot AI shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Intelligent Software Documentation and Repository Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api
app.include_router(repositories_router, prefix="/api")
app.include_router(documentation_router, prefix="/api")
app.include_router(diagrams_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} — Intelligent Software Documentation Platform",
        "docs_url": "/docs",
        "health_url": "/health",
    }
