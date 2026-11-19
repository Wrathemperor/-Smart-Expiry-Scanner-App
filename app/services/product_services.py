from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate,ProductUpdate,ProductSyncItem


class ProductService:

    @staticmethod
    def create_product(db:Session,product:ProductCreate):
        return ProductRepository.create(db,product)

    @staticmethod
    def sync_products(db:Session, products:list[ProductSyncItem]):
        synced = 0
        for item in products:
            barcode = item.barcode.strip() or f"android:{item.device_id}:{item.client_id}"
            db_product = ProductRepository.get_by_barcode(db, barcode)
            if db_product is None:
                from app.models.products import Product
                db_product = Product(barcode=barcode)
                db.add(db_product)
            db_product.name = item.name
            db_product.category = item.category
            db_product.expiry_date = item.expiry_date
            db_product.location = item.location
            db_product.image_id = item.image_id
            synced += 1
        db.commit()
        return {"synced": synced}

    @staticmethod
    def get_products(db:Session):
        return ProductRepository.get_all(db)

    @staticmethod
    def get_product(db:Session,product_id:int):
        product=ProductRepository.get_by_id(db,product_id)
        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found!"
            )
        return product

    @staticmethod
    def update_product(db:Session,product_id:int,product:ProductUpdate):
         db_product=ProductRepository.get_by_id(db,product_id)

         if db_product is None:
              raise HTTPException(
                   status_code=404,
                   details="Product Not Found!"
              )
         return ProductRepository.update(db,db_product,product)

    @staticmethod
    def delete_product(db:Session,product_id:int):
         product=ProductRepository.get_by_id(db,product_id)
         if product is None:
              raise HTTPException(
                   status_code=404,
                   detail="Product Not Found!"
              )
         ProductRepository.delete(db,product)

         return{"message":"Product Deleted Successfully..."}

    @staticmethod
    def delete_product(db:Session,product_id:int):
        product = ProductRepository.get_by_id(db,product_id)

        if product is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Product not found!"
                    )
        ProductRepository.delete(db,product)
      
        return {"message":"Product deleted"}
