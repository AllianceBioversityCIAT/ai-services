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


class AvailableFile(BaseModel):
    """A file currently available in the project S3 folder."""

    file_key: str = Field(..., description="Full S3 object key")
    file_name: str = Field(..., description="File name only")


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
        examples=["success", "empty"]
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


class GetDocumentOverviewResponse(DocumentOverviewResponse):
    """GET response: cached overview plus files currently available in S3."""

    available_files: List[AvailableFile] = Field(
        default_factory=list,
        description="Files currently available in the project S3 folder (excluding response.json)"
    )


class DeleteProjectFilesRequest(BaseModel):
    """Request model for deleting files from a project folder in S3."""

    bucket_name: str = Field(
        ...,
        description="Name of the S3 bucket containing the project documents",
        examples=["ai-services-ibd"]
    )
    project_folder: str = Field(
        ...,
        description="S3 folder prefix for the project",
        examples=["star/ai-insights/projects/abc123"]
    )
    file_names: List[str] = Field(
        ...,
        min_length=1,
        description="File names to delete (file name only, not full path)",
        examples=[["report.pdf", "proposal.docx"]]
    )


class DeleteProjectFilesResponse(BaseModel):
    """Response model for file deletion."""

    bucket_name: str = Field(..., description="S3 bucket where files were deleted")
    project_folder: str = Field(..., description="Project folder prefix")
    deleted_files: List[str] = Field(..., description="File names that were deleted")
    status: str = Field(default="success", description="Deletion status")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Short error message")
    status: str = Field(default="error", description="Error status indicator")
    details: Optional[str] = Field(default=None, description="Additional error details")
