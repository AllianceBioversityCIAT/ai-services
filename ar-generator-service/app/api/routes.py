"""REST API endpoints for AICCRA Report Generator Service."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from typing import Iterator

from app.api.models import ChatRequest, ChatResponse, ErrorResponse
from app.utils.logger.logger_util import get_logger

logger = get_logger()

router = APIRouter()


def _get_knowledge_base_function():
    """Lazy import of knowledge_base function to avoid initialization issues."""
    try:
        from app.llm.knowledge_base import query_knowledge_base
        return query_knowledge_base
    except Exception as e:
        logger.error(f"Failed to import knowledge_base: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Service configuration error",
                "details": "Knowledge base service is not properly configured. Please check AWS credentials and configuration.",
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
    
    Returns the generated report content.
    """
    try:
        logger.info(f"Generating report for indicator: {request.indicator}, year: {request.year}")
        
        # Lazy import the knowledge base function
        query_knowledge_base = _get_knowledge_base_function()
        
        # Call the existing knowledge base function
        response_stream = query_knowledge_base(request.indicator, request.year)
        
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


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Chat with AICCRA assistant", 
    description="Alternative endpoint name for chat-style interaction with the same functionality as /api/generate"
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with the AICCRA assistant to generate reports.
    
    This is an alias for the /api/generate endpoint with the same functionality.
    """
    return await generate_report(request)