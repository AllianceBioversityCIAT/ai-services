import time
import json
import boto3
from typing import Dict, Any
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.config.config_util import AICCRA_BUCKET_KEY_NAME
from app.utils.prompt.prompt_aiccra import DEFAULT_PROMPT_AICCRA
from app.llm.mining import split_text, invoke_model, is_valid_json, extract_json_from_markdown
from app.utils.interactions.interaction_client import interaction_client
from app.llm.reference_cache import get_reference_data, format_reference_for_prompt
from app.llm.vectorize import get_embedding, store_temp_embeddings, get_relevant_chunk

logger = get_logger()

def process_document_aiccra(bucket_name, file_key, prompt, user_id: str = None):
    """Process document for AICCRA project"""
    start_time = time.time()

    try:
        if prompt is None:
            prompt = DEFAULT_PROMPT_AICCRA
            logger.info("📝 Using default AICCRA prompt")
        else:
            logger.info(f"🎯 Using custom prompt (length: {len(prompt)})")

        reference_file_regions = f"{AICCRA_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{AICCRA_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        reference_data = get_reference_data(
            bucket_name, AICCRA_BUCKET_KEY_NAME, reference_file_regions, reference_file_countries
        )

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣ Generating embeddings for AICCRA...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        db, temp_table_name, document_name = store_temp_embeddings(chunks, embeddings, file_key)

        relevant_chunks = get_relevant_chunk(prompt, db, temp_table_name, document_name)

        document_text = "\n\n---\n\n".join(relevant_chunks)
        reference_section = format_reference_for_prompt(reference_data)

        query = f"""{"=" * 80}
DOCUMENT TO ANALYZE:
{"=" * 80}
{document_text}

{"=" * 80}
{reference_section}
{"=" * 80}

{prompt}"""

        response_text = invoke_model(query)
        extracted_json = extract_json_from_markdown(response_text)
        json_content = json.loads(extracted_json) if is_valid_json(extracted_json) else {"text": response_text}

        end_time = time.time()
        elapsed_time = end_time - start_time

        interaction_id = None
        if user_id:
            try:
                user_input = f"Document analysis request for: {file_key}"
                if isinstance(document_content, dict) and document_content.get("type") == "excel":
                    user_input += f" (Excel file with {len(document_content.get('chunks', []))} rows)"
                
                ai_output = json.dumps(json_content, indent=2, ensure_ascii=False)
                
                tracking_context = {
                    "bucket_name": bucket_name,
                    "file_key": file_key,
                    "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                    "prompt_full_length": len(prompt),
                    "chunks_processed": len(chunks),
                    "results_count": len(json_content.get("results", [])),
                    "model_used": "claude-sonnet-4-5",
                    "processing_steps": ["document_read", "text_splitting", "embedding_generation", "vector_search", "llm_processing", "field_mapping"]
                }
                
                interaction_response = interaction_client.track_interaction(
                    user_id=user_id,
                    user_input=user_input,
                    ai_output=ai_output,
                    service_name="text-mining",
                    display_name="AICCRA Text Mining Service",
                    service_description="A service that analyzes documents and extracts insights based on user prompts.",
                    context=tracking_context,
                    response_time_seconds=elapsed_time,
                    platform="AICCRA"
                )

                if interaction_response:
                    interaction_id = interaction_response.get('interaction_id')
                    logger.info(f"📊 Interaction tracked with ID: {interaction_id}")
                else:
                    logger.warning("⚠️ Failed to track interaction with interaction service")

            except Exception as tracking_error:
                logger.error(f"❌ Error tracking interaction: {str(tracking_error)}")
        
        logger.info(f"✅ Successfully generated AICCRA response:\n{json.dumps(json_content, indent=2, ensure_ascii=False)}")
        logger.info(f"⏱️ AICCRA Response time: {elapsed_time:.2f} seconds")

        result = {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json_content,
            "project": "AICCRA"
        }

        if interaction_id:
            result["interaction_id"] = interaction_id
        
        return result

    except Exception as e:
        logger.error(f"❌ AICCRA Error: {str(e)}")
        raise