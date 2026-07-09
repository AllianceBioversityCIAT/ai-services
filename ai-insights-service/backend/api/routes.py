"""REST API endpoints for AI Insights Service."""

import httpx
import traceback
from fastapi.security import APIKeyHeader
from utils.logger.logger_util import get_logger
from utils.config.config_util import CLARISA_VALIDATE_URL
from utils.notification.notification_service import notification_service
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from modules.document_overview.processing import (
    process_project_overview,
    get_cached_project_overview,
)
from api.models import (
    DocumentOverviewRequest,
    DocumentOverviewResponse,
    ProcessedDocument,
    ErrorResponse,
)

logger = get_logger()
router = APIRouter()

APP_NAME = "AI Insights Service (STAR)"


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

http_client = httpx.AsyncClient()

def validate_with_clarisa(microservice_name: str):
    async def _validate(request: Request, api_key: str = Depends(api_key_header)):
        client_ip = request.client.host if request.client else "0.0.0.0"
        endpoint = request.url.path

        payload = {
            "api_key": api_key,
            "microservice_name": microservice_name,
            "endpoint_accessed": endpoint,
            "ip_address": client_ip
        }

        try:
            response = await http_client.post(CLARISA_VALIDATE_URL, json=payload, timeout=5.0)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Communication error with the authentication service"
                )

            data = response.json()

            if not data.get("valid"):
                error_msg = data.get("error", "Invalid API Key")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            return data.get("mis")

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable"
            )

    return _validate


def _build_overview_response(result: dict, cached: bool = False) -> DocumentOverviewResponse:
    documents_processed = []
    for doc in result["documents_processed"]:
        documents_processed.append(
            ProcessedDocument(
                file_key=doc["file_key"],
                file_name=doc.get("file_name") or doc["file_key"].rsplit("/", 1)[-1],
                extraction_method=doc["extraction_method"],
                character_count=doc["character_count"],
            )
        )

    return DocumentOverviewResponse(
        overview=result["overview"],
        time_taken=result["time_taken"],
        project_folder=result["project_folder"],
        bucket_name=result["bucket_name"],
        documents_processed=documents_processed,
        interaction_id=result.get("interaction_id"),
        status=result.get("status", "success"),
        generated_at=result.get("generated_at"),
        cached=cached,
    )


@router.get(
    "/api/document-overview",
    response_model=DocumentOverviewResponse,
    tags=["Document Overview"],
    summary="Get a cached project overview",
    description="""
    Retrieve a previously generated project overview from `response.json` stored
    in the project's S3 folder.

    STAR should call this endpoint when a user opens a project. If a cached overview
    exists, it is returned immediately without reprocessing documents.

    Returns 404 if no cached overview exists for the project folder.
    """,
    response_description="Cached project overview",
    responses={
        200: {
            "description": "Cached project overview found",
            "model": DocumentOverviewResponse,
        },
        404: {
            "description": "No cached overview found for this project",
            "model": ErrorResponse,
        },
    },
)
async def get_document_overview(
    bucket_name: str = Query(..., description="S3 bucket containing the project documents"),
    project_folder: str = Query(..., description="S3 folder prefix for the project"),
) -> DocumentOverviewResponse:
    logger.info(
        f"📥 Cached project overview request — "
        f"s3://{bucket_name}/{project_folder}"
    )

    cached_result = get_cached_project_overview(
        bucket_name=bucket_name,
        project_folder=project_folder,
    )

    if not cached_result:
        logger.warning(
            f"📭 No cached overview found for project folder: {project_folder}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Overview not found",
                "status": "error",
                "details": (
                    f"No cached overview found for project folder: {project_folder}"
                ),
            },
        )

    logger.info(
        f"✅ Cached project overview returned for: {project_folder}"
    )
    return _build_overview_response(cached_result, cached=True)


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
async def document_overview(request: DocumentOverviewRequest, mis: str = Depends(validate_with_clarisa("AI Insights Service - STAR"))) -> DocumentOverviewResponse:
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

        return _build_overview_response(result, cached=False)

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
