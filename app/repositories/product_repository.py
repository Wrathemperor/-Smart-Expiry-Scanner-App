from sqlalchemy.orm import Session
from app.models.products import Product
from app.schemas.product import ProductCreate,ProductUpdate

class ProductRepository:

    @staticmethod
    def create(db:Session,product:ProductCreate)->Product:
        db_product=Product(
            name=product.name,
            category=product.category,
            barcode=product.barcode,
            expiry_date=product.expiry_date,
            location=product.location,
            image_id=product.image_id,
            ocr_confidence=product.ocr_confidence,
        )

        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        return db_product
    @staticmethod
    def get_all(db:Session):
        return db.query(Product).all()

    @staticmethod
    def get_by_id(db:Session,product_id:int):
        return db.query(Product).filter(Product.id==product_id).first()


    # @staticmethod
    # def update(
    #     db:Session,
    #     db_product:Product,
    #     product:ProductUpdate
    # )->Product:
    #     db_product.name=product.name
    #     db_product.name=product.category




        
    @staticmethod
    def delete(db:Session,product:Product):
        db.delete(product)
        db.commit()

    @staticmethod
    def update(db:Session,db_product:Product,product:ProductUpdate)->Product:
        db_product.name=product.name
        db_product.category=product.category
        db_product.barcodee=product.barcode
        db_product.expiry_date=product.expiry_date
        db_product.location=product.location
        db_product.image_id=product.image_id
        db_product.ocr_confidence=product.ocr_confidence

        db.commit()
        db.refresh(db_product)
        return db_product

    # @staticmethod
    # def delete(db:Session,product:Product):
    #     db.delete(product)
    #     db.commit()

    


    