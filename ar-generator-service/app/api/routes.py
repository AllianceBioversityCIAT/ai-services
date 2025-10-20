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


def _run_pipeline_opensearch_annual():
    """Lazy import of annual opensearch function to avoid initialization issues."""
    try:
        from app.llm.vectorize_os_annual import run_pipeline
        return run_pipeline
    except Exception as e:
        logger.error(f"Failed to import annual opensearch: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Service configuration error",
                "details": "Annual Report OpenSearch service is not properly configured. Please check AWS credentials and configuration.",
                "status": "error"
            }
        )


@router.post(
    "/api/generate",
    response_model=ChatResponse,
    tags=["Reports"],
    summary="Generate AICCRA Mid-Year Report",
    description="""
    📊 Generate AI-Powered AICCRA Mid-Year Progress Report
    
    This endpoint generates a mid-year progress report for a specific AICCRA indicator and year.
    The report focuses on progress achieved up to mid-year and is designed for interim reporting cycles.
    
    🎯 Report Type: Mid-Year Progress Report
    
    - Purpose: Track progress achievements up to mid-year
    - Scope: Interim progress assessment and milestone tracking
    - Timeline: Typically covers January-June achievements
    - Use Case: Progress monitoring, mid-year reviews, course correction
    
    🔍 How It Works
    
    1. Data Retrieval: Fetches relevant progress data from SQL Server database
    2. Vector Search: Uses OpenSearch to find contextually relevant information  
    3. AI Generation: Leverages AWS Bedrock Claude 3.7 Sonnet to generate the narrative
    4. Quality Assurance: Ensures report follows AICCRA formatting standards
    
    📈 Mid-Year Report Content
    
    Generated reports include:
    - Progress Summary: Mid-year quantitative achievements vs annual targets  
    - Key Deliverables: Research outputs completed by mid-year with DOI links
    - Cluster Contributions: Mid-year activities by regional/thematic clusters
    - Milestone Tracking: Progress indicators and completion percentages
    - Risk Assessment: Challenges and mitigation strategies for remaining year
    
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
           "insert_data": false
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
                        "content": "## Mid-Year Progress Report - IPI 1.1\n\nBy mid-year 2025, AICCRA had achieved 850 out of 1200 farmers trained (71% progress) for indicator IPI 1.1. The Western Africa cluster contributed significantly with 350 farmers trained across Ghana and Mali...",
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
    Generate an AICCRA mid-year progress report for the specified indicator and year.
    
    This endpoint generates a mid-year report focusing on progress achieved up to mid-year.
    
    - indicator: The indicator to generate a report for (e.g., "IPI 1.1", "PDO Indicator 1")
    - year: The year for the report (must be between 2021 and 2025)
    - insert_data: Optional flag to insert fresh data into OpenSearch (default is False)
    
    Returns the generated mid-year report content.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Starting mid-year report generation for indicator: {request.indicator}, year: {request.year}")
        
        # Lazy import the opensearch function
        query_opensearch = _run_pipeline_opensearch()
        
        # Call the existing opensearch function for mid-year reports
        logger.info("🔍 Executing mid-year report generation pipeline...")
        response_stream = query_opensearch(request.indicator, request.year, insert_data=request.insert_data)
        
        # Collect the streaming response into a single string
        full_response = ""
        for chunk in response_stream:
            full_response += chunk

        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        logger.info(f"✅ Successfully generated mid-year report for {request.indicator} - {request.year} in {processing_time}s")
        
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


@router.post(
    "/api/generate-annual",
    response_model=ChatResponse,
    tags=["Reports"],
    summary="Generate AICCRA Annual Report",
    description="""
    📊 Generate AI-Powered AICCRA Annual Report
    
    This endpoint generates a comprehensive annual report for a specific AICCRA indicator and year.
    The report covers the complete annual achievements and is designed for year-end reporting cycles.
    
    🎯 Report Type: Annual Report
    
    - Purpose: Comprehensive review of full-year achievements
    - Scope: Complete annual performance assessment and impact evaluation
    - Timeline: Covers full January-December achievements
    - Use Case: Annual reviews, donor reporting, impact assessment, strategic planning
    
    🔍 How It Works
    
    1. Data Retrieval: Fetches comprehensive annual data from SQL Server database
    2. Vector Search: Uses OpenSearch to find contextually relevant information  
    3. AI Generation: Leverages AWS Bedrock Claude 3.7 Sonnet to generate detailed narratives
    4. Impact Analysis: Includes comprehensive outcome and impact assessments
    5. Quality Assurance: Ensures report follows AICCRA annual reporting standards
    
    📈 Annual Report Content (More Comprehensive)
    
    Generated reports include:
    - Executive Summary: Complete annual achievements overview
    - Quantitative Analysis: Full-year progress vs targets with trend analysis
    - Key Deliverables: All research outputs completed during the year with DOI links
    - Cluster Contributions: Comprehensive activities by all regional/thematic clusters
    - Innovations & Technologies: Complete innovation pipeline and readiness assessments (for IPI indicators)
    - Outcome Impact Reports: Detailed impact case studies and beneficiary stories (for PDO indicators)
    - Disaggregated Targets: Detailed breakdown by demographics and geography (for select indicators)
    - Gender & Social Inclusion: Comprehensive social impact and equity analysis
    - Lessons Learned: Challenges, successes, and strategic recommendations
    - Reference Links: Complete bibliography of missed or additional references
    
    ⚡ Performance Notes
    
    - With data refresh (`insert_data=True`): ~45-60 minutes (more comprehensive processing)
    - Without data refresh (`insert_data=False`): ~15-45 seconds (more detailed generation)
    
    📋 Example Usage
    
    ```bash
    curl -X POST "http://localhost:8000/api/generate-annual" \\
         -H "Content-Type: application/json" \\
         -d '{
           "indicator": "PDO Indicator 1",
           "year": 2024,
           "insert_data": false
         }'
    ```
    """,
    response_description="Successfully generated comprehensive AICCRA annual report with detailed AI-generated content",
    responses={
        200: {
            "description": "Annual report generated successfully",
            "model": ChatResponse,
            "content": {
                "application/json": {
                    "example": {
                        "indicator": "PDO Indicator 1",
                        "year": 2024,
                        "content": "# Annual Report 2024 - PDO Indicator 1\n\n## Executive Summary\n\nDuring 2024, AICCRA successfully achieved 1,200 out of 1,000 targeted farmers trained (120% achievement) for PDO Indicator 1, surpassing annual goals through innovative climate services delivery...\n\n## Disaggregated Targets\n\nGender distribution: 65% women, 35% men farmers trained...",
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
async def generate_annual_report(request: ChatRequest) -> ChatResponse:
    """
    Generate a comprehensive AICCRA annual report for the specified indicator and year.
    
    This endpoint generates a detailed annual report covering complete year achievements,
    including comprehensive analysis, disaggregated targets, and impact assessments.
    
    - indicator: The indicator to generate a report for (e.g., "IPI 1.1", "PDO Indicator 1")
    - year: The year for the report (must be between 2021 and 2025)
    - insert_data: Optional flag to insert fresh data into OpenSearch (default is False)
    
    Returns the generated comprehensive annual report content.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Starting annual report generation for indicator: {request.indicator}, year: {request.year}")
        
        # Lazy import the annual opensearch function
        query_opensearch_annual = _run_pipeline_opensearch_annual()
        
        # Call the annual opensearch function for comprehensive reports
        logger.info("🔍 Executing comprehensive annual report generation pipeline...")
        full_response = query_opensearch_annual(request.indicator, request.year, insert_data=request.insert_data)
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        logger.info(f"✅ Successfully generated annual report for {request.indicator} - {request.year} in {processing_time}s")
        
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