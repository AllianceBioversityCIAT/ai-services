import re
import json
import time
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.interactions.interaction_client import interaction_client

from ai.models.claude import invoke_model
from utils.logger.logger_util import get_logger
from utils.s3.s3_util import (
    read_document_from_s3,
    list_project_documents,
    save_project_response_json,
    get_project_response_json,
)
from ai.prompts.prompt_document_overview import DEFAULT_PROMPT_DOCUMENT_OVERVIEW
from utils.star.star_client import fetch_star_context, contract_id_from_project_folder
from utils.textract.textract_util import extract_text_from_s3, TEXTRACT_SUPPORTED_EXTENSIONS


logger = get_logger()

MODEL_ID = "claude-sonnet-4-6"

# Rough safety guard (~750K tokens at ~4 chars/token)
MAX_COMBINED_CHARS = 3_000_000


def _extract_document_text(bucket_name: str, file_key: str) -> tuple[str, str]:
    """
    Extract text from a document in S3.

    Automatically selects the extraction method based on the file extension:
    - Textract-supported formats (pdf, jpg, jpeg, png, tiff, tif) → Amazon Textract
    - Everything else (docx, txt, xlsx, xls, pptx) → standard parser

    Returns:
        Tuple of (extracted_text, extraction_method)
    """
    extension = file_key.lower().rsplit('.', 1)[-1]

    if extension in TEXTRACT_SUPPORTED_EXTENSIONS:
        logger.info(f"🔍 Format '{extension}' — using Amazon Textract for s3://{bucket_name}/{file_key}")
        text = extract_text_from_s3(bucket_name, file_key)
        return text, "textract"

    logger.info(f"📄 Format '{extension}' — using standard parser for s3://{bucket_name}/{file_key}")
    content = read_document_from_s3(bucket_name, file_key)

    if isinstance(content, dict) and content.get("type") == "excel":
        chunks = content.get("chunks", [])
        logger.info(f"📊 Flattening {len(chunks)} Excel rows to plain text")
        return "\n".join(chunks), "standard"

    return content, "standard"


def _extract_documents_parallel(bucket_name: str, file_keys: list[str]) -> list[dict]:
    """Extract text from multiple documents in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=len(file_keys)) as executor:
        futures = {
            executor.submit(_extract_document_text, bucket_name, key): key
            for key in file_keys
        }
        for future in as_completed(futures):
            file_key = futures[future]
            text, extraction_method = future.result()
            results.append({
                "file_key": file_key,
                "file_name": file_key.rsplit("/", 1)[-1],
                "text": text,
                "extraction_method": extraction_method,
                "character_count": len(text),
            })

    results.sort(key=lambda item: item["file_key"])
    return results


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if the model adds them."""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _build_combined_document_text(documents: list[dict]) -> str:
    """Combine extracted document texts with clear separators."""
    sections = []
    for index, doc in enumerate(documents, start=1):
        file_name = doc["file_key"].rsplit("/", 1)[-1]
        sections.append(
            f"{'=' * 80}\n"
            f"DOCUMENT {index}: {file_name}\n"
            f"{'=' * 80}\n"
            f"{doc['text']}"
        )
    return "\n\n".join(sections)


def _build_query(
    combined_text: str,
    prompt: str,
    document_count: int,
    project_context: Optional[str] = None,
    results_context: Optional[str] = None,
) -> str:
    separator = "=" * 80

    source_descriptions = []
    if project_context:
        source_descriptions.append("Structured project information from STAR (description, donor, unit, SDGs)")
    if results_context:
        source_descriptions.append("Metadata about the project's reported results in STAR")
    source_descriptions.append("Text extracted from one or more documents uploaded as project evidence")

    numbered_sources = "\n".join(
        f"{index}. {description}" for index, description in enumerate(source_descriptions, start=1)
    )

    preamble = (
        f"## ROLE:\n"
        f"You are an expert analyst specializing in research, development, and policy projects.\n\n"
        f"{separator}\n\n"
        f"## CONTEXT YOU WILL RECEIVE:\n"
        f"You will receive context from the following source(s), all belonging to the SAME project:\n"
        f"{numbered_sources}\n\n"
        f"Review all of the following context, then follow the task instructions at the end of this prompt.\n"
    )

    sections = [preamble]

    if project_context:
        sections.append(
            f"-------\n\n"
            f"### PROJECT INFORMATION:\n\n"
            f"{project_context}"
        )

    if results_context:
        sections.append(
            f"\n-------\n\n"
            f"### PROJECT RESULTS:\n\n"
            f"{results_context}"
        )

    sections.append(
        f"\n-------\n\n"
        f"### UPLOADED PROJECT EVIDENCE ({document_count} file(s)):\n\n"
        f"{combined_text}"
    )

    return (
        f"{chr(10).join(sections)}\n\n"
        f"{separator}\n"
        f"{prompt}"
    )


def process_project_overview(
    bucket_name: str,
    project_folder: str,
    prompt: str = DEFAULT_PROMPT_DOCUMENT_OVERVIEW,
    user_id: Optional[str] = None,
    token: Optional[str] = None,
) -> dict:
    """
    Generate a structured project overview from documents in an S3 folder.

    Steps:
      1. List supported documents in the project folder (1-3 files)
      2. Extract text from all documents in parallel
      3. Combine extracted text and invoke the LLM
      4. Parse and return the structured project overview

    Args:
        bucket_name: S3 bucket containing the project documents
        project_folder: S3 folder prefix for the project
        prompt: Override the default project overview prompt
        user_id: Optional user ID for future interaction tracking
        token: STAR access token for authenticated STAR API calls

    Returns:
        dict with overview, time_taken, project_folder, bucket_name, documents_processed
    """
    start_time = time.time()
    contract_id = contract_id_from_project_folder(project_folder)
    logger.info(
        f"🚀 Starting project overview for s3://{bucket_name}/{project_folder} "
        f"(contract_id={contract_id})"
    )

    project_context, results_context = fetch_star_context(contract_id, token=token)

    file_keys = list_project_documents(bucket_name, project_folder)
    documents = _extract_documents_parallel(bucket_name, file_keys)

    total_chars = sum(doc["character_count"] for doc in documents)
    logger.info(
        f"✅ Text extraction complete — {len(documents)} document(s), "
        f"{total_chars} total characters"
    )

    if total_chars > MAX_COMBINED_CHARS:
        raise ValueError(
            f"Combined document text exceeds the allowed limit "
            f"({total_chars} chars, max {MAX_COMBINED_CHARS})"
        )

    combined_text = _build_combined_document_text(documents)
    query = _build_query(
        combined_text,
        prompt,
        len(documents),
        project_context=project_context,
        results_context=results_context,
    )

    logger.info(f"📝 Full prompt sent to model:\n{query}")

    response_text = invoke_model(query)

    clean_response = _strip_markdown_fences(response_text)
    try:
        overview = json.loads(clean_response)
        logger.info("✅ Model response parsed successfully as JSON")
    except json.JSONDecodeError:
        logger.warning("Model response is not valid JSON — returning raw text in overview")
        overview = {"raw_response": response_text}

    elapsed_time = time.time() - start_time
    logger.info(f"⏱️ Project overview completed in {elapsed_time:.2f} seconds")

    interaction_id = None
    if user_id:
        try:
            file_names = [doc["file_key"].rsplit("/", 1)[-1] for doc in documents]
            user_input = (
                f"Project overview request for: {project_folder.strip('/')} "
                f"({len(documents)} document(s): {', '.join(file_names)})"
            )

            ai_output = json.dumps(overview, indent=2, ensure_ascii=False)

            tracking_context = {
                "bucket_name": bucket_name,
                "project_folder": project_folder.strip('/'),
                "contract_id": contract_id,
                "star_project_context_included": project_context is not None,
                "star_results_context_included": results_context is not None,
                "star_token_provided": bool(token),
                "documents_processed": [
                    {
                        "file_key": doc["file_key"],
                        "file_name": doc["file_name"],
                        "extraction_method": doc["extraction_method"],
                        "character_count": doc["character_count"],
                    }
                    for doc in documents
                ],
                "document_count": len(documents),
                "total_characters": total_chars,
                "prompt_used": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "prompt_full_length": len(prompt),
                "model_used": MODEL_ID,
                "processing_steps": [
                    "star_metadata_fetch",
                    "document_listing",
                    "parallel_text_extraction",
                    "llm_processing",
                ],
            }

            interaction_response = interaction_client.track_interaction(
                user_id=user_id,
                user_input=user_input,
                ai_output=ai_output,
                service_name="ai-insights",
                display_name="AI Insights Service - Project Overview",
                service_description=(
                    "A service that generates structured project overviews "
                    "from documents stored in S3."
                ),
                context=tracking_context,
                response_time_seconds=elapsed_time,
                platform="STAR",
            )

            if interaction_response:
                interaction_id = interaction_response.get("interaction_id")
                logger.info(f"✅ Interaction tracked with ID: {interaction_id}")
            else:
                logger.warning("Failed to track interaction with interaction service")

        except Exception as tracking_error:
            logger.error(f"Error tracking interaction: {str(tracking_error)}")

    result = {
        "overview": overview,
        "time_taken": f"{elapsed_time:.2f}",
        "project_folder": project_folder.strip('/'),
        "bucket_name": bucket_name,
        "documents_processed": [
            {
                "file_key": doc["file_key"],
                "file_name": doc["file_name"],
                "extraction_method": doc["extraction_method"],
                "character_count": doc["character_count"],
            }
            for doc in documents
        ],
        "interaction_id": interaction_id,
        "status": "success",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        save_project_response_json(bucket_name, project_folder, result)
    except Exception as cache_error:
        logger.error(f"Failed to save cached project overview: {str(cache_error)}")

    return result


def get_cached_project_overview(bucket_name: str, project_folder: str) -> dict | None:
    """
    Retrieve a previously generated project overview from response.json in S3.

    Returns:
        Cached response dict if found, otherwise None
    """
    logger.info(f"🔍 Fetching cached project overview for s3://{bucket_name}/{project_folder}")
    return get_project_response_json(bucket_name, project_folder)
