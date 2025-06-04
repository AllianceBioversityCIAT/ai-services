import os
from dotenv import load_dotenv

load_dotenv()

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR"),
    "region": os.getenv("AWS_REGION")
}

SUPABASE = {
    "url": os.getenv("SUPABASE_URL"),
    "collection": os.getenv("COLLECTION_NAME")
}

MYSQL_DATABASE_URL = os.getenv('MYSQL_DATABASE_URL')

OPENSEARCH = {
    "host": os.getenv("OPENSEARCH_HOST"),
    "index": os.getenv("OPENSEARCH_INDEX_NAME"),
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_OS"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_OS")
}

KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")