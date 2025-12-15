"""REST API endpoints for PRMS QA Service."""

import traceback
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
             "result_id": "8",
             "result_type_name": "Innovation Development",
             "result_level_name": "Output",
             "result_name": "Original Title",
             "result_description": "Original Description"
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
        
        result = await improve_prms_result_metadata(request.result_metadata, request.user_id)
        return PrmsResponse(
            time_taken=result["time_taken"],
            json_content=result["json_content"],
            interaction_id=result.get("interaction_id"),
            evidence_metadata=result.get("evidence_metadata"),
            status="success"
        )
    
    except ValueError as e:
        error_msg = str(e)
        
        if "LLM returned invalid JSON" in error_msg or "Output schema validation failed" in error_msg:
            logger.error(f"LLM/service error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "The AI service returned invalid response. Please try submitting your request again.", 
                    "message": error_msg, 
                    "status": "error",
                    "error_type": "INVALID_AI_RESPONSE",
                    "debug_info": {
                        "has_response_wrapper": "response" in request.result_metadata,
                        "traceback": traceback.format_exc()
                    }
                }
            )
        else:
            logger.error(f"Validation error: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Some of the information you provided appears to be incomplete or in an unexpected format. Please review and try again.", 
                    "message": error_msg, 
                    "status": "error",
                    "error_type": "VALIDATION_ERROR",
                    "debug_info": {
                        "has_response_wrapper": "response" in request.result_metadata,
                        "traceback": traceback.format_exc()
                    }
                }
            )
    
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Some required information is missing. Please make sure all fields are filled out and try again.",
                "message": f"Missing required field: {str(e)}",
                "status": "error",
                "error_type": "MISSING_FIELD",
                "debug_info": {
                    "missing_field": str(e),
                    "received_keys": list(request.result_metadata.keys()),
                    "traceback": traceback.format_exc()
                }
            }
        )
    
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if "ThrottlingException" in error_msg:
            user_message = "Service is temporarily overloaded. Please try again in a few minutes."
            error_code = "THROTTLING_ERROR"
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif "Timeout" in error_msg or "timeout" in error_msg:
            user_message = "Your request is taking longer than expected. Try reducing the number of evidence files or try again later."
            error_code = "TIMEOUT_ERROR"
            status_code = status.HTTP_408_REQUEST_TIMEOUT
        else:
            user_message = "Something unexpected happened. Please try again or contact support if the issue persists."
            error_code = "INTERNAL_ERROR"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        logger.error(f"Unexpected error: {error_msg}")
        tb = traceback.format_exc()
        logger.error(f"📋 Full traceback:\n{tb}")
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": user_message, 
                "message": error_msg,
                "status": "error",
                "error_type": error_code,
                "debug_info": {
                    "original_error_type": error_type,
                    "has_response_wrapper": "response" in request.result_metadata if hasattr(request, 'result_metadata') else False,
                    "traceback": tb
                }
            }
        )