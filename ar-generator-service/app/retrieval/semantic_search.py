from app.llm.invoke_llm import get_bedrock_embeddings
from app.utils.logger.logger_util import get_logger
from app.s3_vectors.client import S3VectorsClient, get_vector_store_client

logger = get_logger()

SEMANTIC_TABLES = [
    "vw_ai_deliverables",
    "vw_ai_project_contribution",
    "vw_ai_oicrs",
    "vw_ai_innovations",
]


def build_semantic_filter(indicator: str, year, source_tables: list[str]) -> dict:
    return {
        "$and": [
            {"indicator_acronym": {"$eq": indicator}},
            {"year": {"$eq": str(year)}},
            {
                "$or": [
                    {"source_table": {"$eq": table_name}}
                    for table_name in source_tables
                ]
            },
        ]
    }


def semantic_search(
    query: str,
    indicator: str,
    year,
    source_tables: list[str] | None = None,
    top_k: int = 10000,
    client: S3VectorsClient | None = None,
) -> list[dict]:
    client = client or get_vector_store_client()
    source_tables = source_tables or SEMANTIC_TABLES

    try:
        logger.info("📚 Retrieving relevant context from S3 Vectors...")
        embedding = get_bedrock_embeddings([query])[0]
        if not embedding:
            logger.error("❌ Failed to generate query embedding")
            return []

        metadata_filter = build_semantic_filter(indicator, year, source_tables)
        return client.query_vectors(
            query_vector=embedding,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
    except Exception as error:
        logger.error(f"❌ Error during semantic search: {error}")
        return []
