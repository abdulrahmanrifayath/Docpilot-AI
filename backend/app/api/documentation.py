from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.repository import Document
from app.schemas.repository import DocumentResponse

router = APIRouter(prefix="/repositories", tags=["Documentation"])


@router.get("/{repository_id}/documents", response_model=List[DocumentResponse])
async def list_documents(repository_id: str, db: AsyncSession = Depends(get_db)):
    """List all generated documentation chapters for a repository."""
    result = await db.execute(
        select(Document).where(Document.repository_id == repository_id)
    )
    docs = result.scalars().all()
    return docs


@router.get("/{repository_id}/documents/{doc_type}", response_model=DocumentResponse)
async def get_document(repository_id: str, doc_type: str, db: AsyncSession = Depends(get_db)):
    """Get a specific generated document (readme, api, architecture, onboarding, report)."""
    result = await db.execute(
        select(Document)
        .where(Document.repository_id == repository_id, Document.doc_type == doc_type.lower())
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document of type '{doc_type}' not found")
    return doc


@router.get("/{repository_id}/export/{doc_type}")
async def export_document(repository_id: str, doc_type: str, db: AsyncSession = Depends(get_db)):
    """Export document directly as downloadable raw Markdown."""
    result = await db.execute(
        select(Document)
        .where(Document.repository_id == repository_id, Document.doc_type == doc_type.lower())
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document of type '{doc_type}' not found")

    filename = f"{doc_type.upper()}.md"
    return Response(
        content=doc.content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
