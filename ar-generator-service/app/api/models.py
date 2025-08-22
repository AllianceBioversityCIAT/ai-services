"""Pydantic models for API request and response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """
    Request model for generating AICCRA reports.
    
    This model defines the required parameters for generating an AI-powered
    report for AICCRA indicators.
    """

    indicator: str = Field(
        ...,
        description="""
        AICCRA indicator identifier for report generation.
        
        IPI Indicators (Intermediate Performance):
        - IPI 1.1-1.4: Climate information services and early warning systems
        - IPI 2.1-2.3: Agricultural technologies and farming practices  
        - IPI 3.1-3.4: Institutional capacity building and partnerships
        
        PDO Indicators (Project Development Objective):
        - PDO Indicator 1-5: Project outcome and impact metrics
        """,
        examples=["IPI 1.1", "PDO Indicator 1"]
    )
    
    year: int = Field(
        ..., 
        description="""
        Target year for report generation (2021-2025).
        
        The system will generate a progress report for the specified year,
        summarizing achievements and progress.
        """,
        ge=2021,
        le=2025,
        examples=[2024, 2025]
    )
    
    insert_data: Optional[bool] = Field(
        default=False,
        description="""
        Data refresh flag - whether to reload fresh data into OpenSearch vector database.
        
        - True: Refresh the vector database with latest data from SQL Server (slower)
        - False: Use existing vectorized data (faster)

        Recommendation: Use True when you need the most recent data updates.
        """,
        examples=[False, True]
    )


class ChatResponse(BaseModel):
    """
    Successful response model for AICCRA report generation.
    
    Contains the generated report content and metadata about the request.
    """
    
    indicator: str = Field(
        ..., 
        description="The AICCRA indicator that was processed",
        examples=["IPI 1.1", "PDO Indicator 1"]
    )
    
    year: int = Field(
        ..., 
        description="The target year that was processed",
        examples=[2024, 2025]
    )
    
    content: str = Field(
        ..., 
        description="""
        Generated report content in markdown format.
        
        The report includes:
        - Progress summary with quantitative achievements
        - Key deliverables with DOI links
        - Cluster contributions and activities
        - Innovations and outcomes (where applicable)
        - Gender and social inclusion aspects
        """,
        examples=[
            "By mid-year 2025, AICCRA had already achieved 850 out of 1200 farmers trained, representing 71% progress for indicator IPI 1.1..."
        ]
    )
    
    status: str = Field(
        default="success", 
        description="Response status indicator",
        examples=["success"]
    )

class ErrorResponse(BaseModel):
    """
    Error response model for failed requests.
    
    Provides detailed error information to help with troubleshooting.
    """
    
    error: str = Field(
        ..., 
        description="Brief error message describing what went wrong",
        examples=[
            "Invalid request parameters",
            "Service configuration error", 
            "AWS Bedrock service unavailable"
        ]
    )
    
    status: str = Field(
        default="error", 
        description="Response status indicator",
        examples=["error"]
    )

    details: Optional[str] = Field(None, description="Additional error details")