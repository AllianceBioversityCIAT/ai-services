import os
from dotenv import load_dotenv

load_dotenv()

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR"),
    "region": os.getenv("AWS_REGION")
}

S3 = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION"),
    "bucket_name": os.getenv("BUCKET_NAME")
}