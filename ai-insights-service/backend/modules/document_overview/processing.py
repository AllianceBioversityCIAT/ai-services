import re
import json
import time
from typing import Optional

from ai.models.claude import invoke_model
from utils.logger.logger_util import get_logger
from utils.s3.s3_util import read_document_from_s3
from ai.prompts.prompt_document_overview import DEFAULT_PROMPT_DOCUMENT_OVERVIEW
from utils.textract.textract_util import extract_text_from_s3, TEXTRACT_SUPPORTED_EXTENSIONS

logger = get_logger()


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
        logger.info(f"Format '{extension}' — using Amazon Textract for s3://{bucket_name}/{file_key}")
        text = extract_text_from_s3(bucket_name, file_key)
        return text, "textract"

    logger.info(f"Format '{extension}' — using standard parser for s3://{bucket_name}/{file_key}")
    content = read_document_from_s3(bucket_name, file_key)

    # Excel files return a dict with chunks; flatten to plain text
    if isinstance(content, dict) and content.get("type") == "excel":
        chunks = content.get("chunks", [])
        logger.info(f"Flattening {len(chunks)} Excel rows to plain text")
        return "\n".join(chunks), "standard"

    return content, "standard"


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if the model adds them."""
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _build_query(document_text: str, prompt: str) -> str:
    separator = "=" * 80
    return (
        f"{separator}\n"
        f"DOCUMENT CONTENT:\n"
        f"{separator}\n"
        f"{document_text}\n\n"
        f"{separator}\n\n"
        f"{prompt}"
    )


def process_document_overview(
    bucket_name: str,
    file_key: str,
    prompt: str = DEFAULT_PROMPT_DOCUMENT_OVERVIEW,
    user_id: Optional[str] = None,
) -> dict:
    """
    Generate a structured overview of a document stored in S3.

    The extraction method is chosen automatically based on the file extension:
    Textract-supported formats (pdf, jpg, png, tiff) use Amazon Textract;
    all other formats (docx, txt, xlsx, pptx) use the standard parser.

    Steps:
      1. Extract document text (auto-selected method)
      2. Build the model prompt with the extracted text
      3. Invoke the LLM
      4. Parse and return the structured overview

    Args:
        bucket_name: S3 bucket containing the document
        file_key: S3 object key of the document
        prompt: Override the default overview prompt
        user_id: Optional user ID for future interaction tracking

    Returns:
        dict with keys: overview, time_taken, file_key, bucket_name, extraction_method
    """
    start_time = time.time()
    logger.info(f"Starting document overview for s3://{bucket_name}/{file_key}")

    # Step 1 — Extract text (method chosen automatically by file extension)
    document_text, extraction_method = _extract_document_text(bucket_name, file_key)
    logger.info(
        f"Text extraction complete — {len(str(document_text))} characters "
        f"(method: {extraction_method})"
    )

    # Step 2 — Build query
    query = _build_query(str(document_text), prompt)

    # Step 3 — Invoke model
    response_text = invoke_model(query)

    # Step 4 — Parse JSON response
    clean_response = _strip_markdown_fences(response_text)
    try:
        overview = json.loads(clean_response)
        logger.info("Model response parsed successfully as JSON")
    except json.JSONDecodeError:
        logger.warning("Model response is not valid JSON — returning raw text in overview")
        overview = {"raw_response": response_text}

    elapsed_time = time.time() - start_time
    logger.info(f"Document overview completed in {elapsed_time:.2f} seconds")

    return {
        "overview": overview,
        "time_taken": f"{elapsed_time:.2f}",
        "file_key": file_key,
        "bucket_name": bucket_name,
        "extraction_method": extraction_method,
    }
