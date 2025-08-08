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
    "index_chatbot": os.getenv("OPENSEARCH_INDEX_NAME_CHATBOT"),
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID_OS"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY_OS")
}

KNOWLEDGE_BASE = {
    "knowledge_base_id": os.getenv("KNOWLEDGE_BASE_ID"),
    "agent_id": os.getenv("AGENT_ID"),
    "agent_alias_id": os.getenv("AGENT_ALIAS_ID"),
    "memory_id": os.getenv("MEMORY_ID")
}