import vecs
import os
import uuid
from dotenv import load_dotenv
from app.utils.logger.logger_util import get_logger

logger = get_logger()

load_dotenv()


def store_embedding(collection, text: str, embedding: list):
    try:   
        new_id = str(uuid.uuid4())     
        collection.upsert(
            records=[(new_id, embedding, {"text": text})]
        )
        print(f"✓ Vector saved: '{text}...'")
    except Exception as e:
        print(f"Error saving vector: {str(e)}")

