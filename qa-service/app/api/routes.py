"""REST API endpoints for PRMS QA Service."""

from app.utils.logger.logger_util import get_logger
from fastapi import APIRouter, HTTPException, status
from app.llm.mining import improve_prms_result_metadata
from app.api.models import PrmsRequest, PrmsResponse, ErrorResponse

logger = get_logger()
router = APIRouter()

@router.post(
    "/api/prms-qa",
    response_model=PrmsResponse,
    tags=["PRMS QA"],
    summary="Process PRMS result metadata",
    description="""
    🔍 Process CGIAR result metadata for PRMS using an LLM to improve titles, descriptions, and short names.

    Send PRMS result metadata (e.g., result type, level, name, description) and optionally a user ID for interaction tracking. The service uses AWS Bedrock Claude to generate QA improvements based on predefined prompts.

    Example use cases:
    - Improve result titles and descriptions for clarity and non-specialist audiences
    - Generate short names for innovation developments
    - Ensure consistency with CGIAR standards

    Example usage:
    ```bash
    curl -X POST "http://localhost:8000/api/prms-qa" \\
         -H "Content-Type: application/json" \\
         -d '{
           "result_metadata": {
             "response": {
               "result_type_name": "Innovation Development",
               "result_level_name": "Output",
               "result_name": "Original Title",
               "result_description": "Original Description"
             }
           },
           "user_id": "user123"
         }'
    ```
    """,
    response_description="Successfully processed PRMS metadata",
    responses={
        200: {
            "description": "Successfully processed PRMS metadata",
            "model": PrmsResponse,
            "content": {
                "application/json": {
                    "example": {
                        "content": "{\"new_title\": \"Improved Title\", \"new_description\": \"Improved Description\"}",
                        "time_taken": "1.23",
                        "json_content": {"new_title": "Improved Title", "new_description": "Improved Description"},
                        "project": "PRMS",
                        "interaction_id": "abc123",
                        "status": "success"
                    }
                }
            }
        },
        400: {
            "description": "Invalid parameters",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid parameters",
                        "status": "error"
                    }
                }
            }
        },
        500: {
            "description": "Internal error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Internal error",
                        "status": "error"
                    }
                }
            }
        }
    }
)
async def prms_qa(request: PrmsRequest) -> PrmsResponse:
    """
    Process PRMS result metadata using an LLM.
    - result_metadata: JSON dict with PRMS result details.
    - user_id: Optional user ID for tracking.
    """
    try:
        logger.info(f"🔍 Processing PRMS QA for user: {request.user_id}")
        result = improve_prms_result_metadata(request.result_metadata, request.user_id)
        return PrmsResponse(
            content=result["content"],
            time_taken=result["time_taken"],
            json_content=result["json_content"],
            project=result["project"],
            interaction_id=result.get("interaction_id"),
            status="success"
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid parameters", "details": str(e), "status": "error"}
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal error", "details": str(e), "status": "error"}
        )