import boto3
from botocore.exceptions import ClientError
from app.utils.config.config_util import AWS
from app.utils.logger.logger_util import get_logger

logger = get_logger()

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS['aws_access_key'],
    aws_secret_access_key=AWS['aws_secret_key'],
    region_name=AWS['region']
)

bucket_name = AWS['bucket_name']


def s3_file_exists(file_key):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise


def upload_file_to_s3(file_key, local_file_path):
    """
    Upload a file to an S3 bucket.

    Args:
        bucket_name: Name of the S3 bucket
        file_key: The key (path) where the file will be stored in S3
        local_file_path: Path to the local file to be uploaded

    Returns:
        dict: The response from S3 upload operation

    Raises:
        Exception: If the upload fails
    """
    try:
        logger.info(f"📤 Uploading file to {bucket_name}/{file_key}...")

        with open(local_file_path, 'rb') as file_content:
            response = s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=file_content
            )

        logger.info(f"✅ File successfully uploaded to {bucket_name}/{file_key}")
        
        return response

    except Exception as e:
        logger.error(
            f"❌ Error uploading file to {bucket_name}/{file_key}: {str(e)}")
        raise