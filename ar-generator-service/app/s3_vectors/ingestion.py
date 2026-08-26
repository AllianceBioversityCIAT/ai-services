import json
import pandas as pd
from db_conn.sql_connection import load_data
from app.utils.logger.logger_util import get_logger
from app.llm.invoke_llm import get_bedrock_embeddings
from app.s3_vectors.schemas import build_vector_record, rows_to_chunks
from app.s3_vectors.client import S3VectorsClient, get_vector_store_client


logger = get_logger()

MIDYEAR_INGEST_TABLES = [
    "vw_ai_deliverables",
    "vw_ai_project_contribution",
    "vw_ai_questions",
    "vw_ai_oicrs",
    "vw_ai_innovations",
]

ANNUAL_INGEST_TABLES = MIDYEAR_INGEST_TABLES + ["vw_ai_challenges"]


def ingest_table(table_name: str, client: S3VectorsClient | None = None) -> int:
    client = client or get_vector_store_client()

    try:
        logger.info(f"🔍 Processing table: {table_name}")
        df = load_data(table_name)
        if df.empty:
            logger.warning(f"⚠️ No rows found for {table_name}")
            return 0

        rows = df.to_dict(orient="records")
        chunks = rows_to_chunks(rows)

        logger.info(f"🔢 Generating embeddings for {len(chunks)} rows...")
        texts = [json.dumps(chunk, ensure_ascii=False, default=str) for chunk in chunks]
        embeddings = get_bedrock_embeddings(texts)

        vectors = []
        for index, (row, embedding, chunk) in enumerate(zip(rows, embeddings, chunks)):
            if not embedding:
                logger.warning(f"⚠️ Skipping row {index} in {table_name} due to missing embedding")
                continue
            vectors.append(build_vector_record(table_name, index, row, chunk, embedding))

        logger.info(f"📥 Indexing {len(vectors)} vectors in S3 Vectors...")
        inserted = client.put_vectors_batch(vectors)
        logger.info(f"✅ Vectorization completed for {inserted} rows of {table_name}")
        return inserted

    except Exception as error:
        logger.error(f"❌ Error inserting into S3 Vectors for {table_name}: {error}")
        return 0


def ingest_tables(table_names: list[str], client: S3VectorsClient | None = None) -> int:
    client = client or get_vector_store_client()
    total = 0
    for table_name in table_names:
        total += ingest_table(table_name, client=client)
    return total
