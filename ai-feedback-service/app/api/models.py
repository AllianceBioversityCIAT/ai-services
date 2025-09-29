"""Pydantic models for API request and response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timezone
import uuid

class FeedbackRequest(BaseModel):
    """
    General request model for submitting feedback on AI service responses.
    
    This model captures user feedback on AI-generated content for quality improvement
    and service monitoring purposes across different AI services.
    """
    
    # User and Session Context
    user_id: str = Field(
        ...,
        description="User identifier (email, ID, or session-based identifier)",
        examples=["user@example.com", "researcher@cgiar.org", "session_user_123"]
    )
    
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID from the original interaction (if applicable)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    # AI Interaction Data
    user_input: Optional[str] = Field(
        default=None,
        description="Original user input/request that was sent to the AI service",
        examples=[
            "What progress has been made on IPI 1.1 in 2025?",
            "Generate a summary of the climate data"
        ]
    )
    
    ai_output: str = Field(
        ...,
        description="AI-generated output that the user is providing feedback on",
        examples=[
            "Based on the latest data, AICCRA has achieved significant progress...",
            "The climate data shows trends of..."
        ]
    )
    
    # Core feedback data
    feedback_type: Literal["positive", "negative"] = Field(
        ...,
        description="Type of feedback - positive (thumbs up) or negative (thumbs down)",
        examples=["positive", "negative"]
    )
    
    feedback_comment: Optional[str] = Field(
        default=None,
        description="Optional detailed feedback comment from the user",
        max_length=5000,
        examples=[
            "Great response with detailed information",
            "The response was not relevant to my question",
            "Missing important context about climate data"
        ]
    )
    
    # AI Service Information
    service_name: str = Field(
        ...,
        description="Name of the AI service being evaluated",
        examples=["chatbot", "reports-generator", "text-mining"]
    )
    
    # Flexible context and metadata
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context specific to the AI service",
        examples=[{
            # For chatbot
            "filters_applied": {
                "phase": "Progress 2025",
                "indicator": "IPI 1.1",
                "section": "All sections"
            }
        }]
    )
    
    # Performance and technical metadata
    response_time_seconds: Optional[float] = Field(
        default=None,
        description="Time taken by AI service to generate the response",
        examples=[2.5, 15.3, 120.7]
    )
    
    # Additional metadata
    platform: Optional[str] = Field(
        default=None,
        description="Platform or application where the feedback is coming from",
        examples=["STAR", "AICCRA", "PRMS"]
    )


class FeedbackResponse(BaseModel):
    """Response model for successful feedback submission."""
    
    feedback_id: str = Field(
        ...,
        description="Unique identifier for the submitted feedback",
        examples=["fb_550e8400-e29b-41d4-a716-446655440000"]
    )
    
    status: str = Field(
        default="success",
        description="Status of the feedback submission",
        examples=["success"]
    )
    
    message: str = Field(
        default="Feedback submitted successfully",
        description="Confirmation message",
        examples=[
            "Feedback submitted successfully. Thank you for helping us improve!",
            "Your feedback has been recorded and will help improve our AI services."
        ]
    )
    
    timestamp: datetime = Field(
        ...,
        description="Timestamp when the feedback was processed",
        examples=["2025-01-27T10:30:00Z"]
    )
    
    service_name: str = Field(
        ...,
        description="Name of the service that received the feedback"
    )


class FeedbackSummary(BaseModel):
    """Model for feedback analytics and summary data."""
    
    service_name: Optional[str] = Field(
        default=None,
        description="Service name filter applied (null for all services)"
    )
    
    total_feedback: int = Field(
        ...,
        description="Total number of feedback entries"
    )
    
    positive_feedback: int = Field(
        ...,
        description="Number of positive feedback entries"
    )
    
    negative_feedback: int = Field(
        ...,
        description="Number of negative feedback entries"
    )
    
    satisfaction_rate: float = Field(
        ...,
        description="Percentage of positive feedback (0.0 to 100.0)",
        ge=0.0,
        le=100.0
    )
    
    average_response_time: Optional[float] = Field(
        default=None,
        description="Average AI response time in seconds"
    )
    
    services_breakdown: Dict[str, Dict[str, int]] = Field(
        ...,
        description="Breakdown of feedback by service",
        examples=[{
            "chatbot": {"positive": 150, "negative": 25},
            "reports-generator": {"positive": 89, "negative": 12},
            "text-mining": {"positive": 45, "negative": 8}
        }]
    )
    
    recent_feedback: List[Dict[str, Any]] = Field(
        ...,
        description="Recent feedback entries (last 10)"
    )
    
    time_period: Dict[str, Optional[datetime]] = Field(
        ...,
        description="Time period for the summary data"
    )


class GetFeedbackRequest(BaseModel):
    """Request model for retrieving feedback data."""
    
    # Service filters
    service_name: Optional[str] = Field(
        default=None,
        description="Filter by specific AI service",
        examples=["chatbot", "report-generator", "text-mining"]
    )
    
    # User and session filters
    user_id: Optional[str] = Field(
        default=None,
        description="Filter by specific user identifier",
        examples=["user@example.com", "researcher@cgiar.org"]
    )
    
    # Feedback filters
    feedback_type: Optional[Literal["positive", "negative"]] = Field(
        default=None,
        description="Filter by feedback type"
    )
    
    has_comment: Optional[bool] = Field(
        default=None,
        description="Filter by whether feedback includes comments"
    )
    
    # Time filters
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter feedback from this date onwards"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter feedback up to this date"
    )
    
    max_response_time: Optional[float] = Field(
        default=None,
        description="Filter by maximum response time in seconds"
    )
    
    # Result controls
    limit: Optional[int] = Field(
        default=50,
        description="Maximum number of feedback entries to return",
        le=1000,
        ge=1
    )
    
    offset: Optional[int] = Field(
        default=0,
        description="Number of entries to skip (for pagination)",
        ge=0
    )
    
    sort_by: Optional[Literal["timestamp", "feedback_type", "service_name", "response_time"]] = Field(
        default="timestamp",
        description="Field to sort results by"
    )
    
    sort_order: Optional[Literal["asc", "desc"]] = Field(
        default="desc",
        description="Sort order"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Status indicator")
    details: Optional[str] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str = Field(default="ai-feedback-service", description="Service name")