import time
import json
from app.utils.logger.logger_util import get_logger
from app.llm.vectorize import get_all_reference_data
from app.utils.s3.s3_util import read_document_from_s3
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.prompt.bulk_upload_capdev_prompt import PROMPT_BULK_UPLOAD_CAPDEV
from app.llm.vectorize import get_embedding, store_temp_embeddings, get_relevant_chunk
from app.llm.mining import initialize_reference_data, split_text, invoke_model, is_valid_json

logger = get_logger()


def process_excel_in_batches(chunks, batch_size=5):
    """
    Split Excel chunks into batches of specified size
    """
    batches = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batches.append(batch)
    return batches


def process_single_batch(batch_chunks, prompt, batch_number, all_reference_data):
    """
    Process a single batch of chunks (thread-safe)
    """
    logger.info(f"🔄 [Thread-{batch_number}] Processing batch {batch_number} with {len(batch_chunks)} rows...")
    
    try:
        batch_data = "\n".join(batch_chunks)
        
        if isinstance(all_reference_data, list):
            reference_text = "\n".join(all_reference_data)
        elif isinstance(all_reference_data, str):
            reference_text = all_reference_data
        else:
            logger.warning(f"⚠️ [Thread-{batch_number}] Unexpected reference_data type: {type(all_reference_data)}")
            reference_text = str(all_reference_data)
        
        context = reference_text + f"\n\nBatch Data to Process:\n{batch_data}"

        query = f"""
        Based on this context:\n{context}\n\n
        Do the following:\n{prompt}
        """

        response_text = invoke_model(query, max_tokens=8000)
        
        logger.info(f"✅ [Thread-{batch_number}] Batch {batch_number} processed successfully")
        
        if is_valid_json(response_text):
            parsed_result = json.loads(response_text)
            
            if isinstance(parsed_result, dict) and "results" in parsed_result:
                for result in parsed_result["results"]:
                    if isinstance(result, dict):
                        result["batch_number"] = batch_number
            return parsed_result
        
        else:
            logger.warning(f"⚠️ [Thread-{batch_number}] Batch {batch_number} response is not valid JSON")
            cleaned_response = response_text.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
            
            if is_valid_json(cleaned_response):
                parsed_result = json.loads(cleaned_response)
                if isinstance(parsed_result, dict) and "results" in parsed_result:
                    for result in parsed_result["results"]:
                        if isinstance(result, dict):
                            result["batch_number"] = batch_number
                return parsed_result
            
            return {"results": [{"text": response_text, "batch": batch_number, "parsing_error": True}]}
            
    except Exception as e:
        logger.error(f"❌ [Thread-{batch_number}] Error processing batch {batch_number}: {str(e)}")
        return {"results": [{"error": str(e), "batch": batch_number}]}


def merge_batch_results(batch_results_with_numbers):
    """
    Combine all batch results into a single JSON, maintaining the original order.
    """
    sorted_results = sorted(batch_results_with_numbers, key=lambda x: x[1])
    
    merged_results = {"results": []}
    
    for batch_result, batch_number in sorted_results:
        if isinstance(batch_result, dict):
            if "results" in batch_result and isinstance(batch_result["results"], list):
                merged_results["results"].extend(batch_result["results"])
            else:
                merged_results["results"].append(batch_result)
        else:
            merged_results["results"].append({"data": batch_result, "batch": batch_number})
    
    logger.info(f"📊 Merged {len(merged_results['results'])} total results from all batches")
    return merged_results


def process_document_capdev(bucket_name, file_key, prompt=PROMPT_BULK_UPLOAD_CAPDEV, max_workers=20):
    start_time = time.time()

    try:
        reference_file_regions = "star/text-mining/files/clarisa_regions.xlsx"
        reference_file_countries = "star/text-mining/files/clarisa_countries.xlsx"
        initialize_reference_data(
            bucket_name, reference_file_regions, reference_file_countries)

        document_content = read_document_from_s3(bucket_name, file_key)
        chunks = split_text(document_content)

        all_reference_data = get_all_reference_data()

        if isinstance(document_content, dict) and document_content.get("type") == "excel":
            logger.info(f"📊 Excel file detected with {len(chunks)} rows. Processing in parallel batches of 10...")

            batches = process_excel_in_batches(chunks, batch_size=5)
            logger.info(f"📦 Created {len(batches)} batches for parallel processing with {max_workers} workers")
            
            batch_results_with_numbers = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_batch = {}
                for i, batch in enumerate(batches, 1):
                    future = executor.submit(
                        process_single_batch,
                        batch, prompt, i, all_reference_data
                    )
                    future_to_batch[future] = i
                
                for future in as_completed(future_to_batch):
                    batch_number = future_to_batch[future]
                    try:
                        batch_result = future.result()
                        batch_results_with_numbers.append((batch_result, batch_number))
                        logger.info(f"✅ Completed batch {batch_number}/{len(batches)}")
                    except Exception as e:
                        logger.error(f"❌ Exception in batch {batch_number}: {str(e)}")
                        error_result = {"results": [{"error": str(e), "batch": batch_number}]}
                        batch_results_with_numbers.append((error_result, batch_number))
            
            final_result = merge_batch_results(batch_results_with_numbers)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            logger.info(f"✅ Successfully processed all {len(batches)} batches in parallel")
            logger.info(f"📊 Total results: {len(final_result.get('results', []))}")
            logger.info(f"⏱️ Total processing time: {elapsed_time:.2f} seconds")
            logger.info(f"🚀 Used {max_workers} parallel workers")
            logger.info(f"⚡ Processing mode: SIMPLIFIED (no embeddings)")
            
            return {
                "content": final_result,
                "time_taken": f"{elapsed_time:.2f}",
                "json_content": json.dumps(final_result, ensure_ascii=False, indent=2),
                "batches_processed": len(batches),
                "total_rows": len(chunks),
                "workers_used": max_workers
            }
            
        else:
            logger.info(f"📄 Non-Excel file detected. Using standard processing...")
            logger.info("#️⃣ Generating embeddings...")
            
            embeddings = [get_embedding(chunk) for chunk in chunks]
            db, temp_table_name, document_name = store_temp_embeddings(chunks, embeddings, file_key)
            relevant_chunks = get_relevant_chunk(prompt, db, temp_table_name, document_name)
            
            if isinstance(all_reference_data, list):
                context = "\n".join(all_reference_data) + relevant_chunks
            else:
                context = str(all_reference_data) + relevant_chunks

            query = f"""
            Based on this context:\n{context}\n\n
            Do the following:\n{prompt}
            """

            response_text = invoke_model(query, max_tokens=4000)

            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"✅ Successfully generated response:\n{response_text}")
            logger.info(f"⏱️ Response time: {elapsed_time:.2f} seconds")

            return {
                "content": response_text,
                "time_taken": f"{elapsed_time:.2f}",
                "json_content": json.loads(response_text) if is_valid_json(response_text) else {"text": response_text}
            }

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise