import os
import uuid
import shutil
import logging
from pathlib import Path
from fastapi import UploadFile, Request, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

class ImageService:
    @staticmethod
    def save_image(request: Request, file: UploadFile):
        os.makedirs(settings.IMAGE_DIRECTORY, exist_ok=True)
        extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        if not extension:
            extension = ".jpg"
        image_id = f"{uuid.uuid4()}{extension}"
        local_path = os.path.join(str(settings.IMAGE_DIRECTORY), image_id)

        # 1. Always save a local copy for immediate OCR processing and offline serving
        try:
            file.file.seek(0)
            with open(local_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file.file.seek(0)
        except Exception as e:
            logger.error(f"Failed to save image locally: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image locally: {str(e)}")

        # Default local URL
        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/images/{image_id}"

        # 2. Upload to AWS S3 if credentials and bucket are available
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            s3_client = boto3.client('s3')
            bucket_name = settings.S3_BUCKET_NAME

            file.file.seek(0)
            s3_client.upload_fileobj(
                file.file,
                bucket_name,
                image_id,
                ExtraArgs={"ContentType": file.content_type or "image/jpeg"}
            )
            # Generate presigned URL (valid for 7 days)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': image_id},
                ExpiresIn=604800
            )
            image_url = presigned_url
            logger.info(f"Successfully uploaded {image_id} to S3 bucket {bucket_name}")
        except Exception as s3_err:
            logger.warning(f"S3 upload bypassed/failed, falling back to local storage URL: {s3_err}")

        return {
            "image_id": image_id,
            "filename": file.filename,
            "image_url": image_url,
            "local_path": local_path
        }

    @staticmethod
    def get_image_url(request: Request, image_id: str | None) -> str | None:
        if not image_id:
            return None
        # Check if S3 can generate a presigned URL, else return local endpoint
        try:
            import boto3
            s3_client = boto3.client('s3')
            bucket_name = settings.S3_BUCKET_NAME
            return s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': image_id},
                ExpiresIn=604800
            )
        except Exception:
            pass
        base_url = str(request.base_url).rstrip("/")
        return f"{base_url}/images/{image_id}"