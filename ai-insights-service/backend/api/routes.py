"""REST API endpoints for AI Insights Service."""

import traceback
from fastapi import APIRouter, HTTPException, status
from utils.logger.logger_util import get_logger
from modules.document_overview.processing import process_document_overview
from api.models import (
    DocumentOverviewRequest,
    DocumentOverviewResponse,
    ErrorResponse,
)

logger = get_logger()
router = APIRouter()


@router.post(
    "/api/document-overview",
    response_model=DocumentOverviewResponse,
    tags=["Document Overview"],
    summary="Generate a structured overview of a document",
    description="""
    Generate a comprehensive, structured overview of a document stored in Amazon S3.

    The service reads the document, extracts its text, and uses an LLM (Claude via AWS Bedrock)
    to produce a structured JSON overview with fields such as title, summary, key findings,
    authors, organizations, recommendations, and more.

    **Supported document formats:**
    - **PDF** — via Amazon Textract (handles both native and scanned)
    - **DOCX** — Microsoft Word
    - **TXT** — Plain text
    - **XLSX / XLS** — Excel spreadsheets
    - **PPTX** — PowerPoint presentations
    - **JPEG, PNG, TIFF** — Images via Amazon Textract

    The extraction method is selected automatically based on the file extension.
    """,
    response_description="Structured document overview",
    responses={
        200: {
            "description": "Successfully generated document overview",
            "model": DocumentOverviewResponse
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid parameters",
                        "status": "error",
                        "details": "File format 'mp4' is not supported."
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Internal server error",
                        "status": "error",
                        "details": "An unexpected error occurred. Please check the logs."
                    }
                }
            }
        }
    }
)
async def document_overview(request: DocumentOverviewRequest) -> DocumentOverviewResponse:
    """
    Generate a structured document overview from a file stored in S3.

    - **bucket_name**: S3 bucket containing the document
    - **file_key**: S3 object key (path) of the document
    - **user_id**: Optional user ID for interaction tracking
    """
    try:
        logger.info(
            f"Document overview request — "
            f"s3://{request.bucket_name}/{request.file_key} "
            f"(user={request.user_id})"
        )

        result = process_document_overview(
            bucket_name=request.bucket_name,
            file_key=request.file_key,
            user_id=request.user_id,
        )

        return DocumentOverviewResponse(
            overview=result["overview"],
            time_taken=result["time_taken"],
            file_key=result["file_key"],
            bucket_name=result["bucket_name"],
            extraction_method=result["extraction_method"],
            interaction_id=result.get("interaction_id"),
            status="success",
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid parameters",
                "status": "error",
                "details": str(e),
            }
        )

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Unexpected error: {str(e)}\n{tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "status": "error",
                "details": str(e),
            }
        )
