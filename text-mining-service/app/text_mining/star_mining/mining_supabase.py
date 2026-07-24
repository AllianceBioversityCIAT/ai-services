import time
import json
from app.text_mining.providers import invoke_model
from app.text_mining.shared.retrieval import split_text
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.prompt.prompt_star import DEFAULT_PROMPT_STAR
from app.utils.config.config_util import STAR_BUCKET_KEY_NAME
from app.text_mining.shared.json_parser import extract_json_from_markdown, is_valid_json
from app.text_mining.star_mining.vectorize_supabase import (get_embedding,
                               store_reference_embeddings,
                               store_temp_embeddings,
                               get_all_reference_data,
                               get_relevant_chunk,
                               initialize_supabase_tables,
                               get_connection
                               )


logger = get_logger()


def initialize_reference_data(bucket_name, file_key_regions, file_key_countries):
    """Initialize reference data if it doesn't exist"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reference_embeddings")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        if count == 2:
            logger.info("✅ Reference data already exists in the database. Skipping initialization.")
            return True
        
        logger.info("🔄 Initializing reference data...")

        document_content_regions = read_document_from_s3(
            bucket_name, file_key_regions)
        regions_embeddings = get_embedding(document_content_regions)

        document_content_countries = read_document_from_s3(
            bucket_name, file_key_countries)
        countries_embeddings = get_embedding(document_content_countries)

        store_reference_embeddings(document_content_regions, regions_embeddings)
        store_reference_embeddings(document_content_countries, countries_embeddings)

        logger.info("✅ Reference data initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error initializing reference data: {str(e)}")
        raise


def process_document(bucket_name, file_key, prompt=DEFAULT_PROMPT_STAR):
    start_time = time.time()

    try:
        reference_file_regions = f"{STAR_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{STAR_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        initialize_supabase_tables()
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣ Generating embeddings...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        document_name = store_temp_embeddings(chunks, embeddings, file_key)

        all_reference_data = get_all_reference_data()

        relevant_chunks = get_relevant_chunk(prompt, document_name)

        context = all_reference_data + relevant_chunks

        query = f"""
        Based on this context:\n{context}\n\n
        Answer the question:\n{prompt}
        """

        response_text = invoke_model(query, max_tokens=3000).text

        extracted_json = extract_json_from_markdown(response_text)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"✅ Successfully generated response:\n{response_text}")
        logger.info(f"⏱️ Response time: {elapsed_time:.2f} seconds")

        return {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json.loads(extracted_json) if is_valid_json(extracted_json) else {"text": response_text}
        }

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise