"""REST API endpoints for AICCRA Report Generator Service."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import time
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
                "details": "OpenSearch service is not properly configured. Please check AWS credentials and configuration.",
                "status": "error"
            }
        )


@router.post(
    "/api/generate",
    response_model=ChatResponse,
    tags=["Reports"],
    summary="Generate AICCRA Report",
    description="""
    📊 Generate AI-Powered AICCRA Report
    
    This endpoint generates a comprehensive report for a specific AICCRA indicator and year.
    The report is generated using advanced AI (AWS Bedrock Claude 3.7 Sonnet) combined with vector search 
    capabilities to provide data-driven insights.
    
    🔍 How It Works
    
    1. Data Retrieval: Fetches relevant data from SQL Server database
    2. Vector Search: Uses OpenSearch to find contextually relevant information  
    3. AI Generation: Leverages AWS Bedrock Claude 3.7 Sonnet to generate the narrative
    4. Quality Assurance: Ensures report follows AICCRA formatting standards
    
    📈 Report Content
    
    Generated reports include:
    - Progress Summary: Quantitative achievements vs targets  
    - Key Deliverables: Research outputs with DOI links
    - Cluster Contributions: Activities by regional/thematic clusters
    - Innovations: Technology and practice developments (for IPI indicators)
    - Outcomes: Impact case reports (for PDO indicators)
    - Gender & Inclusion: Social impact considerations
    
    ⚡ Performance Notes
    
    - With data refresh (`insert_data=True`): ~30-40 minutes
    - Without data refresh (`insert_data=False`): ~10-30 seconds
    
    📋 Example Usage
    
    ```bash
    curl -X POST "http://localhost:8000/api/generate" \\
         -H "Content-Type: application/json" \\
         -d '{
           "indicator": "IPI 1.1",
           "year": 2025,
           "insert_data": False
         }'
    ```
    """,
    response_description="Successfully generated AICCRA report with AI-generated content",
    responses={
        200: {
            "description": "Report generated successfully",
            "model": ChatResponse,
            "content": {
                "application/json": {
                    "example": {
                        "indicator": "IPI 1.1",
                        "year": 2025,
                        "content": "By mid-year 2025, AICCRA had already achieved 850 out of 1200 farmers trained, representing 71% progress for indicator IPI 1.1. The Western Africa cluster contributed significantly...",
                        "status": "success"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request parameters (validation error)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid request parameters",
                        "status": "error"
                    }
                }
            }
        },
        403: {
            "description": "Access denied (authentication/authorization error)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Access denied",
                        "status": "error"
                    }
                }
            }
        },
        422: {
            "description": "Validation error in request body",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Internal server error",
                        "status": "error"
                    }
                }
            }
        }
    }
)
async def generate_report(request: ChatRequest) -> ChatResponse:
    """
    Generate an AICCRA report for the specified indicator and year.
    
    - indicator: The indicator to generate a report for (e.g., "IPI 1.1", "PDO Indicator 1")
    - year: The year for the report (must be between 2020 and 2030)
    - insert_data: Optional flag to insert fresh data into OpenSearch (default is False)
    
    Returns the generated report content.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Starting report generation for indicator: {request.indicator}, year: {request.year}")
        
        # Lazy import the opensearch function
        query_opensearch = _run_pipeline_opensearch()
        
        # Call the existing opensearch function
        logger.info("🔍 Executing report generation pipeline...")
        response_stream = query_opensearch(request.indicator, request.year, insert_data=request.insert_data)
        
        # Collect the streaming response into a single string
        full_response = ""
        for chunk in response_stream:
            full_response += chunk

        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        logger.info(f"✅ Successfully generated report for {request.indicator} - {request.year} in {processing_time}s")
        
        return ChatResponse(
            indicator=request.indicator,
            year=request.year,
            content=full_response,
            status="success"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request parameters", "details": str(e), "status": "error"}
        )
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Access denied", "details": str(e), "status": "error"}
        )
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Service error", "details": str(e), "status": "error"}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "details": str(e), "status": "error"}
        )