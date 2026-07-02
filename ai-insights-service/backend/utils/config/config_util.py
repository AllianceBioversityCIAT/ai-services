import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

STAR_BUCKET_KEY_NAME = os.getenv("STAR_BUCKET_KEY_NAME")

MAPPING_URL = os.getenv("MAPPING_URL")

CLIENT_ID = os.getenv("CLIENT_ID", None)
CLIENT_SECRET = os.getenv("CLIENT_SECRET", None)

IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"

CLARISA_VALIDATE_URL = os.getenv("CLARISA_VALIDATE_URL")