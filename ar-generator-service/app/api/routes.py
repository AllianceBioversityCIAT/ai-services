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


def _generate_indicator_tables():
    """Lazy import of indicator tables function to avoid initialization issues."""
    try:
        from app.llm.vectorize_os_annual import generate_indicator_tables
        return generate_indicator_tables
    except Exception as e:
        logger.error(f"Failed to import generate_indicator_tables: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Service configuration error",
                "details": "Indicator tables generation service is not properly configured. Please check AWS credentials and configuration.",
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
    

@router.post(
    "/api/generate-annual-tables",
    tags=["Reports"],
    summary="Generate AICCRA Annual Indicator Summary Tables",
    description="""
    📊 Generate AI-Powered AICCRA Annual Indicator Summary Tables
    
    This endpoint generates comprehensive summary tables for all AICCRA indicators grouped by type (PDO, IPI 1.x, IPI 2.x, IPI 3.x).
    Each table provides key metrics and AI-generated brief overviews for the specified year.
    
    🎯 Report Type: Annual Indicator Summary Tables
    
    - Purpose: Provide consolidated overview of all indicators performance
    - Scope: Summary tables with quantitative targets, achievements, and qualitative overviews
    - Timeline: Annual performance snapshot for all indicators
    - Use Case: Executive dashboards, annual reporting, performance monitoring
    
    🔍 How It Works
    
    1. Data Retrieval: Fetches contribution data from SQL Server database for all indicators
    2. Aggregation: Groups indicators by type and calculates summary statistics
    3. AI Summarization: Uses AWS Bedrock Claude 3.7 Sonnet to generate brief overviews from cluster narratives
    4. Table Generation: Creates structured tables with quantitative and qualitative data
    
    📈 Table Content
    
    Each table includes:
    - Indicator Statement: Full indicator title/description
    - End-year Target: Sum of expected milestone values for the year
    - Projected Targets: Reserved for mid-year projections (currently empty)
    - Achieved: Sum of reported milestone values for the year
    - Brief Overviews: AI-generated summaries of cluster contributions and achievements
    
    Generated tables:
    - PDO Indicators: All PDO indicators (1-5)
    - IPI 1.x Indicators: All IPI 1.1 through 1.4 indicators
    - IPI 2.x Indicators: All IPI 2.1 through 2.3 indicators
    - IPI 3.x Indicators: All IPI 3.1 through 3.4 indicators
    
    ⚡ Performance Notes
    
    - Processing time: ~2-5 minutes (depends on number of indicators and narratives)
    - AI calls: One per indicator for brief overview generation
    
    📋 Example Usage
    
    ```bash
    curl -X POST "http://localhost:8000/api/generate-annual-tables" \\
         -H "Content-Type: application/json" \\
         -d '{
           "year": 2025
         }'
    ```
    
    Response format:
    ```json
    {
      "year": 2025,
      "tables": {
        "PDO": [
          {
            "Indicator statement": "PDO Indicator 1: Number of farmers trained in climate-smart agriculture",
            "End-year target 2025": 1200,
            "Projected targets for 2025 (Mid-year report 2025)": "",
            "Achieved in 2025": 1350,
            "Brief overviews": "Kenya: Successfully trained 450 farmers in drought-resistant crop varieties. Zambia: Reached 300 farmers with improved irrigation techniques..."
          }
        ],
        "IPI 1.x": [...],
        "IPI 2.x": [...],
        "IPI 3.x": [...]
      },
      "status": "success"
    }
    ```
    """,
    response_description="Successfully generated annual indicator summary tables with AI-generated overviews",
    responses={
        200: {
            "description": "Tables generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "year": 2025,
                        "tables": {
                            "PDO": [
                                {
                                    "Indicator statement": "PDO Indicator 1: Number of farmers trained in climate-smart agriculture",
                                    "End-year target 2025": 1200,
                                    "Projected targets for 2025 (Mid-year report 2025)": "",
                                    "Achieved in 2025": 1350,
                                    "Brief overviews": "Kenya: Successfully trained 450 farmers in drought-resistant crop varieties. Zambia: Reached 300 farmers with improved irrigation techniques. Ethiopia: Achieved 600 farmer trainings focusing on sustainable land management practices."
                                }
                            ],
                            "IPI 1.x": [],
                            "IPI 2.x": [],
                            "IPI 3.x": []
                        },
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
async def generate_annual_tables(request: ChatRequest):
    """
    Generate annual indicator summary tables for the specified year.
    
    This endpoint generates summary tables for all AICCRA indicators,
    including quantitative targets/achievements and AI-generated brief overviews.
    
    - year: The year for the tables (must be between 2021 and 2025)
    
    Returns the generated tables organized by indicator type.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Starting annual tables generation for year: {request.year}")
        
        # Lazy import the tables generation function
        generate_tables_func = _generate_indicator_tables()
        
        # Call the tables generation function
        logger.info("🔍 Executing annual tables generation...")
        tables = generate_tables_func(request.year)
        
        # Convert DataFrames to dictionaries for JSON response
        tables_dict = {}
        for group_name, df_table in tables.items():
            tables_dict[group_name] = df_table.to_dict(orient="records")
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        logger.info(f"✅ Successfully generated annual tables for {request.year} in {processing_time}s")
        
        return {
            "year": request.year,
            "tables": tables_dict,
            "status": "success"
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid request parameters", "details": str(e), "status": "error"}
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