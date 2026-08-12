from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate,ProductUpdate


class ProductService:

    @staticmethod
    def create_product(db:Session,product:ProductCreate):
        return ProductRepository.create(db,product)

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