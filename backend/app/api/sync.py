from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.repository import SyncResponse
from app.services.sync_service import sync_service

router = APIRouter(prefix="/repositories", tags=["Synchronization"])


@router.post("/{repository_id}/sync", response_model=SyncResponse)
async def sync_repository(repository_id: str, db: AsyncSession = Depends(get_db)):
    """Detect changes and incrementally synchronize repository documentation."""
    try:
        response = await sync_service.check_and_sync(repository_id, db)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")
