"""Pydantic models for the AI Insights API."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class DocumentOverviewRequest(BaseModel):
    """Request model for generating a project overview."""

    bucket_name: str = Field(
        ...,
        description="Name of the S3 bucket containing the project documents",
        examples=["ai-services-ibd"]
    )
    project_folder: str = Field(
        ...,
        description="S3 folder prefix for the project (1-3 documents)",
        examples=["star/ai-insights/projects/abc123"]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user identifier for interaction tracking",
        examples=["user123"]
    )


class ProcessedDocument(BaseModel):
    """Metadata for a document processed during overview generation."""

    file_key: str = Field(..., description="S3 object key of the processed document")
    file_name: str = Field(..., description="File name extracted from the S3 object key")
    extraction_method: str = Field(
        ...,
        description="Text extraction method used: 'textract' or 'standard'",
        examples=["textract", "standard"]
    )
    character_count: int = Field(..., description="Number of characters extracted from the document")


class DocumentOverviewResponse(BaseModel):
    """Successful response model for the project overview endpoint."""

    overview: Dict[str, Any] = Field(
        ...,
        description="Structured project overview extracted by the LLM"
    )
    time_taken: str = Field(
        ...,
        description="Total processing time in seconds",
        examples=["24.32"]
    )
    project_folder: str = Field(
        ...,
        description="S3 folder prefix of the analyzed project"
    )
    bucket_name: str = Field(
        ...,
        description="S3 bucket of the analyzed project"
    )
    documents_processed: List[ProcessedDocument] = Field(
        ...,
        description="List of documents extracted and analyzed"
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
    generated_at: Optional[str] = Field(
        default=None,
        description="UTC timestamp when the overview was generated (ISO 8601)",
        examples=["2026-07-03T15:32:29.230000+00:00"]
    )
    cached: bool = Field(
        default=False,
        description="True when the response was loaded from a cached response.json file"
    )

class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Short error message")
    status: str = Field(default="error", description="Error status indicator")
    details: Optional[str] = Field(default=None, description="Additional error details")
