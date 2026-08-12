from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.repositories.scan_history_repository import ScanHistoryRepository

router=APIRouter(
    prefix="/api/v1/history",
    tags=["History"]
)

@router.get("")
def history(db:Session=Depends(get_db)):
    return ScanHistoryRepository.get_all(db)