"""REST API endpoints for AI Insights Service."""

import traceback
from fastapi import APIRouter, HTTPException, status
from utils.logger.logger_util import get_logger
from modules.document_overview.processing import process_project_overview
from utils.notification.notification_service import notification_service
from api.models import (
    DocumentOverviewRequest,
    DocumentOverviewResponse,
    ProcessedDocument,
    ErrorResponse,
)

logger = get_logger()
router = APIRouter()

APP_NAME = "AI Insights Service (STAR)"


@router.post(
    "/api/document-overview",
    response_model=DocumentOverviewResponse,
    tags=["Document Overview"],
    summary="Generate a structured overview of a project",
    description="""
    Generate a comprehensive, structured overview of a project based on documents
    stored in an Amazon S3 folder.

    The service lists all supported documents in the project folder (1 to 3 files),
    extracts their text in parallel, and uses an LLM (Claude via AWS Bedrock) to
    produce a single synthesized project overview.

    **Supported document formats:**
    - **PDF** — via Amazon Textract
    - **DOCX** — Microsoft Word (Mammoth)
    - **TXT** — Plain text
    - **XLSX / XLS** — Excel spreadsheets
    - **PPTX** — PowerPoint presentations
    - **JPEG, PNG, TIFF** — Images via Amazon Textract

    The extraction method is selected automatically based on each file extension.
    """,
    response_description="Structured project overview",
    responses={
        200: {
            "description": "Successfully generated project overview",
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
                        "details": "No supported documents found in s3://bucket/project-folder"
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
    Generate a structured project overview from documents in an S3 folder.

    - **bucket_name**: S3 bucket containing the project documents
    - **project_folder**: S3 folder prefix for the project (1-3 documents)
    - **user_id**: Optional user ID for interaction tracking
    """
    try:
        logger.info(
            f"Project overview request — "
            f"s3://{request.bucket_name}/{request.project_folder} "
            f"(user={request.user_id})"
        )

        result = process_project_overview(
            bucket_name=request.bucket_name,
            project_folder=request.project_folder,
            user_id=request.user_id,
        )

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name=APP_NAME,
            color="#36a64f",
            title="Project Overview Generated",
            message=(
                f"Successfully generated project overview for project: *{result['project_folder']}*\n"
                f"*User:* {request.user_id or 'N/A'}"
            ),
            time_taken=f"*Time taken:* {result['time_taken']} seconds",
            priority="Low",
        )

        return DocumentOverviewResponse(
            overview=result["overview"],
            time_taken=result["time_taken"],
            project_folder=result["project_folder"],
            bucket_name=result["bucket_name"],
            documents_processed=[
                ProcessedDocument(**doc) for doc in result["documents_processed"]
            ],
            interaction_id=result.get("interaction_id"),
            status="success",
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name=APP_NAME,
            color="#FF0000",
            title="Project Overview Failed",
            message=(
                f"Validation error for project overview: *{request.project_folder}*\n"
                f"*Error:* {str(e)}\n"
                f"*User:* {request.user_id or 'N/A'}"
            ),
            time_taken="*Time taken:* N/A",
            priority="High",
        )
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
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name=APP_NAME,
            color="#FF0000",
            title="Project Overview Failed",
            message=(
                f"Error generating project overview: *{request.project_folder}*\n"
                f"*Bucket:* {request.bucket_name}\n"
                f"*Error:* {str(e)}\n"
                f"*User:* {request.user_id or 'N/A'}"
            ),
            time_taken="*Time taken:* N/A",
            priority="High",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "status": "error",
                "details": str(e),
            }
        )
