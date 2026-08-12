from datetime import date
from pydantic import BaseModel,ConfigDict

class ProductBase(BaseModel):
    name:str
    category: str
    barcode: str
    expiry_date:date
    location: str
    image_id:str|None=None
    ocr_confidence:float=0.0

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name:str|None=None
    category:str|None=None

    barcode:str|None=None

    expiry_date:date|None=None

    location:str|None=None

    image_id:str|None=None

    ocr_confidence:float|None=None

class ProductResponse(ProductBase):
    id:int
    model_config=ConfigDict(from_attributes=True)
