from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.repository import Repository, ChatMessage
from app.schemas.repository import ChatMessageCreate, ChatMessageResponse
from app.ai.chat_service import chat_service

router = APIRouter(prefix="/repositories", tags=["AI Chat"])


@router.get("/{repository_id}/chat", response_model=List[ChatMessageResponse])
async def get_chat_history(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve chat history for a repository."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.repository_id == repository_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


@router.post("/{repository_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    repository_id: str,
    payload: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Ask a question about the repository using repository-aware RAG."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Record user message
    user_msg = ChatMessage(
        repository_id=repository_id,
        role="user",
        content=payload.content,
        sources=[],
    )
    db.add(user_msg)
    await db.commit()

    # Query RAG chat service
    answer, citations = await chat_service.ask(
        query=payload.content,
        repository_id=repository_id,
        repo_name=repo.name,
    )

    # Record assistant message
    asst_msg = ChatMessage(
        repository_id=repository_id,
        role="assistant",
        content=answer,
        sources=citations,
    )
    db.add(asst_msg)
    await db.commit()
    await db.refresh(asst_msg)

    return asst_msg
