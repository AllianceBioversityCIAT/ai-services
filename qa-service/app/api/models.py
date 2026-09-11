"""Pydantic models for PRMS QA API."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class PrmsRequest(BaseModel):
    """
    Request model for processing PRMS result metadata.
    """
    result_metadata: Dict[str, Any] = Field(
        ...,
        description="JSON metadata for the PRMS result, including fields like result_name, result_description, etc.",
        examples=[{
            "result_id": "8",
            "result_type_name": "Innovation Development",
            "result_level_name": "Output",
            "result_name": "Original Title",
            "result_description": "Original Description"
        }]
    )
    user_id: Optional[str] = Field(
        None,
        description="Optional user identifier for tracking interactions.",
        examples=["user123"]
    )

class PrmsResponse(BaseModel):
    """
    Successful response model for PRMS QA API.
    """
    time_taken: str = Field(..., description="Time taken to process in seconds", examples=["1.23"])
    json_content: Dict[str, Any] = Field(..., description="Parsed JSON content from the LLM response", examples=[{"new_title": "Improved Title", "new_description": "Improved Description"}])
    interaction_id: Optional[str] = Field(None, description="Optional interaction tracking ID", examples=["abc123"])
    evidence_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata about the evidences processed", examples=[{"evidence_count": 3, "successful_evidences": 2}])
    status: str = Field(default="success", description="Status indicator", examples=["success"])

class ErrorResponse(BaseModel):
    """
    Error response model for PRMS QA API.
    """
    error: str = Field(..., description="User-friendly error message", examples=["Validation Error", "Service is temporarily overloaded"])
    status: str = Field(default="error", description="Error status indicator", examples=["error"])
    message: str = Field(..., description="Technical error message", examples=["Missing required field: result_name"])
    error_type: str = Field(..., description="Error type for frontend handling", examples=["VALIDATION_ERROR", "THROTTLING_ERROR"])
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Debug information for development")