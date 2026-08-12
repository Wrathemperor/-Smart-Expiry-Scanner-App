from datetime import datetime
from sqlalchemy import Integer,String,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column

from app.database.base import Base

class ScanHistory(Base):
    __tablename__="ScanHistory"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)

    product_id:Mapped[int]=mapped_column(
        ForeignKey("Products.id"),
        nullable=False
    )

    action:Mapped[str]=mapped_column(
        String(30),
        nullable=False
    )

    timestamp:Mapped[datetime]=mapped_column(
        DateTime,
        default=datetime.utcnow
    )