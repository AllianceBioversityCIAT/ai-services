import os
from dotenv import load_dotenv

load_dotenv()

S3 = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR")
}

MS_NAME = os.getenv("MS_NAME", "Mining Microservice")

STAR_BUCKET_KEY_NAME = os.getenv("STAR_BUCKET_KEY_NAME")
PRMS_BUCKET_KEY_NAME = os.getenv("PRMS_BUCKET_KEY_NAME")