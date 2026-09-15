import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_or_create_bucket():
    s3_client = boto3.client('s3')
    bucket_name = settings.S3_BUCKET_NAME
    region = boto3.session.Session().region_name or 'us-east-1'
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket {bucket_name} already exists and is accessible.")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            logger.info(f"Bucket {bucket_name} does not exist. Creating it.")
            try:
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                logger.info(f"Successfully created bucket {bucket_name}.")
                return True
            except Exception as create_error:
                logger.error(f"Failed to create bucket: {create_error}")
                return False
        elif error_code == '403':
            logger.error(f"Bucket {bucket_name} exists but you don't have permission to access it.")
            return False
        else:
            logger.error(f"Error checking bucket: {e}")
            return False

if __name__ == "__main__":
    get_or_create_bucket()
