from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.database.dependencies import get_db
from app.schemas.product import ProductCreate,ProductResponse,ProductUpdate
from app.services.product_services import ProductService

router =APIRouter(
    prefix="/api/v1/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    product:ProductCreate,
    db:Session=Depends(get_db),
):
    return ProductService.create_product(db,product)

@router.get(
    "",
    response_model=list[ProductResponse],
)
def get_product(
    db:Session=Depends(get_db),
):
    return ProductService.get_products(db)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id:int,
    db:Session=Depends(get_db)

):
    return ProductService.get_product(db,product_id)

@router.put("/{product_id}",response_model=ProductResponse)
def update_product(
    product_id:int,
    product:ProductUpdate,
    db:Session=Depends(get_db)

):
    return ProductService.update_product(db,product_id,product)

@router.delete("/{product_id}")
def delete_product(
    product_id:int,
    db:Session=Depends(get_db)
):
    return ProductService.delete_product(db,product_id)
