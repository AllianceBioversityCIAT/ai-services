"""Pydantic models for API request and response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime, timezone
import uuid

class AIInteractionRequest(BaseModel):
    """
    Request model for tracking AI interactions and optionally submitting feedback.
    
    This model captures all AI interactions with optional feedback data for quality improvement
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
        description="AI-generated output from the interaction",
        examples=[
            "Based on the latest data, AICCRA has achieved significant progress...",
            "The climate data shows trends of..."
        ]
    )
    
    # Optional feedback data (only provided when user gives feedback)
    feedback_type: Optional[Literal["positive", "negative"]] = Field(
        default=None,
        description="Type of feedback - positive (thumbs up) or negative (thumbs down). Only provided when user gives feedback.",
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
    
    # Update mode for feedback
    update_mode: Optional[bool] = Field(
        default=False,
        description="Set to true when updating existing interaction with feedback",
        examples=[False, True]
    )
    
    interaction_id: Optional[str] = Field(
        default=None,
        description="Existing interaction ID when updating with feedback",
        examples=["req_550e8400-e29b-41d4-a716-446655440000"]
    )
    
    # AI Service Information
    service_name: str = Field(
        ...,
        description="Name of the AI service being evaluated",
        examples=["chatbot", "reports-generator", "text-mining"]
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Optional human-readable display name for the service. If provided, will be used for service registration instead of auto-generated name.",
        examples=["AICCRA Chatbot", "Reports Generator AI", "Advanced Text Mining Service"]
    )
    
    service_description: Optional[str] = Field(
        default=None,
        description="Optional description of the AI service. If provided, will be used for service registration instead of auto-generated description.",
        examples=[
            "Conversational AI for AICCRA data exploration",
            "AI-powered reports generation service",
            "Advanced text analysis and mining capabilities"
        ]
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


class AIInteractionResponse(BaseModel):
    """Response model for successful AI interaction tracking."""
    
    interaction_id: str = Field(
        ...,
        description="Unique identifier for the tracked interaction",
        examples=["req_550e8400-e29b-41d4-a716-446655440000"]
    )
    
    status: str = Field(
        default="success",
        description="Status of the interaction tracking",
        examples=["success", "updated"]
    )
    
    message: str = Field(
        default="Interaction tracked successfully",
        description="Confirmation message",
        examples=[
            "AI interaction tracked successfully",
            "Interaction updated with feedback successfully"
        ]
    )
    
    timestamp: datetime = Field(
        ...,
        description="Timestamp when the interaction was processed",
        examples=["2025-01-27T10:30:00Z"]
    )
    
    service_name: str = Field(
        ...,
        description="Name of the service that generated the interaction"
    )
    
    has_feedback: bool = Field(
        default=False,
        description="Whether this interaction includes feedback",
        examples=[True, False]
    )


class InteractionSummary(BaseModel):
    """Model for AI interaction analytics and summary data."""
    
    service_name: Optional[str] = Field(
        default=None,
        description="Service name filter applied (null for all services)"
    )
    
    total_interactions: int = Field(
        ...,
        description="Total number of AI interactions"
    )
    
    interactions_with_feedback: int = Field(
        ...,
        description="Number of interactions that have feedback"
    )
    
    positive_feedback: int = Field(
        ...,
        description="Number of positive feedback entries"
    )
    
    negative_feedback: int = Field(
        ...,
        description="Number of negative feedback entries"
    )
    
    feedback_rate: float = Field(
        ...,
        description="Percentage of interactions that received feedback (0.0 to 100.0)",
        ge=0.0,
        le=100.0
    )
    
    satisfaction_rate: float = Field(
        ...,
        description="Percentage of positive feedback among feedback entries (0.0 to 100.0)",
        ge=0.0,
        le=100.0
    )
    
    average_response_time: Optional[float] = Field(
        default=None,
        description="Average AI response time in seconds"
    )
    
    services_breakdown: Dict[str, Dict[str, int]] = Field(
        ...,
        description="Breakdown of interactions and feedback by service",
        examples=[{
            "chatbot": {"total_interactions": 1000, "positive": 150, "negative": 25, "no_feedback": 825},
            "reports-generator": {"total_interactions": 500, "positive": 89, "negative": 12, "no_feedback": 399}
        }]
    )
    
    recent_interactions: List[Dict[str, Any]] = Field(
        ...,
        description="Recent interaction entries (last 10)"
    )
    
    time_period: Dict[str, Optional[datetime]] = Field(
        ...,
        description="Time period for the summary data"
    )


class GetInteractionRequest(BaseModel):
    """Request model for retrieving AI interaction data."""
    
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
    
    has_feedback: Optional[bool] = Field(
        default=None,
        description="Filter by whether interaction includes feedback"
    )
    
    has_comment: Optional[bool] = Field(
        default=None,
        description="Filter by whether feedback includes comments"
    )
    
    # Time filters
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter interactions from this date onwards"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter interactions up to this date"
    )
    
    max_response_time: Optional[float] = Field(
        default=None,
        description="Filter by maximum response time in seconds"
    )
    
    # Result controls
    limit: Optional[int] = Field(
        default=50,
        description="Maximum number of interaction entries to return",
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
    service: str = Field(default="ai-interaction-service", description="Service name")