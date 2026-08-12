from sqlalchemy.orm import Session
from app.models import pending_scan
from app.models.pending_scan import PendingScan
from app.repositories.pending_scan_repository import PendingScanRepository
from app.schemas.scan import ScanRequest
from app.schemas.product import ProductCreate
from app.services.product_services import ProductService
from app.repositories.scan_history_repository import ScanHistoryRepository
from app.core.enums import ScanStatus
import os

class ScanService:
    @staticmethod
    def process_scan(db: Session, scan: ScanRequest):
        pending = PendingScan(
            name=scan.name,
            category=scan.category,
            barcode=scan.barcode,
            expiry_date=scan.expiry_date,
            location=scan.location,
            image_id=scan.image_id,
            ocr_confidence=scan.ocr_confidence,
            pi_id="pi_123",
            status=ScanStatus.PENDING,
        )

        return PendingScanRepository.create(db, pending)
    @staticmethod
    def approve_scan(db: Session, scan_id: int):

        pending_scan = PendingScanRepository.get_by_id(db, scan_id)

        if pending_scan is None:
            return {
                "error": "Scan not found"
            }

        if pending_scan.status != ScanStatus.PENDING:
            return {
                "error": "Scan already processed"
            }

        product = ProductCreate(
            name=pending_scan.name,
            category=pending_scan.category,
            barcode=pending_scan.barcode,
            expiry_date=pending_scan.expiry_date,
            location=pending_scan.location,
            image_id=pending_scan.image_id,
            ocr_confidence=pending_scan.ocr_confidence
        )

        created_product = ProductService.create_product(db, product)

        pending_scan.status = ScanStatus.APPROVED
        PendingScanRepository.update(db, pending_scan)

        ScanHistoryRepository.create(
            db,
            created_product.id,
            "Created"
        )

        PendingScanRepository.update_status(db, pending_scan, ScanStatus.APPROVED)
        return created_product

    @staticmethod
    def reject_scan(db: Session, scan_id: int):
        pending_scan = PendingScanRepository.get_by_id(db, scan_id)
        if pending_scan is None:
            return {"error": "Scan not found"}

        if pending_scan.image_id:
            image_path = os.path.join("app", "images", pending_scan.image_id)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass

        pending_scan.status = ScanStatus.REJECTED
        PendingScanRepository.update(db, pending_scan)
        return {"status": "success", "message": "Scan rejected and image discarded"}

    @staticmethod
    def request_rescan(db: Session, scan_id: int):
        pending_scan = PendingScanRepository.get_by_id(db, scan_id)
        if pending_scan is None:
            return {"error": "Scan not found"}

        pending_scan.status = ScanStatus.RESCAN_REQUEST
        PendingScanRepository.update(db, pending_scan)
        return {"status": "success", "message": "Rescan requested"}

        