import time
import json
from typing import Dict, Any, Union
from app.llm.providers import invoke_model
from app.llm.shared.retrieval import split_text
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.prompt.prompt_star import DEFAULT_PROMPT_STAR
from app.llm.shared.map_fields import map_fields_with_opensearch
from app.llm.shared.organization_fields import clean_organization_fields
from app.utils.interactions.interaction_client import interaction_client
from app.utils.config.config_util import STAR_BUCKET_KEY_NAME, MAPPING_URL
from app.llm.shared.json_parser import extract_json_from_markdown, is_valid_json
from app.llm.shared.reference_cache import get_reference_data, format_reference_for_prompt
from app.llm.shared.vectorize import get_embedding, store_temp_embeddings, get_relevant_chunk
from app.schemas.star_mining_schemas import MiningResponse, InnovationDevelopmentResult, PolicyChangeResult, CapacityDevelopmentResult


logger = get_logger()


def format_mining_response(raw_response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format the mining response to ensure consistent structure with indicator-specific fields
    Accepts either raw JSON string or already parsed dict (after field mapping)
    """
    try:
        # If already a dict, use it directly (post field mapping)
        if isinstance(raw_response, dict):
            parsed_response = raw_response
        elif is_valid_json(raw_response):
            parsed_response = json.loads(raw_response)
        else:
            logger.warning(f"Invalid JSON received from LLM: {raw_response[:200]}...")
            return {
                "content": raw_response,
                "status": "partial_success", 
                "error": "LLM returned invalid JSON"
            }

        results = parsed_response.get("results", [])
        if not isinstance(results, list):
            results = []
        
        typed_results = []
        for result in results:
            indicator = result.get("indicator", "")
            
            try:
                if indicator == "Capacity Sharing for Development":
                    capacity_result = CapacityDevelopmentResult(**result)
                    typed_results.append(capacity_result)
                    
                elif indicator == "Policy Change":
                    policy_result = PolicyChangeResult(**result)
                    typed_results.append(policy_result)
                    
                elif indicator == "Innovation Development":
                    innovation_result = InnovationDevelopmentResult(**result)
                    typed_results.append(innovation_result)
                    
                else:
                    logger.warning(f"❌ Unknown indicator type: {indicator}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing result with indicator '{indicator}': {str(e)}")
                continue
        
        total_count = len(results)
        valid_count = len(typed_results)
        failed_count = total_count - valid_count
        
        if failed_count > 0:
            logger.warning(f"⚠️ {failed_count} of {total_count} results failed validation and will NOT be sent to STAR")
        
        if valid_count > 0:
            logger.info(f"✅ {valid_count} of {total_count} results validated successfully")
        elif total_count > 0:
            logger.error(f"❌ All {total_count} results failed validation - returning empty results")
        
        mining_response = MiningResponse(
            results=typed_results
        )
        
        return mining_response.model_dump(exclude_none=True)
        
    except Exception as e:
        logger.error(f"❌ Critical error formatting mining response: {str(e)}")
        
        return {
            "results": [],
            "status": "error",
            "error": f"Critical formatting error: {str(e)}"
        }


def process_document(bucket_name, file_key, prompt=DEFAULT_PROMPT_STAR, user_id: str = None):
    start_time = time.time()

    try:
        reference_file_regions = f"{STAR_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{STAR_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        reference_data = get_reference_data(
            bucket_name, STAR_BUCKET_KEY_NAME, reference_file_regions, reference_file_countries
        )

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣  Generating embeddings...")
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

        response_text = invoke_model(query).text
        
        extracted_json = extract_json_from_markdown(response_text)

        json_content = json.loads(extracted_json) if is_valid_json(extracted_json) else {"text": response_text}
        
        if isinstance(json_content, dict) and "results" in json_content:
            mapped_results = []
            for result in json_content["results"]:
                try:
                    mapped_result = map_fields_with_opensearch(result, MAPPING_URL)
                    clean_organization_fields(mapped_result)
                    mapped_results.append(mapped_result)
                    logger.info(f"🔗 Fields mapped for result with indicator: {result.get('indicator', 'Unknown')}")
                except Exception as map_error:
                    logger.warning(f"⚠️ Field mapping failed for result: {str(map_error)}")
                    mapped_results.append(result)
            
            json_content["results"] = mapped_results
            logger.info(f"🔗 Field mapping completed for {len(mapped_results)} results")

        end_time = time.time()
        elapsed_time = end_time - start_time

        formatted_response = format_mining_response(json_content)

        interaction_id = None
        if user_id:
            try:
                user_input = f"Document analysis request for: {file_key}"
                if isinstance(document_content, dict) and document_content.get("type") == "excel":
                    user_input += f" (Excel file with {len(document_content.get('chunks', []))} rows)"
                
                ai_output = json.dumps(formatted_response, indent=2, ensure_ascii=False)
                
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
                    display_name="STAR Text Mining Service",
                    service_description="A service that analyzes documents and extracts insights based on user prompts.",
                    context=tracking_context,
                    response_time_seconds=elapsed_time,
                    platform="STAR"
                )

                if interaction_response:
                    interaction_id = interaction_response.get('interaction_id')
                    logger.info(f"📊 Interaction tracked with ID: {interaction_id}")
                else:
                    logger.warning("⚠️ Failed to track interaction with interaction service")

            except Exception as tracking_error:
                logger.error(f"❌ Error tracking interaction: {str(tracking_error)}")

        logger.info(f"✅ Successfully generated response:\n{json.dumps(formatted_response, indent=2, ensure_ascii=False)}")
        logger.info(f"⏱️ Response time: {elapsed_time:.2f} seconds")

        result = {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": formatted_response
        }
        
        if interaction_id:
            result["interaction_id"] = interaction_id
        
        return result

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise