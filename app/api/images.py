from fastapi import APIRouter,UploadFile,File,Request
from app.services.image_service import ImageService

router=APIRouter(
    prefix="/api/v1/images",
    tags=["Images"]
)

@router.post("/upload")
def upload_image(request:Request,file:UploadFile = File(...)):
    return ImageService.save_image(request,file)



