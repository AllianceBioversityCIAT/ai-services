import os
from dotenv import load_dotenv

load_dotenv(override=False)

BR = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_BR"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_BR"),
    "region": os.getenv("AWS_REGION", "us-east-1")
}

S3 = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
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

S3_VECTORS = {
    "bucket": os.getenv("S3_VECTORS_BUCKET_NAME"),
    "index": os.getenv("S3_VECTORS_INDEX_NAME"),
    "region": os.getenv("AWS_REGION", "us-east-1"),
}

KNOWLEDGE_BASE = {
    "knowledge_base_id": os.getenv("KNOWLEDGE_BASE_ID"),
    "data_source_id": os.getenv("DATA_SOURCE_ID")
}

_SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

LOCAL_DATA = {
    "use_csv_data": os.getenv("USE_CSV_DATA", "false").lower() in ("true", "1", "yes"),
    "csv_data_dir": os.getenv("CSV_DATA_DIR", _SERVICE_ROOT),
}