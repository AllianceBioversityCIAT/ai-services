import os
from dotenv import load_dotenv

load_dotenv()


BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

OPENAI = {
    "api_key": os.getenv("OPENAI_API_KEY")
}