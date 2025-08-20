"""REST API endpoints for AICCRA Report Generator Service."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from typing import Iterator

from app.api.models import ChatRequest, ChatResponse, ErrorResponse
from app.utils.logger.logger_util import get_logger

logger = get_logger()

router = APIRouter()


def _run_pipeline_opensearch():
    """Lazy import of opensearch function to avoid initialization issues."""
    try:
        from app.llm.vectorize_os import run_pipeline
        return run_pipeline
    except Exception as e:
        logger.error(f"Failed to import opensearch: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Service configuration error",
                "details": "Opensearch service is not properly configured. Please check AWS credentials and configuration.",
                "status": "error"
            }
        )


@router.post(
    "/api/generate",
    response_model=ChatResponse,
    summary="Generate AICCRA report",
    description="Generate an AICCRA report based on the provided indicator and year using AWS Bedrock integration",
    responses={
        200: {
            "description": "Report generated successfully",
            "model": ChatResponse
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
async def generate_report(request: ChatRequest) -> ChatResponse:
    """
    Generate an AICCRA report for the specified indicator and year.
    
    - **indicator**: The indicator to generate a report for (e.g., "IPI 1.1", "PDO Indicator 1")
    - **year**: The year for the report (must be between 2020 and 2030)
    - **insert_data**: Optional flag to insert fresh data into OpenSearch (default is False)
    
    Returns the generated report content.
    """
    try:
        logger.info(f"Generating report for indicator: {request.indicator}, year: {request.year}")
        
        # Lazy import the opensearch function
        query_opensearch = _run_pipeline_opensearch()
        
        # Call the existing opensearch function
        response_stream = query_opensearch(request.indicator, request.year, insert_data=request.insert_data)
        
        # Collect the streaming response into a single string
        full_response = ""
        for chunk in response_stream:
            full_response += chunk
        
        logger.info(f"Successfully generated report for {request.indicator} - {request.year}")
        
        return ChatResponse(
            indicator=request.indicator,
            year=request.year,
            content=full_response,
            status="success"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid request parameters", "details": str(e), "status": "error"}
        )
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        raise HTTPException(
            status_code=403,
            detail={"error": "Access denied", "details": str(e), "status": "error"}
        )
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Service error", "details": str(e), "status": "error"}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "details": str(e), "status": "error"}
        )