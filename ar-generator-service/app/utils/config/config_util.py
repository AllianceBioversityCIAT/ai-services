import os
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
# In Lambda, variables come from environment variables configured in the function
load_dotenv(override=False)

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),  # Optional: IAM Role used in Lambda
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR"),  # Optional: IAM Role used in Lambda
    "region": os.getenv("AWS_REGION", "us-east-1")
}

S3 = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),  # Optional: IAM Role used in Lambda
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),  # Optional: IAM Role used in Lambda
    "aws_region": os.getenv("AWS_REGION", "us-east-1"),
    "bucket_name": os.getenv("BUCKET_NAME")
}

SUPABASE = {
    "url": os.getenv("SUPABASE_URL"),
    "collection": os.getenv("COLLECTION_NAME")
}

MYSQL_DATABASE_URL = os.getenv('MYSQL_DATABASE_URL')

SQL_SERVER = {
    "server": os.getenv("SERVER"),
    "database": os.getenv("DATABASE"),
    "client_id": os.getenv("CLIENT_ID"),
    "client_secret": os.getenv("CLIENT_SECRET")
}

OPENSEARCH = {
    "host": os.getenv("OPENSEARCH_HOST"),
    "index": os.getenv("OPENSEARCH_INDEX_NAME"),
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_OS"),  # Optional: IAM Role used in Lambda
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_OS")  # Optional: IAM Role used in Lambda
}

KNOWLEDGE_BASE = {
    "knowledge_base_id": os.getenv("KNOWLEDGE_BASE_ID"),
    "data_source_id": os.getenv("DATA_SOURCE_ID")
}