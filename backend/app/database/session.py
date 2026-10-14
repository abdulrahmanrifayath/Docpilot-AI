from datetime import datetime, timezone
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
    import app.models.project  # noqa: F401 - Register all models with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in settings.DATABASE_URL:
            try:
                res = await conn.execute(text("PRAGMA table_info(projects)"))
                existing_cols = {row[1] for row in res.fetchall()}
                if "infrastructure" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN infrastructure JSON DEFAULT '[]'"))
                if "last_commit_sha" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN last_commit_sha VARCHAR(100)"))
                if "branch" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN branch VARCHAR(100) DEFAULT 'main'"))
                if "sync_status" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN sync_status VARCHAR(50) DEFAULT 'SYNCED'"))
                if "user_id" not in existing_cols and "id" in existing_cols:
                    await conn.execute(text("ALTER TABLE projects ADD COLUMN user_id VARCHAR(36)"))

                # Ensure default demo user exists for legacy and unauthenticated projects
                from app.core.security import hash_password
                u_check = await conn.execute(text("SELECT id FROM users WHERE email = 'demo@docpilot.ai'"))
                demo_row = u_check.fetchone()
                demo_id = "00000000-0000-0000-0000-000000000001"
                if not demo_row:
                    now_str = datetime.now(timezone.utc).isoformat()
                    demo_pw_hash = hash_password("password123")
                    await conn.execute(
                        text("INSERT INTO users (id, email, password_hash, full_name, created_at, updated_at) VALUES (:id, :email, :pw, :name, :now, :now)"),
                        {"id": demo_id, "email": "demo@docpilot.ai", "pw": demo_pw_hash, "name": "Demo Developer", "now": now_str}
                    )
                else:
                    demo_id = demo_row[0]

                # Backfill any null user_id projects
                await conn.execute(
                    text("UPDATE projects SET user_id = :demo_id WHERE user_id IS NULL"),
                    {"demo_id": demo_id}
                )

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
