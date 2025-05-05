import re
import json
import boto3
import lancedb
import unicodedata
from pathlib import Path
from datetime import datetime
from app.utils.config.config_util import BR
from app.utils.logger.logger_util import get_logger
import os


logger = get_logger()

is_prod = os.getenv('IS_PROD', 'false').lower() == 'true'

#if is_prod:
DB_PATH = "/tmp/miningdb"
Path(DB_PATH).mkdir(parents=True, exist_ok=True)
logger.info(f"Production mode: DB path set to {DB_PATH}")

#else:
#    BASE_DIR = Path(__file__).resolve().parent.parent.parent
#    DB_PATH = str(BASE_DIR / "app" / "db" / "miningdb")
#    logger.info(f"Development mode: DB path set to {DB_PATH}")

REFERENCE_TABLE_NAME = "clarisa_reference"
TEMP_TABLE_NAME = "temp_documents"


bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)


def get_embedding(text):
    try:
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


def check_reference_exists(db_path=DB_PATH):
    """Check if reference table already exists in the database"""
    try:
        db = lancedb.connect(db_path)
        return REFERENCE_TABLE_NAME in db.table_names()
    except Exception as e:
        logger.error(f"❌ Error checking reference table: {str(e)}")
        return False


def normalize_filename(filename):
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('utf-8')
    filename = filename.lower().replace(" ", "_")
    filename = re.sub(r'[^a-z0-9_\-\.]', '', filename)

    return filename


def store_reference_embeddings(chunks, embeddings, db_path=DB_PATH):
    """Store reference data embeddings that should persist"""
    try:
        logger.info("💾 Storing reference embeddings in LanceDB...")
        db = lancedb.connect(db_path)

        data = [{"text": chunk, "vector": embedding, "is_reference": True}
                for chunk, embedding in zip(chunks, embeddings)]

        if REFERENCE_TABLE_NAME not in db.table_names():
            db.create_table(REFERENCE_TABLE_NAME, data=data)
            logger.info(f"✅ Created reference table with {len(data)} entries")
        else:
            logger.info("✅ Reference table already exists")

        return db
    except Exception as e:
        logger.error(f"❌ Error storing reference embeddings: {str(e)}")
        raise


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


def get_all_reference_data(db_path=DB_PATH):
    """
    Retrieve all data from the reference table without filtering by relevance
    """
    try:
        logger.info("📚 Retrieving all reference data...")
        db = lancedb.connect(db_path)

        if REFERENCE_TABLE_NAME not in db.table_names():
            logger.warning("⚠️ Reference table does not exist!")
            return []

        ref_table = db.open_table(REFERENCE_TABLE_NAME)
        all_data = ref_table.to_pandas()

        logger.info(f"✅ Retrieved {len(all_data)} reference records")
        return all_data["text"].tolist()

    except Exception as e:
        logger.error(f"❌ Error retrieving all reference data: {str(e)}")
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
