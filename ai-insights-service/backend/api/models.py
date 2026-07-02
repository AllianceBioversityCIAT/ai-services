"""Pydantic models for the AI Insights API."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class DocumentOverviewRequest(BaseModel):
    """Request model for generating a document overview."""

    bucket_name: str = Field(
        ...,
        description="Name of the S3 bucket containing the document",
        examples=["cgiar-insights-documents"]
    )
    file_key: str = Field(
        ...,
        description="S3 object key (path) of the document to analyze",
        examples=["reports/annual_report_2024.pdf"]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user identifier for interaction tracking",
        examples=["user123"]
    )


class DocumentOverviewResponse(BaseModel):
    """Successful response model for the document overview endpoint."""

    overview: Dict[str, Any] = Field(
        ...,
        description="Structured document overview extracted by the LLM"
    )
    time_taken: str = Field(
        ...,
        description="Total processing time in seconds",
        examples=["4.32"]
    )
    file_key: str = Field(
        ...,
        description="S3 object key of the analyzed document"
    )
    bucket_name: str = Field(
        ...,
        description="S3 bucket of the analyzed document"
    )
    extraction_method: str = Field(
        ...,
        description="Text extraction method used: 'textract' or 'standard'",
        examples=["standard", "textract"]
    )
    interaction_id: Optional[str] = Field(
        default=None,
        description="Interaction tracking ID if user_id was provided"
    )
    status: str = Field(
        default="success",
        description="Processing status",
        examples=["success"]
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Short error message")
    status: str = Field(default="error", description="Error status indicator")
    details: Optional[str] = Field(default=None, description="Additional error details")
