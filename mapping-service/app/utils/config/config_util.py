import os
from dotenv import load_dotenv

load_dotenv()


STAR = {
    "opensearch_url": os.getenv("STAR_OPENSEARCH_URL"),
    "opensearch_index": os.getenv("STAR_OPENSEARCH_BASE_INDEX"),
    "opensearch_username": os.getenv("STAR_OPENSEARCH_USERNAME"),
    "opensearch_password": os.getenv("STAR_OPENSEARCH_PASSWORD"),
}

CLARISA = {
    "opensearch_url": os.getenv("CLARISA_OPENSEARCH_URL"),
    "opensearch_index": os.getenv("CLARISA_OPENSEARCH_BASE_INDEX"),
    "opensearch_username": os.getenv("CLARISA_OPENSEARCH_USERNAME"),
    "opensearch_password": os.getenv("CLARISA_OPENSEARCH_PASSWORD"),
}