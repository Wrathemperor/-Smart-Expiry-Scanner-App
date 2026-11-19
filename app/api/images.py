from fastapi import APIRouter,UploadFile,File,Request,Header
from app.services.image_service import ImageService

router=APIRouter(
    prefix="/api/v1/images",
    tags=["Images"]
)

@router.post("/upload")
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Header("default-user", alias="X-User-ID"),
    device_id: str = Header("unknown-device", alias="X-Device-ID"),
):
    return ImageService.save_image(request, file, user_id=user_id, device_id=device_id)



