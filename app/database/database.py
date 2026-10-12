from app.database.base import Base
from app.database.session import engine

#import models so sqlalchemy registers them
from app.models.products import Product

def create_database():
    Base.metadata.create_all(bind=engine)