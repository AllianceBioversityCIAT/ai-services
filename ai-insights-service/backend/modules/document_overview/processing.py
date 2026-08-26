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
    MAX_PROJECT_DOCUMENTS,
)
from modules.prompts.processing import get_active_sections, render_sections
from ai.prompts.registry import (
    PROJECT_OVERVIEW_PROMPT_ID,
    PROMPT_SECTIONS,
    get_default_sections,
)
from utils.star.star_client import fetch_star_context, contract_id_from_project_folder
from utils.textract.textract_util import extract_text_from_s3, TEXTRACT_SUPPORTED_EXTENSIONS


logger = get_logger()

MODEL_ID = "claude-sonnet-4-6"

# Rough safety guard (~750K tokens at ~4 chars/token)
MAX_COMBINED_CHARS = 3_000_000

# Lower document limit when free-text user input is also part of the context
MAX_PROJECT_DOCUMENTS_WITH_TEXT = 2


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
    if not file_keys:
        return []

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


def _build_context_variables(
    combined_text: str,
    document_count: int,
    project_context: Optional[str] = None,
    results_context: Optional[str] = None,
    text: Optional[str] = None,
) -> dict[str, str]:
    """
    Build the replacement value for every `{variable}` in the prompt template.

    An absent source gets an explicit "not available" sentence rather than an empty
    string: a bare heading with nothing under it invites the model to invent content.
    """
    source_descriptions = []
    if project_context:
        source_descriptions.append("Structured project information from STAR (description, donor, unit, SDGs)")
    if results_context:
        source_descriptions.append("Metadata about the project's reported results in STAR")
    if document_count > 0:
        source_descriptions.append("Text extracted from one or more documents uploaded as project evidence")
    if text:
        source_descriptions.append("Free-text input provided by the user")

    numbered_sources = "\n".join(
        f"{index}. {description}" for index, description in enumerate(source_descriptions, start=1)
    )

    if document_count > 0:
        uploaded_evidence = f"{document_count} file(s) were uploaded:\n\n{combined_text}"
    else:
        # Kept source-agnostic on purpose: naming STAR here would point the model at
        # metadata that may itself be absent (e.g. when only user text was provided).
        uploaded_evidence = (
            "No documents were uploaded for this project. Base the overview entirely on the "
            "other context provided above."
        )

    return {
        "available_context_sources": numbered_sources,
        "project_information": project_context or "No STAR project information is available for this project.",
        "project_results": results_context or "No STAR results metadata is available for this project.",
        "uploaded_evidence": uploaded_evidence,
        "user_input": text or "No additional user input was provided.",
    }


def _build_query(
    combined_text: str,
    sections: dict[str, str],
    document_count: int,
    project_context: Optional[str] = None,
    results_context: Optional[str] = None,
    text: Optional[str] = None,
) -> str:
    """Assemble the four prompt sections and substitute the context variables."""
    values = _build_context_variables(
        combined_text,
        document_count,
        project_context=project_context,
        results_context=results_context,
        text=text,
    )
    return render_sections(sections, values)


def process_project_overview(
    bucket_name: str,
    project_folder: str,
    sections: Optional[dict[str, str]] = None,
    user_id: Optional[str] = None,
    token: Optional[str] = None,
    text: Optional[str] = None,
) -> dict:
    """
    Generate a structured project overview from documents in an S3 folder.

    Steps:
      1. Resolve the prompt sections managed through the STAR Prompt Manager
      2. List supported documents in the project folder (0-3 files, or 0-2 if `text` is provided)
      3. Extract text from all documents in parallel
      4. Combine extracted text and invoke the LLM
      5. Parse and return the structured project overview

    Args:
        bucket_name: S3 bucket containing the project documents
        project_folder: S3 folder prefix for the project
        sections: Override the prompt sections; defaults to the stored user version,
            falling back to the code-defined defaults
        user_id: Optional user ID for future interaction tracking
        token: STAR access token for authenticated STAR API calls
        text: Optional free-text input from the user, included in the AI context

    Returns:
        dict with overview, time_taken, project_folder, bucket_name, documents_processed
    """
    start_time = time.time()

    if sections is None:
        sections = get_active_sections(PROJECT_OVERVIEW_PROMPT_ID)
    contract_id = contract_id_from_project_folder(project_folder)
    logger.info(
        f"🚀 Starting project overview for s3://{bucket_name}/{project_folder} "
        f"(contract_id={contract_id})"
    )

    project_context, results_context = fetch_star_context(contract_id, token=token)

    max_documents = MAX_PROJECT_DOCUMENTS_WITH_TEXT if text else MAX_PROJECT_DOCUMENTS
    file_keys = list_project_documents(bucket_name, project_folder, max_documents=max_documents)

    # Free-text input counts as a source on its own: a request only fails when there is
    # nothing at all to work from.
    if not file_keys and not (project_context or results_context) and not text:
        raise ValueError(
            f"No supported documents found in s3://{bucket_name}/{project_folder}, "
            f"no STAR context is available for contract {contract_id}, "
            f"and no text input was provided"
        )

    if not file_keys:
        remaining_sources = []
        if project_context or results_context:
            remaining_sources.append("STAR context")
        if text:
            remaining_sources.append("user text input")
        logger.info(
            f"📭 No documents found in s3://{bucket_name}/{project_folder} — "
            f"generating overview from {' and '.join(remaining_sources)} only"
        )

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
        sections,
        len(documents),
        project_context=project_context,
        results_context=results_context,
        text=text,
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
            prompt_template = "\n\n".join(sections[section] for section in PROMPT_SECTIONS)
            file_names = [doc["file_key"].rsplit("/", 1)[-1] for doc in documents]
            documents_summary = (
                f"{len(documents)} document(s): {', '.join(file_names)}"
                if documents else "no documents (STAR context only)"
            )
            user_input = (
                f"Project overview request for: {project_folder.strip('/')} "
                f"({documents_summary})"
            )

            ai_output = json.dumps(overview, indent=2, ensure_ascii=False)

            tracking_context = {
                "bucket_name": bucket_name,
                "project_folder": project_folder.strip('/'),
                "contract_id": contract_id,
                "star_project_context_included": project_context is not None,
                "star_results_context_included": results_context is not None,
                "star_token_provided": bool(token),
                "user_text_provided": bool(text),
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
                "prompt_id": PROJECT_OVERVIEW_PROMPT_ID,
                "prompt_used": prompt_template[:500] + "..." if len(prompt_template) > 500 else prompt_template,
                "prompt_full_length": len(prompt_template),
                "prompt_is_modified": sections != get_default_sections(PROJECT_OVERVIEW_PROMPT_ID),
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
        "text": text or "",
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
