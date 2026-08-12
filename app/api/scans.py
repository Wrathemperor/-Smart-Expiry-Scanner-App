from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.database.dependencies import get_db
from app.schemas.scan import ScanRequest, PendingScanResponse
from app.services.scan_service import ScanService
from app.services.image_service import ImageService
from app.services.ocr_service import analyze_image
from app.raspberry_pi_client import detect_barcodes
from app.models.pending_scan import PendingScan
from app.repositories.pending_scan_repository import PendingScanRepository
from app.core.enums import ScanStatus
from fastapi import UploadFile, File, Form, HTTPException, Request
import os
from datetime import datetime


router=APIRouter(
    prefix="/api/v1/scans",
    tags=["Scans"]
)

@router.post("/")
def scan_product(
    scan:ScanRequest,
    db:Session=Depends(get_db)
):
    return ScanService.process_scan(db,scan)

@router.post("/{scan_id}/approve")
def approve_scan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    return ScanService.approve_scan(db, scan_id)

@router.post("/{scan_id}/reject")
def reject_scan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    result = ScanService.reject_scan(db, scan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/{scan_id}/rescan")
def request_rescan(
    scan_id: int,
    db: Session = Depends(get_db)
):
    result = ScanService.request_rescan(db, scan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/from-image", response_model=PendingScanResponse)
def create_scan_from_image(
    request: Request,
    device_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 2. Validate image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be an image.")

    # 3. Save the image
    try:
        saved_image = ImageService.save_image(request, file)
        image_id = saved_image["image_id"]
        image_url = saved_image["image_url"]
        image_path = os.path.join("app", "images", image_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 4. Barcode detection
    barcode = ""
    try:
        barcodes = detect_barcodes(image_path)
        if barcodes:
            barcode = barcodes[0]
    except Exception:
        pass

    # 5. Run OCRService
    ocr_result = analyze_image(image_path)
    
    # 6. Extract
    raw_text = ocr_result.get("raw_text")
    ocr_conf = ocr_result.get("ocr_confidence", 0.0)
    expiry_date_str = ocr_result.get("expiry_date")
    product_name = ocr_result.get("name") or ""
    
    expiry_date_dt = None
    if expiry_date_str:
        try:
            expiry_date_dt = datetime.fromisoformat(expiry_date_str)
        except Exception:
            pass
            
    # 7. Create PendingScan
    pending_scan = PendingScan(
        barcode=barcode,
        name=product_name,
        category="",
        expiry_date=expiry_date_dt,
        location="",
        image_id=image_id,
        ocr_text=raw_text,
        ocr_confidence=ocr_conf,
        pi_id=device_id,
        status=ScanStatus.PENDING,
        scanned_at=datetime.utcnow()
    )
    
    # 8. Persist
    pending_scan = PendingScanRepository.create(db, pending_scan)
    
    # 9. Return
    return {
        "id": str(pending_scan.id),
        "image_id": pending_scan.image_id,
        "image_url": image_url,
        "product_name": pending_scan.name,
        "barcode": pending_scan.barcode,
        "ocr_text": pending_scan.ocr_text,
        "ocr_confidence": pending_scan.ocr_confidence,
        "expiry_date_iso": pending_scan.expiry_date.strftime("%Y-%m-%d") if pending_scan.expiry_date else None,
        "category": pending_scan.category,
        "location": pending_scan.location,
        "scan_timestamp_ms": int(pending_scan.scanned_at.timestamp() * 1000) if pending_scan.scanned_at else 0,
        "pi_id": pending_scan.pi_id,
        "status": pending_scan.status.value if hasattr(pending_scan.status, "value") else str(pending_scan.status)
    }