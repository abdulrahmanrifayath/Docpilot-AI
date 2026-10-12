from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.repository import Diagram
from app.schemas.repository import DiagramResponse

router = APIRouter(prefix="/repositories", tags=["Diagrams"])


@router.get("/{repository_id}/diagrams", response_model=List[DiagramResponse])
async def list_diagrams(repository_id: str, db: AsyncSession = Depends(get_db)):
    """List all generated diagrams for a repository."""
    result = await db.execute(
        select(Diagram).where(Diagram.repository_id == repository_id)
    )
    return result.scalars().all()


@router.get("/{repository_id}/diagrams/{diagram_type}", response_model=DiagramResponse)
async def get_diagram(repository_id: str, diagram_type: str, db: AsyncSession = Depends(get_db)):
    """Get a specific diagram (architecture, sequence, er, dependency, react_flow)."""
    result = await db.execute(
        select(Diagram)
        .where(Diagram.repository_id == repository_id, Diagram.diagram_type == diagram_type.lower())
    )
    diagram = result.scalars().first()
    if not diagram:
        raise HTTPException(status_code=404, detail=f"Diagram '{diagram_type}' not found")
    return diagram
