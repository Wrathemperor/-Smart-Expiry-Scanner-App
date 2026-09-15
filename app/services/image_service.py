import os
import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, Request, HTTPException
from app.core.config import settings

class ImageService:
    @staticmethod
    def save_image(request: Request, file: UploadFile):
        extension = os.path.splitext(file.filename)[1]
        image_id = f"{uuid.uuid4()}{extension}"

        s3_client = boto3.client('s3')
        bucket_name = settings.S3_BUCKET_NAME
        
        try:
            # Upload the file to S3
            s3_client.upload_fileobj(
                file.file,
                bucket_name,
                image_id,
                ExtraArgs={"ContentType": file.content_type}
            )
            
            # Generate a presigned URL that is valid for 7 days (maximum allowed)
            image_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': image_id},
                ExpiresIn=604800
            )
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"Could not upload image to S3: {str(e)}")

        return {
            "image_id": image_id,
            "filename": file.filename,
            "image_url": image_url
        }