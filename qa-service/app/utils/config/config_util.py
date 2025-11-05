import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}