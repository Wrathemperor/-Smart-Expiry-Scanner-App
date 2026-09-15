from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
from app.core.enums import ScanStatus

class PendingScan(Base):
    __tablename__="PendingScans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    barcode: Mapped[str] = mapped_column(String(100), default="")
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    name: Mapped[str] = mapped_column(String(255), default="")
    ocr_text: Mapped[str|None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(200), default="")
    expiry_date: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str] = mapped_column(String(100), default="")
    image_id: Mapped[str|None] = mapped_column(String(255), nullable=True)
    pi_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(Enum(ScanStatus), default=ScanStatus.PENDING)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
