import os
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.system import (
    SystemStatusResponse,
    DatabaseStatus,
    AIProviderStatus,
    VectorDBStatus,
)


class SystemService:
    @staticmethod
    def check_database(db: Session) -> DatabaseStatus:
        engine_type = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
        try:
            db.execute(text("SELECT 1"))
            return DatabaseStatus(
                status="connected",
                engine=engine_type,
                message="Database connection verified successfully.",
            )
        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return DatabaseStatus(
                status="error",
                engine=engine_type,
                message=f"Database unreachable: {str(e)}",
            )

    @staticmethod
    def check_ai_provider() -> AIProviderStatus:
        has_key = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
        if has_key:
            message = "AI provider configured and ready."
        else:
            message = "API key not configured. Please set OPENAI_API_KEY in .env or Settings."

        return AIProviderStatus(
            configured=has_key,
            provider="openai",
            model=settings.OPENAI_MODEL,
            embedding_model=settings.EMBEDDING_MODEL,
            message=message,
        )

    @staticmethod
    def check_vector_db() -> VectorDBStatus:
        storage_path = settings.CHROMA_PERSIST_DIRECTORY
        try:
            # Ensure storage directory can be created or accessed
            os.makedirs(storage_path, exist_ok=True)
            return VectorDBStatus(
                status="ready",
                provider="chromadb",
                storage_path=storage_path,
                message="Vector storage directory ready.",
            )
        except Exception as e:
            logger.error(f"Vector DB storage check error: {e}")
            return VectorDBStatus(
                status="error",
                provider="chromadb",
                storage_path=storage_path,
                message=f"Storage directory error: {str(e)}",
            )

    @classmethod
    def get_system_status(cls, db: Session) -> SystemStatusResponse:
        db_status = cls.check_database(db)
        ai_status = cls.check_ai_provider()
        vdb_status = cls.check_vector_db()

        # Overall status calculation
        if db_status.status == "error":
            overall_status = "unhealthy"
        elif not ai_status.configured or vdb_status.status == "error":
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return SystemStatusResponse(
            status=overall_status,
            environment=settings.ENVIRONMENT,
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            database=db_status,
            ai_provider=ai_status,
            vector_db=vdb_status,
        )
