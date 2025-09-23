import time
import json
import boto3
from typing import Dict, Any
from app.utils.logger.logger_util import get_logger
from app.utils.s3.s3_util import read_document_from_s3
from app.utils.prompt.prompt_star import DEFAULT_PROMPT_STAR
from app.utils.prompt.prompt_prms import DEFAULT_PROMPT_PRMS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.utils.config.config_util import BR, STAR_BUCKET_KEY_NAME, PRMS_BUCKET_KEY_NAME
from app.schemas.mining_schemas import MiningResponse, ErrorResponse, InnovationDevelopmentResult, PolicyChangeResult, CapacityDevelopmentResult
from app.llm.vectorize import (get_embedding,
                               check_reference_exists,
                               store_reference_embeddings,
                               store_temp_embeddings,
                               get_all_reference_data,
                               get_relevant_chunk
                               )


logger = get_logger()

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    aws_access_key_id=BR['aws_access_key'],
    aws_secret_access_key=BR['aws_secret_key'],
    region_name='us-east-1'
)


def split_text(text):
    logger.info("✂️  Dividing the text into fragments...")
    
    if isinstance(text, dict) and text.get("type") == "excel":
        logger.info(f"📊 Using Excel rows as chunks: {len(text['chunks'])} rows")
        return text["chunks"]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=8000, chunk_overlap=1500)
    return text_splitter.split_text(text)


def invoke_model(prompt, max_tokens=5000):
    try:
        logger.info("🚀 Invoking the model...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_k": 250,
            "top_p": 0.999,
            "stop_sequences": [],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{prompt}"}
                    ]
                }
            ]
        }
        response = bedrock_runtime.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        return json.loads(response['body'].read())['content'][0]['text']

    except Exception as e:
        logger.error(f"❌ Error invoking the model: {str(e)}")
        raise


def is_valid_json(text):
    """Check if the text is a valid JSON string"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def initialize_reference_data(bucket_name, file_key_regions, file_key_countries):
    """Initialize reference data if it doesn't exist"""
    try:
        if check_reference_exists():
            logger.info("✅ Reference data already exists in the database")
            return True

        logger.info("🔄 Initializing reference data...")

        document_content_regions = read_document_from_s3(bucket_name, file_key_regions)
        document_content_countries = read_document_from_s3(bucket_name, file_key_countries)

        if isinstance(document_content_regions, dict) and document_content_regions.get("type") == "excel":
            regions_chunks = document_content_regions["chunks"]
        else:
            regions_chunks = [document_content_regions]
         
        if isinstance(document_content_countries, dict) and document_content_countries.get("type") == "excel":
            countries_chunks = document_content_countries["chunks"]
        else:
            countries_chunks = [document_content_countries]

        logger.info(f"📊 Generating embeddings for {len(regions_chunks)} region chunks and {len(countries_chunks)} country chunks...")
        
        regions_embeddings = [get_embedding(chunk) for chunk in regions_chunks]
        countries_embeddings = [get_embedding(chunk) for chunk in countries_chunks]

        all_content = regions_chunks + countries_chunks
        all_embeddings = regions_embeddings + countries_embeddings

        store_reference_embeddings(all_content, all_embeddings)

        logger.info("✅ Reference data initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error initializing reference data: {str(e)}")
        raise


def format_mining_response(raw_response: str) -> Dict[str, Any]:
    """
    Format the mining response to ensure consistent structure with indicator-specific fields
    """
    try:
        if is_valid_json(raw_response):
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
                    logger.warning(f"Unknown indicator type: {indicator}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing result with indicator '{indicator}': {str(e)}")
                continue
        
        mining_response = MiningResponse(
            results=typed_results
        )
        
        return mining_response.model_dump(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Error formatting mining response: {str(e)}")
        
        error_response = ErrorResponse(
            error=f"Error formatting response: {str(e)}"
        )
        return error_response.model_dump(exclude_none=True)


def process_document(bucket_name, file_key, prompt=DEFAULT_PROMPT_STAR):
    start_time = time.time()
    print(prompt)

    try:
        reference_file_regions = f"{STAR_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{STAR_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        logger.info("#️⃣ Generating embeddings...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        db, temp_table_name, document_name = store_temp_embeddings(chunks, embeddings, file_key)

        all_reference_data = get_all_reference_data()

        relevant_chunks = get_relevant_chunk(prompt, db, temp_table_name, document_name)

        context = all_reference_data + relevant_chunks

        query = f"""
        Based on this context:\n{context}\n\n
        Answer the question:\n{prompt}
        """

        response_text = invoke_model(query)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # formatted_response = format_mining_response(
        #     raw_response=response_text
        # )

        # logger.info(f"✅ Successfully generated response:\n{json.dumps(formatted_response, indent=2)}")
        logger.info(f"✅ Successfully generated response:\n{response_text}")
        logger.info(f"⏱️ Response time: {elapsed_time:.2f} seconds")

        return {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json.loads(response_text) if is_valid_json(response_text) else {"text": response_text}
            # "json_content": formatted_response
        }

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise


def process_document_prms(bucket_name, file_key, prompt=DEFAULT_PROMPT_PRMS):
    """Process document for PRMS project - identical functionality to process_document"""
    start_time = time.time()
    print(f"PRMS Processing: {prompt}")

    try:
        reference_file_regions = f"{PRMS_BUCKET_KEY_NAME}/clarisa_regions.xlsx"
        reference_file_countries = f"{PRMS_BUCKET_KEY_NAME}/clarisa_countries.xlsx"
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)

        if isinstance(document_content, dict) and document_content.get("type") == "excel":
            logger.info(f"📊 Excel content detected with {len(document_content['chunks'])} chunks")
            logger.info(f"📝 First 3 chunks: {document_content['chunks'][:3]}")
        else:
            logger.info(f"📄 Text content length: {len(str(document_content))}")

        chunks = split_text(document_content)

        if isinstance(document_content, dict) and document_content.get("type") == "excel":
            logger.info(f"📊 Excel document processed into {len(chunks)} row chunks")
        else:
            logger.info(f"📄 Document split into {len(chunks)} chunks")

        logger.info("#️⃣ Generating embeddings for PRMS...")
        embeddings = [get_embedding(chunk) for chunk in chunks]

        db, temp_table_name, document_name = store_temp_embeddings(chunks, embeddings, file_key)

        all_reference_data = get_all_reference_data()

        relevant_chunks = get_relevant_chunk(prompt, db, temp_table_name, document_name)

        context = all_reference_data + relevant_chunks

        query = f"""
        Based on this context:\n{context}\n\n
        Answer the question:\n{prompt}
        """

        response_text = invoke_model(query)

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"✅ Successfully generated PRMS response:\n{response_text}")
        logger.info(f"⏱️ PRMS Response time: {elapsed_time:.2f} seconds")

        return {
            "content": response_text,
            "time_taken": f"{elapsed_time:.2f}",
            "json_content": json.loads(response_text) if is_valid_json(response_text) else {"text": response_text},
            "project": "PRMS"
        }

    except Exception as e:
        logger.error(f"❌ PRMS Error: {str(e)}")
        raise