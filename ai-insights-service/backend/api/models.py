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
        description="S3 folder prefix for the project (0-3 documents, or 0-2 if 'text' is provided). Also used as the STAR contract ID.",
        examples=["a1578"]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user identifier for interaction tracking",
        examples=["user123"]
    )
    text: Optional[str] = Field(
        default=None,
        description="Optional free-text input from the user, included in the AI context as additional user-provided information",
        examples=["Focus the overview on the project's contribution to gender equity."]
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
    text: str = Field(
        default="",
        description="Free-text user input received for this overview. Empty string means no text was provided."
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


class PromptSections(BaseModel):
    """The four editable sections of a managed prompt."""

    system_role: str = Field(
        ...,
        min_length=1,
        description="Who the model is and how it should behave",
        examples=["## ROLE:\nYou are an expert analyst specializing in research projects."]
    )
    context: str = Field(
        ...,
        min_length=1,
        description=(
            "Template describing the context supplied to the model. Contains read-only "
            "{variable} placeholders replaced with real content at generation time."
        ),
        examples=["## CONTEXT YOU WILL RECEIVE:\n{available_context_sources}\n\n{project_information}"]
    )
    user_instructions: str = Field(
        ...,
        min_length=1,
        description="The task the model must perform, plus the guidelines it must follow",
        examples=["## TASK:\nSynthesize all the context above into a single project overview."]
    )
    expected_output_format: str = Field(
        ...,
        min_length=1,
        description="The exact shape the model's answer must take",
        examples=["## OUTPUT FORMAT:\nReturn ONLY a valid JSON object with the following structure: ..."]
    )


class PromptVariableInfo(BaseModel):
    """A context placeholder the service fills in. Not editable in the Prompt Manager."""

    name: str = Field(..., description="Variable name without braces", examples=["project_information"])
    placeholder: str = Field(
        ...,
        description="How the variable appears inside the prompt text",
        examples=["{project_information}"]
    )
    description: str = Field(..., description="What the service substitutes into this variable")
    required: bool = Field(
        default=True,
        description=(
            "When true, the variable must appear exactly once somewhere in the prompt. "
            "Removing it or repeating it makes the update fail."
        )
    )


class PromptResponse(BaseModel):
    """A managed prompt, with both its default and its current user version."""

    id: str = Field(..., description="Prompt identifier (service or module name)", examples=["project-overview"])
    name: str = Field(..., description="Human-readable prompt name", examples=["Project Overview"])
    description: str = Field(..., description="What this prompt is used for")
    sections: List[str] = Field(
        ...,
        description="Section keys in the order they are assembled into the final prompt",
        examples=[["system_role", "context", "user_instructions", "expected_output_format"]]
    )
    variables: List[PromptVariableInfo] = Field(
        ...,
        description="Context placeholders available to this prompt. Render these read-only."
    )
    default_prompt: PromptSections = Field(
        ...,
        description="The original prompt shipped with the service. Used as fallback and for 'reset to default'."
    )
    user_prompt: PromptSections = Field(
        ...,
        description="The version currently in use. Equal to default_prompt until someone edits it."
    )
    is_modified: bool = Field(
        ...,
        description="True when user_prompt differs from default_prompt"
    )
    created_at: Optional[str] = Field(
        default=None,
        description="UTC timestamp of the first save (ISO 8601). Null while never edited.",
        examples=["2026-08-20T14:02:11.481000+00:00"]
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="UTC timestamp of the last save (ISO 8601). Null while never edited.",
        examples=["2026-08-20T14:02:11.481000+00:00"]
    )
    updated_by: Optional[str] = Field(
        default=None,
        description="Identifier of whoever last saved the prompt",
        examples=["user123"]
    )


class GetPromptsResponse(BaseModel):
    """Response listing every managed prompt."""

    prompts: List[PromptResponse] = Field(
        ...,
        description="All registered prompts. STAR filters by id in the Prompt Manager."
    )


class UpdatePromptRequest(BaseModel):
    """Request model for overwriting the user version of a prompt."""

    id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the prompt to overwrite",
        examples=["project-overview"]
    )
    user_prompt: PromptSections = Field(
        ...,
        description="All four sections. This replaces the stored user version entirely."
    )
    updated_by: Optional[str] = Field(
        default=None,
        description="Optional identifier of the user making the change, recorded for auditing",
        examples=["user123"]
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Short error message")
    status: str = Field(default="error", description="Error status indicator")
    details: Optional[str] = Field(default=None, description="Additional error details")
