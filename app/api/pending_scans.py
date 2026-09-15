from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List

from app.database.dependencies import get_db
from app.repositories.pending_scan_repository import PendingScanRepository
from app.schemas.scan import PendingScanResponse

router = APIRouter(
    prefix="/api/v1/scans",
    tags=["Pending Scans"]
)

@router.get("/pending", response_model=List[PendingScanResponse])
def get_pending_scans(
    request: Request,
    db: Session = Depends(get_db)
):
    pending_scans = PendingScanRepository.get_all_pending(db)
    result = []

    for scan in pending_scans:
        image_url = None
        if scan.image_id:
            image_url = str(request.base_url).rstrip("/") + f"/images/{scan.image_id}"

        result.append({
            "id": str(scan.id),
            "image_id": scan.image_id,
            "image_url": image_url,
            "product_name": scan.name,
            "barcode": scan.barcode,
            "ocr_text": scan.ocr_text,
            "ocr_confidence": scan.ocr_confidence or 0.0,
            "expiry_date_iso": scan.expiry_date.strftime("%Y-%m-%d") if scan.expiry_date else None,
            "category": scan.category,
            "location": scan.location,
            "scan_timestamp_ms": int(scan.scanned_at.timestamp() * 1000) if scan.scanned_at else 0,
            "pi_id": scan.pi_id,
            "status": scan.status.value if hasattr(scan.status, "value") else str(scan.status)
        })

    return result
