from datetime import date
from pydantic import BaseModel

class ScanRequest(BaseModel):
    name:str
    category:str
    barcode:str
    expiry_date: date
    location:str
    image_id:str | None=None
    ocr_confidence:float=0.0
    scan_timestamp_ms: int

class PendingScanResponse(BaseModel):
    id: str
    image_id: str | None = None
    image_url: str | None = None
    product_name: str
    barcode: str
    ocr_text: str | None = None
    ocr_confidence: float
    expiry_date_iso: str | None = None
    category: str
    location: str
    scan_timestamp_ms: int
    pi_id: str
    status: str