import os
from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "region": os.getenv("AWS_REGION"),
    "bucket_name": os.getenv("BUCKET_NAME")
}

SQL_SERVER = {
    "server": os.getenv("SERVER"),
    "database": os.getenv("DATABASE"),
    "client_id": os.getenv("CLIENT_ID"),
    "client_secret": os.getenv("CLIENT_SECRET")
}

OPENSEARCH = {
    "host": os.getenv("OPENSEARCH_HOST"),
    "index_chatbot": os.getenv("OPENSEARCH_INDEX_NAME_CHATBOT")
}

KNOWLEDGE_BASE = {
    "knowledge_base_id": os.getenv("KNOWLEDGE_BASE_ID"),
    "agent_id": os.getenv("AGENT_ID"),
    "agent_alias_id": os.getenv("AGENT_ALIAS_ID"),
    "memory_id": os.getenv("MEMORY_ID")
}

AI_FEEDBACK_URL = os.getenv("AI_FEEDBACK_URL")