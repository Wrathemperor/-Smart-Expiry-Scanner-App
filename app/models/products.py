from sqlalchemy import Date as date,String,Integer,Float
from sqlalchemy.orm import Mapped,mapped_column

from app.database.base import Base

class Product(Base):
    __tablename__="Products"
    id: Mapped[int] = mapped_column(Integer,primary_key=True,index=True)
    name:Mapped[String] = mapped_column(String(255),nullable=False)
    category:Mapped[str] = mapped_column(String(255),nullable=False)
    barcode:Mapped[str] = mapped_column(String(100),unique=True,nullable=False)
    expiry_date:Mapped[date] = mapped_column(date,nullable=False)

    location:Mapped[str] = mapped_column(String(100),nullable=False)

    image_id:Mapped[str|None] = mapped_column(String(255),nullable=True)

    ocr_confidence:Mapped[float] = mapped_column(Float,default=0.0)