import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "aws_region": os.getenv("AWS_REGION", "us-east-1")
}

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"

CLARISA_VALIDATE_URL = os.getenv("CLARISA_VALIDATE_URL")

INTERACTION_SERVICE_URL = os.getenv("INTERACTION_SERVICE_URL")