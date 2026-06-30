import re
import json
import boto3
import lancedb
import unicodedata
from pathlib import Path
from datetime import datetime
from app.utils.config.config_util import AWS
from app.utils.logger.logger_util import get_logger


logger = get_logger()

DB_PATH = "/tmp/miningdb"
Path(DB_PATH).mkdir(parents=True, exist_ok=True)
logger.info(f"Production mode: DB path set to {DB_PATH}")

# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# DB_PATH = str(BASE_DIR / "app" / "db" / "miningdb")
# logger.info(f"Development mode: DB path set to {DB_PATH}")

TEMP_TABLE_NAME = "temp_documents"


bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=AWS['aws_access_key'],
    aws_secret_access_key=AWS['aws_secret_key'],
    region_name='us-east-1'
)


def get_embedding(text):
    try:
        # Ensure text is a string, not a dict or other object
        if isinstance(text, dict):
            # If it's an Excel structure, convert to string representation
            if text.get("type") == "excel":
                text = "\n".join(text.get("chunks", []))
            else:
                text = str(text)
        elif not isinstance(text, str):
            text = str(text)
        
        # Ensure text is not empty
        if not text.strip():
            logger.warning("⚠️ Empty text provided for embedding, using placeholder")
            text = "Empty document"
        
        request_body = {
            "inputText": text
        }
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response['body'].read())
        embeddings = response_body['embedding']

        return embeddings
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {str(e)}")
        raise


def normalize_filename(filename):
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('utf-8')
    filename = filename.lower().replace(" ", "_")
    filename = re.sub(r'[^a-z0-9_\-\.]', '', filename)

    return filename


def store_temp_embeddings(chunks, embeddings, file_key, db_path=DB_PATH):
    """Store temporary document embeddings"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        s_file_key = normalize_filename(file_key)
        document_name = f"{s_file_key}_{timestamp}"

        logger.info("💾 Storing temporary document embeddings in LanceDB...")
        db = lancedb.connect(db_path)

        data = [{"text": chunk, "vector": embedding, "is_reference": False, "document_name": document_name}
                for chunk, embedding in zip(chunks, embeddings)]

        if TEMP_TABLE_NAME not in db.table_names():
            table = db.create_table(TEMP_TABLE_NAME, data=data)
            logger.info(f"✅ Created temporary table with {len(data)} entries")
        else:
            table = db.open_table(TEMP_TABLE_NAME)
            table.add(data)
            logger.info(
                f"✅ Appended {len(data)} entries to existing temporary table")

        return db, TEMP_TABLE_NAME, document_name
    except Exception as e:
        logger.error(f"❌ Error storing temporary embeddings: {str(e)}")
        raise


def get_relevant_chunk(query, db, table_name, document_name):
    try:
        logger.info("🔍 Searching for relevant fragment...")
        query_embedding = get_embedding(query)
        table = db.open_table(table_name)
        result = table.search(query_embedding).where(
            f'document_name == "{document_name}"').to_pandas()

        table.delete(f'document_name == "{document_name}"')

        return result["text"].tolist()

    except Exception as e:
        logger.error(f"❌ Error retrieving relevant chunk: {str(e)}")
        raise
