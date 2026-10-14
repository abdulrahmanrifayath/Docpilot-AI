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
        if "sqlite" in settings.DATABASE_URL:
            try:
                res = await conn.execute(text("PRAGMA table_info(projects)"))
                existing_cols = {row[1] for row in res.fetchall()}
                if "infrastructure" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN infrastructure JSON DEFAULT '[]'"))

                # Documents table Phase 9 columns migration
                d_res = await conn.execute(text("PRAGMA table_info(documents)"))
                d_cols = {row[1] for row in d_res.fetchall()}
                if "target_path" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN target_path VARCHAR(500)"))
                if "target_entity_id" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN target_entity_id VARCHAR(100)"))
                if "source_entities" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN source_entities JSON DEFAULT '[]'"))
                if "model" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN model VARCHAR(100) DEFAULT 'gpt-4o-mini'"))
                if "version" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1"))
                if "generated_at" not in d_cols and "id" in d_cols:
                    await conn.execute(text("ALTER TABLE documents ADD COLUMN generated_at TIMESTAMP"))

                # Diagrams table Phase 10 columns migration
                diag_res = await conn.execute(text("PRAGMA table_info(diagrams)"))
                diag_cols = {row[1] for row in diag_res.fetchall()}
                if "description" not in diag_cols and "id" in diag_cols:
                    await conn.execute(text("ALTER TABLE diagrams ADD COLUMN description VARCHAR(500)"))
                if "source_entities" not in diag_cols and "id" in diag_cols:
                    await conn.execute(text("ALTER TABLE diagrams ADD COLUMN source_entities JSON DEFAULT '[]'"))
                if "version" not in diag_cols and "id" in diag_cols:
                    await conn.execute(text("ALTER TABLE diagrams ADD COLUMN version INTEGER DEFAULT 1"))
                if "metadata" not in diag_cols and "id" in diag_cols:
                    await conn.execute(text("ALTER TABLE diagrams ADD COLUMN metadata JSON DEFAULT '{}'"))

                # Chat Messages table Phase 12 columns migration
                c_res = await conn.execute(text("PRAGMA table_info(chat_messages)"))
                c_cols = {row[1] for row in c_res.fetchall()}
                if "confidence" not in c_cols and "id" in c_cols:
                    await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN confidence VARCHAR(200)"))
                if "intent" not in c_cols and "id" in c_cols:
                    await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN intent VARCHAR(50)"))
                if "relevant_components" not in c_cols and "id" in c_cols:
                    await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN relevant_components JSON DEFAULT '[]'"))
            except Exception:
                pass



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
