"""Pydantic models for API request and response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """Request model for the chat/generate endpoint."""
    indicator: str = Field(
        ..., 
        description="Indicator name for report generation (e.g., 'IPI 1.1', 'PDO Indicator 1')",
        examples=["IPI 1.1", "PDO Indicator 1"]
    )
    year: int = Field(
        ..., 
        description="Year for report generation",
        ge=2020,
        le=2030,
        examples=[2024, 2025]
    )


class ChatResponse(BaseModel):
    """Response model for the chat/generate endpoint."""
    indicator: str = Field(..., description="The indicator that was processed")
    year: int = Field(..., description="The year that was processed")
    content: str = Field(..., description="Generated report content")
    status: str = Field(default="success", description="Response status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Response status")
    details: Optional[str] = Field(None, description="Additional error details")