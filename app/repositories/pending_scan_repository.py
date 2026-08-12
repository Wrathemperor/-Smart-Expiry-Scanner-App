from sqlalchemy.orm import Session
from app.core.enums import ScanStatus
from app.models.pending_scan import PendingScan

class PendingScanRepository:
    @staticmethod
    def create(db:Session,pending_scan:PendingScan):
        db.add(pending_scan)
        db.commit()
        db.refresh(pending_scan)

        return pending_scan
    @staticmethod
    def get_all_pending(db:Session):
        return(
            db.query(PendingScan).filter(PendingScan.status == "PENDING").all()
        )

    @staticmethod
    def get_by_id(db:Session,pending_scan_id:int):
        return db.query(PendingScan).filter(PendingScan.id==pending_scan_id).first()

    @staticmethod
    def update(db:Session,scan:PendingScan):
        db.commit()
        db.refresh(scan)

        return scan

    @staticmethod
    def delete(db:Session,scan:PendingScan):
        db.delete(scan)
        db.commit()

    @staticmethod
    def update_status(
        db: Session,
        pending_scan: PendingScan,
        status: ScanStatus
    ):
        pending_scan.status = status

        db.commit()
        db.refresh(pending_scan)

        return pending_scan