import shutil
import uuid
from pathlib import Path
import pytest
from app.database.session import AsyncSessionLocal, init_db
from app.models.repository import Repository, Document, Diagram
from app.services.pipeline_service import pipeline_service
from app.ai.chat_service import chat_service
from sqlalchemy import select


@pytest.mark.asyncio
async def test_full_pipeline_execution():
    await init_db()

    # Create temporary mini codebase
    temp_dir = Path("backend/uploads/test_mini_project")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # File 1: models.py
    (temp_dir / "models.py").write_text(
        '''
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    orders = relationship("Order")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
''',
        encoding="utf-8",
    )

    # File 2: main.py
    (temp_dir / "main.py").write_text(
        '''
from fastapi import FastAPI
from models import Account

app = FastAPI()

@app.get("/api/accounts")
async def get_accounts():
    """Retrieve all accounts in the system."""
    return []

@app.post("/api/accounts")
async def create_account(username: str):
    """Register a new user account."""
    return {"status": "created"}
''',
        encoding="utf-8",
    )

    # File 3: requirements.txt
    (temp_dir / "requirements.txt").write_text("fastapi>=0.100.0\nsqlalchemy>=2.0.0\n", encoding="utf-8")

    # Insert repository record
    repo_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        repo = Repository(
            id=repo_id,
            name="Test Mini Project",
            source_type="local",
            local_path=str(temp_dir),
            status="pending",
            current_step="Queued",
        )
        session.add(repo)
        await session.commit()

    # Run pipeline
    await pipeline_service.run_pipeline(repo_id, AsyncSessionLocal)

    # Verify results in database
    async with AsyncSessionLocal() as session:
        repo = await session.get(Repository, repo_id)
        assert repo.status == "completed"
        assert repo.progress_percent == 100
        assert "FastAPI" in repo.frameworks
        assert "SQLAlchemy" in repo.frameworks
        assert repo.stats["apis"] == 2
        assert repo.stats["models"] == 2

        # Check documents
        docs_res = await session.execute(
            select(Document).where(Document.repository_id == repo_id)
        )
        docs = docs_res.scalars().all()
        doc_types = {d.doc_type for d in docs}
        assert "readme" in doc_types
        assert "api" in doc_types
        assert "architecture" in doc_types
        assert "onboarding" in doc_types
        assert "report" in doc_types

        # Check diagrams
        diag_res = await session.execute(
            select(Diagram).where(Diagram.repository_id == repo_id)
        )
        diagrams = diag_res.scalars().all()
        diag_types = {d.diagram_type for d in diagrams}
        assert "architecture" in diag_types
        assert "sequence" in diag_types
        assert "er" in diag_types
        assert "dependency" in diag_types
        assert "react_flow" in diag_types

    # Test chat service query
    answer, citations = await chat_service.ask(
        query="Where is the Account model defined?",
        repository_id=repo_id,
        repo_name="Test Mini Project",
    )
    assert len(citations) > 0
    assert any("models.py" in c["file"] for c in citations)

    # Cleanup temp dir
    shutil.rmtree(temp_dir, ignore_errors=True)
