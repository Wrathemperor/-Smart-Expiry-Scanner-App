from sqlalchemy.orm import Session
from app.models.scan_history import ScanHistory

class ScanHistoryRepository:
    @staticmethod
    def create(
        db:Session,
        product_id:int,
        action:str
    ):
        history=ScanHistory(
            product_id=product_id,action=action
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        return history
    @staticmethod
    def get_all(db:Session):
        return db.query(ScanHistory).all()
    
