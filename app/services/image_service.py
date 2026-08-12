import os
import uuid
import shutil

from fastapi import UploadFile,APIRouter,Request,File

IMAGE_DIR="app/images"


class ImageService:
    @staticmethod
    def save_image(request:Request,file:UploadFile):
        os.makedirs(IMAGE_DIR,exist_ok=True)

        extension=os.path.splitext(file.filename)[1]

        image_id = f"{uuid.uuid4()}{extension}"

        image_path = os.path.join(IMAGE_DIR,image_id)

        #Save da file
        with open(image_path,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)

        image_url=str(request.base_url)+f"images/{image_id}"

        return{
            "image_id":image_id,
            "filename":file.filename,
            "image_url":image_url
        }