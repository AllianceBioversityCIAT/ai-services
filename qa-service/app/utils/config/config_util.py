import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

CLARISA_VALIDATE_URL = os.getenv("CLARISA_VALIDATE_URL")