from typing import Any, AsyncGenerator, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

engine_args: Dict[str, Any] = {
    "echo": False,
    "future": True,
}

if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **engine_args)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_health() -> Dict[str, Any]:
    """Checks database connectivity and type for system status reporting."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        return {
            "status": "connected",
            "type": db_type,
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "type": "unknown",
        }
