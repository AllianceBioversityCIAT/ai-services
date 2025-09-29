"""REST API endpoints for General AI Services Feedback System."""

import traceback
from pydantic import Field
from datetime import datetime
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from app.utils.logger.logger_util import get_logger
from fastapi import APIRouter, HTTPException, status, Query
from app.utils.feedback.feedback_util import ai_feedback_service

from app.api.models import (
    FeedbackRequest, FeedbackResponse, FeedbackSummary, GetFeedbackRequest, ErrorResponse
)

logger = get_logger()

router = APIRouter()


@router.post(
    "/api/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"],
    summary="Submit feedback on AI service responses",
    description="""
    📝 Submit User Feedback on AI Responses
    
    This endpoint allows users to provide feedback (positive or negative) on AI-generated responses
    to help improve the service quality and monitor performance.

    🔄 Feedback Collection Process
    
    1. Capture Context: Records the original question, AI response, and conversation metadata
    2. Store Feedback: Saves feedback data to S3 with unique tracking ID
    3. Enable Analytics: Provides data for service improvement and quality monitoring
    4. Track Performance: Enables measurement of user satisfaction over time
    
    🎯 Use Cases
    
    Positive Feedback (👍)
    - Response was accurate and helpful
    - Information was relevant and well-structured
    - User found the answer satisfactory
    
    Negative Feedback (👎)
    - Response was inaccurate or misleading
    - Information was not relevant to the question
    - Response missed important context
    - Technical errors or formatting issues

    📊 Feedback Metadata
    
    The system automatically captures:
    - Unique feedback ID for tracking
    - Timestamp of feedback submission
    - Session and user context
    - Response characteristics (length, filters used)
    - Service identification
    
    🎯 Multi-Service Support
    
    This endpoint supports feedback from various AI services:
    
    Currently Supported Services:
    - `chatbot`: Conversational AI interactions
    
    📝 Service-Specific Context
    
    Chatbot Services:
    ```json
    {
        "context": {
            "filters_applied": {"phase": "2025", "indicator": "IPI 1.1"}
        }
    }
    ```

    📊 Automatic Service Registration
    
    New AI services are automatically registered when first encountered:
    - Service information is stored for analytics
    - Context fields are tracked for service-specific insights
    
    🔒 Data Privacy & Security
    
    - All feedback is stored securely in AWS S3
    - User identifiers can be emails, session IDs, or anonymous tokens
    - AI output content is stored for improvement but can be configured for privacy
    - Context data is flexible and can exclude sensitive information
    
    📈 Analytics & Monitoring
    
    Submitted feedback enables:
    - Service-specific satisfaction tracking
    - Cross-service performance comparison
    - User experience monitoring
    - AI model performance insights
    - Context-aware improvement identification
    """,
    response_description="Feedback submitted successfully with tracking information",
    responses={
        200: {"model": FeedbackResponse, "description": "Feedback submitted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid feedback parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error. Feedback submission failed"}
    }
)
async def submit_feedback(feedback_request: FeedbackRequest) -> FeedbackResponse:
    """
    Submit user feedback on AI-generated responses from any AI service.
    
    This endpoint processes user feedback to help improve AI service quality
    and provides tracking for service performance monitoring across different AI applications.
    """
    try:
        logger.info(f"📝 Processing feedback submission for AI service...")
        logger.info(f"🔧 Service: {feedback_request.service_name}")
        logger.info(f"👤 User: {feedback_request.user_id}")
        logger.info(f"📊 Feedback Type: {feedback_request.feedback_type}")
        logger.info(f"💭 Has Comment: {feedback_request.feedback_comment is not None}")
        
        response = ai_feedback_service.submit_feedback(feedback_request)
        
        logger.info(f"✅ Feedback submitted successfully: {response.feedback_id}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error in feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid feedback parameters",
                "details": str(e),
                "status": "error"
            }
        )
    except RuntimeError as e:
        logger.error(f"Runtime error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Feedback submission failed",
                "details": str(e),
                "status": "error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in feedback submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "details": "An unexpected error occurred while processing feedback",
                "status": "error"
            }
        )


@router.get(
    "/api/feedback/summary",
    response_model=FeedbackSummary,
    tags=["Feedback"],
    summary="Get feedback analytics summary",
    description="""
    📊 Multi-Service Feedback Analytics
    
    Retrieve comprehensive analytics and summary statistics for user feedback
    across all AI services or filtered by specific services.
    
    Analytics Include:
    - Total feedback counts by service
    - Satisfaction rates and trends
    - Service performance comparison
    - Recent feedback samples
    - Time-based analytics
    
    Service Breakdown:
    - Individual service satisfaction rates
    - Cross-service performance comparison
    - Service-specific feedback volume
    - Response time analytics (if available)
    
    Use Cases:
    - Monitor overall AI service quality
    - Compare performance across different services
    - Identify services needing improvement
    - Track satisfaction trends over time
    - Generate executive dashboards
    """
)
async def get_feedback_summary(
    service_name: Optional[str] = Query(
        None, 
        description="Filter by specific AI service",
        examples=["chatbot", "report-generator", "text-mining"]
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter from this date (ISO format: 2025-01-01T00:00:00Z)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter until this date (ISO format: 2025-12-31T23:59:59Z)"
    )
) -> FeedbackSummary:
    """Get comprehensive feedback analytics across AI services."""
    try:
        logger.info(f"📊 Generating feedback summary...")
        logger.info(f"🔍 Service filter: {service_name or 'All services'}")
        logger.info(f"📅 Date range: {start_date} to {end_date}")
        
        summary = ai_feedback_service.get_feedback_summary(
            service_name=service_name,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info("✅ Feedback summary generated successfully")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating feedback summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to generate feedback summary",
                "details": str(e),
                "status": "error"
            }
        )


@router.post(
    "/api/feedback/search",
    response_model=Dict[str, Any],
    tags=["Feedback"],
    summary="Search and retrieve feedback entries",
    description="""
    🔍 Advanced Feedback Search & Analytics
    
    Retrieve feedback entries with advanced filtering, sorting, and pagination
    capabilities across all AI services.
    
    Advanced Filtering Options:
    - Service Filters: Filter by service name
    - User Filters: Filter by user ID
    - Feedback Filters: Filter by type, comments
    - Performance Filters: Filter by response time, model performance
    - Time Filters: Date range filtering with flexible periods
    
    Sorting & Pagination:
    - Sort by timestamp, service, feedback type, response time
    - Configurable page size (up to 1000 entries)
    - Offset-based pagination for large datasets
    
    Response Format:
    ```json
    {
        "feedback_entries": [...],
        "pagination": {
            "total_count": 1250,
            "returned_count": 50,
            "offset": 0,
            "limit": 50,
            "has_more": true
        },
        "filters_applied": {...},
        "summary": {
            "positive_count": 30,
            "negative_count": 20
        }
    }
    ```
    
    Use Cases:
    - Investigate specific user complaints
    - Analyze feedback patterns by service
    - Export feedback data for external analysis
    - Research service performance trends
    - Generate detailed reports for stakeholders
    """
)
async def search_feedback(search_request: GetFeedbackRequest) -> Dict[str, Any]:
    """Search and retrieve feedback entries with advanced filtering and pagination."""
    try:
        logger.info(f"🔍 Searching feedback with advanced filters...")
        logger.info(f"🏷️ Service: {search_request.service_name or 'All'}")
        logger.info(f"👤 User: {search_request.user_id or 'All'}")
        logger.info(f"📊 Type: {search_request.feedback_type or 'All'}")
        
        # Get filtered results
        feedback_entries, total_count = ai_feedback_service.get_feedback(search_request)
        
        # Calculate summary statistics
        positive_count = sum(1 for entry in feedback_entries if entry.get('feedback_type') == 'positive')
        negative_count = len(feedback_entries) - positive_count
        
        # Prepare response with metadata
        response = {
            "feedback_entries": feedback_entries,
            "pagination": {
                "total_count": total_count,
                "returned_count": len(feedback_entries),
                "offset": search_request.offset,
                "limit": search_request.limit,
                "has_more": total_count > (search_request.offset + len(feedback_entries))
            },
            "filters_applied": {
                "service_name": search_request.service_name,
                "user_id": search_request.user_id,
                "feedback_type": search_request.feedback_type,
                "has_comment": search_request.has_comment,
                "date_range": {
                    "start_date": search_request.start_date.isoformat() if search_request.start_date else None,
                    "end_date": search_request.end_date.isoformat() if search_request.end_date else None
                }
            },
            "summary": {
                "positive_count": positive_count,
                "negative_count": negative_count,
                "satisfaction_rate": (positive_count / len(feedback_entries) * 100) if feedback_entries else 0
            }
        }
        
        logger.info(f"✅ Found {len(feedback_entries)} feedback entries (total: {total_count})")
        return response
        
    except Exception as e:
        logger.error(f"Error searching feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to search feedback",
                "details": str(e),
                "status": "error"
            }
        )


@router.get(
    "/api/feedback/services",
    response_model=Dict[str, Any],
    tags=["Feedback"],
    summary="Get registered AI services information",
    description="""
    🏗️ Registered AI Services Registry
    
    Get information about all registered AI services that are collecting feedback
    through this system.
    
    Service Information Includes:
    - Service display name and description
    - Expected context fields
    - Registration timestamp
    - Feedback collection status
    
    Use Cases:
    - Service discovery and integration
    - Understanding available feedback sources
    - API documentation generation
    - Service monitoring and management
    """
)
async def get_registered_services() -> Dict[str, Any]:
    """Get information about all registered AI services."""
    try:
        logger.info("📋 Retrieving registered AI services information")
        logger.info(f"🔧 ai_feedback_service object: {type(ai_feedback_service)}")
        
        services = ai_feedback_service.get_registered_services()
        logger.info(f"📋 Raw services data: {services}")
        
        logger.info(f"✅ Retrieved information for {len(services)} registered services")
        return {
            "services": services,
            "total_count": len(services),
            "service_names": list(services.keys())
        }
        
    except Exception as e:
        logger.error(f"❌ Detailed error in get_registered_services: {type(e).__name__}: {str(e)}")
        logger.error(f"❌ ai_feedback_service type: {type(ai_feedback_service)}")
        logger.error(f"❌ ai_feedback_service methods: {dir(ai_feedback_service)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        logger.error(f"Error retrieving services: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to retrieve services information",
                "details": str(e),
                "status": "error"
            }
        )


@router.get(
    "/api/feedback/service/{service_name}",
    response_model=List[Dict[str, Any]],
    tags=["Feedback"],
    summary="Get feedback for a specific AI service",
    description="""
    🎯 Service-Specific Feedback Analytics
    
    Retrieve all feedback entries for a specific AI service with service-optimized
    analytics and insights.
    
    Service-Specific Features:
    - Context-aware filtering based on service type
    - Service-specific performance metrics
    - Tailored analytics for different AI service types
    - Recent feedback trends for the service
    
    Supported Services:
    - `chatbot`: Conversational AI feedback
    - Any registered AI service
    """
)
async def get_service_feedback(
    service_name: str,
    limit: int = Query(50, description="Maximum number of entries to return", le=500)
) -> List[Dict[str, Any]]:
    """Get all feedback for a specific AI service."""
    try:
        logger.info(f"🎯 Retrieving feedback for AI service: {service_name}")
        
        results = ai_feedback_service.get_service_feedback(service_name, limit)
        
        logger.info(f"✅ Found {len(results)} feedback entries for service: {service_name}")
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving service feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"Failed to retrieve feedback for service: {service_name}",
                "details": str(e),
                "status": "error"
            }
        )