"""REST API endpoints for PRMS QA Service."""

import time
import httpx
import traceback
from fastapi.security import APIKeyHeader
from app.utils.logger.logger_util import get_logger
from app.llm.mining import improve_prms_result_metadata
from app.utils.config.config_util import CLARISA_VALIDATE_URL
from app.utils.assessment.contract_validation import validate
from app.llm.assessment import assess_result, AssessmentUnavailable
from fastapi import APIRouter, HTTPException, status, Request, Depends
from app.utils.notification.notification_service import NotificationService
from app.api.models import PrmsRequest, PrmsResponse, ErrorResponse, QualityAssessmentRequest, QualityAssessmentResponse


logger = get_logger()
router = APIRouter()

notification_service = NotificationService()


if not CLARISA_VALIDATE_URL:
    logger.error("❌ CLARISA_VALIDATE_URL is not configured; refusing to authorize")
    raise RuntimeError(
        "CLARISA_VALIDATE_URL is not configured. The service refuses to start without authentication."
    )


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
# async def prms_qa(request: PrmsRequest, mis: str = Depends(validate_with_clarisa("AI Review - PRMS"))) -> PrmsResponse:
async def prms_qa(request: PrmsRequest) -> PrmsResponse:
    """
    Process PRMS result metadata using an LLM.
    - result_metadata: JSON dict with PRMS result details.
    - user_id: Optional user ID for tracking.
    """
    try:
        logger.info(f"🔍 Processing PRMS QA for user: {request.user_id}")
        
        result = await improve_prms_result_metadata(request.result_metadata, request.user_id)

        await notification_service.send_slack_notification(
            emoji=":ai: :sparkles:",
            app_name="PRMS Reporting Tool QA-AI Service",
            color="#36a64f",
            title="Reporting Tool Result Processed",
            message=f"Successfully improved result metadata\nUser: *{request.user_id or 'Unknown'}*\nResult Type: *{request.result_metadata.get('result_type_name', 'Unknown')}*",
            time_taken=f"Processing time: *{result['time_taken']}* seconds",
            priority="Low"
        )

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
            
            await notification_service.send_slack_notification(
                emoji=":ai: :alert:",
                app_name="PRMS Reporting Tool QA-AI Service",
                color="#ff0000",
                title="Validation Error",
                message=f"LLM validation failed\nUser: *{request.user_id or 'Unknown'}*",
                time_taken="Time taken: *N/A*",
                priority="High"
            )
            
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
            
            await notification_service.send_slack_notification(
                emoji=":ai: :alert:",
                app_name="PRMS Reporting Tool QA-AI Service",
                color="#ff0000",
                title="Validation Error",
                message=f"Invalid data provided\nUser: *{request.user_id or 'Unknown'}*",
                time_taken="Time taken: *N/A*",
                priority="High"
            )
            
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
        
        await notification_service.send_slack_notification(
            emoji=":ai: :alert:",
            app_name="PRMS Reporting Tool QA-AI Service",
            color="#ff0000",
            title="Missing Required Field",
            message=f"Required field missing: *{str(e)}*\nUser: *{request.user_id or 'Unknown'}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        
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
            user_message = "The request is taking longer than expected. Try reducing the number of evidence files or try again later."
            error_code = "TIMEOUT_ERROR"
            status_code = status.HTTP_408_REQUEST_TIMEOUT
        else:
            user_message = "Something unexpected happened. Please try again or contact support if the issue persists."
            error_code = "INTERNAL_ERROR"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        logger.error(f"Unexpected error: {error_msg}")
        tb = traceback.format_exc()
        logger.error(f"📋 Full traceback:\n{tb}")
        
        await notification_service.send_slack_notification(
            emoji=":ai: :alert:",
            app_name="PRMS Reporting Tool QA-AI Service",
            color="#ff0000",
            title=f"Service Error - {error_code}",
            message=f"Unexpected error occurred\nUser: *{request.user_id or 'Unknown'}*\nError: *{user_message}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        
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


quality_assessment_auth = validate_with_clarisa("AI Traffic Light - PRMS")

@router.post(
    "/prms/quality-assessment",
    response_model=QualityAssessmentResponse,
    tags=["Quality Assessment"],
    summary="AI quality check for W3/Bilateral results",
    description="""
    🚦 Assess a W3/Bilateral result against the CGIAR QA criteria and return a
    traffic-light verdict for the result as a whole and for each section.

    Applies the same criteria QA assessors use for pooled-funding results. Roughly
    half the criteria are resolved deterministically in code; the rest are judged
    by the model against a closed list, so the set of possible findings never
    grows between runs.

    Evidence links are fetched and read: the check reports whether each item is
    reachable, genuine, and actually supports the result.

    The check never blocks a submission. If part of it cannot be completed the
    response still returns, with `status` set to `partial` or `unavailable`.
    """,
)
async def quality_assessment(request: QualityAssessmentRequest, mis: str = Depends(quality_assessment_auth)) -> QualityAssessmentResponse:
    problems = validate(request)
    if problems:
        logger.warning(f"⚠️ Contract problems in {request.request_id}: {len(problems)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "The submitted payload does not match the agreed contract.",
                "status": "error",
                "error_type": "CONTRACT_VIOLATION",
                "request_id": request.request_id,
                "problems": problems,
            },
        )

    started = time.monotonic()

    try:
        result = await assess_result(request)
        elapsed = time.monotonic() - started

        total = len(request.sections.evidence)
        evaluated = sum(1 for e in result.evidence if e.verdict.value != "grey")

        light = {"green": ":large_green_circle:", "amber": ":large_yellow_circle:",
                 "red": ":red_circle:", "grey": ":white_circle:"}
        verdict = result.overall.verdict.value
        issues = sum(len(sec["issues"]) for sec in result.sections.model_dump().values())
        skipped = result.coverage.criteria_total - result.coverage.criteria_evaluated

        message = (
            f"Successfully assessed result quality\n"
            f"User: *{request.user_id or 'Unknown'}*\n"
            f"Result Type: *{request.result.type}*\n"
            f"\n"
            f"*Result quality (QA outcome):*\n"
            f"Verdict: {light.get(verdict, '')} *{verdict.upper()}*"
            f"{f' — score *{result.overall.score}*' if result.overall.score is not None else ''}\n"
            f"Points to address: *{issues}*\n"
            f"\n"
            f"*Run details (service):*\n"
            f"Evidence: *{total}* total, *{evaluated}* read, *{total - evaluated}* not read\n"
            f"Checks: *{result.coverage.criteria_evaluated}* of "
            f"*{result.coverage.criteria_total}* completed"
            f"{f' — *{skipped}* skipped' if skipped else ''}\n"
            f"Coverage: *{result.status.value}*"
            f"{f' — _{result.degraded_reason}_' if result.degraded_reason else ''}\n"
            f"Request: `{request.request_id}`"
        )

        await notification_service.send_slack_notification(
            emoji=":ai: :vertical_traffic_light:",
            app_name="PRMS Bilateral QA Assessment",
            color="#36a64f",
            title="✅ Reporting Tool Result Assessed",
            message=message,
            time_taken=f"Processing time: *{elapsed:.2f}* seconds",
            priority="Low",
        )

        return result

    except AssessmentUnavailable as e:
        logger.error(f"❌ No assessment produced for {request.request_id}: {e}")

        await notification_service.send_slack_notification(
            emoji=":ai: :vertical_traffic_light:",
            app_name="PRMS Bilateral QA Assessment",
            color="#ff0000",
            title="❌ Quality assessment unavailable",
            message=(
                f"The AI could not review this result\n"
                f"User: *{request.user_id or 'Unknown'}*\n"
                f"Result Type: *{request.result.type}*\n"
                f"\n"
                f"*Reason:*\n"
                f"_{str(e)[:300]}_\n"
                f"Request: `{request.request_id}`"
            ),
            time_taken=f"Processing time: *{time.monotonic() - started:.2f}* seconds",
            priority="High",
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "The AI quality check is not available at the moment.",
                "status": "error",
                "error_type": "ASSESSMENT_UNAVAILABLE",
                "request_id": request.request_id,
            },
        )

    except Exception as e:
        logger.error(f"❌ Assessment failed for {request.request_id}: {e}")
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")

        await notification_service.send_slack_notification(
            emoji=":ai: :vertical_traffic_light:",
            app_name="PRMS Bilateral QA Assessment",
            color="#ff0000",
            title="❌ Quality assessment failed",
            message=(
                f"The service could not produce an assessment\n"
                f"User: *{request.user_id or 'Unknown'}*\n"
                f"Result Type: *{request.result.type}*\n"
                f"\n"
                f"*Error:*\n"
                f"`{type(e).__name__}` — _{str(e)[:300]}_\n"
                f"Request: `{request.request_id}`"
            ),
            time_taken="Time taken: *N/A*",
            priority="High",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "The AI quality check is not available at the moment.",
                "status": "error",
                "error_type": "ASSESSMENT_UNAVAILABLE",
                "request_id": request.request_id,
            },
        )