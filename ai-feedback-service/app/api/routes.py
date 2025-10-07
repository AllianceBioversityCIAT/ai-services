"""REST API endpoints for General AI Services Feedback System."""

import traceback
from pydantic import Field
from datetime import datetime
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from app.utils.logger.logger_util import get_logger
from fastapi import APIRouter, HTTPException, status, Query
from app.utils.feedback.feedback_util import ai_interaction_service

from app.api.models import (
    AIInteractionRequest, AIInteractionResponse, InteractionSummary, GetInteractionRequest, ErrorResponse
)

logger = get_logger()

router = APIRouter()


@router.post(
    "/api/interactions",
    response_model=AIInteractionResponse,
    tags=["Interactions"],
    summary="Track AI interactions and optionally submit feedback",
    description="""
    📝 Track AI Interactions with Optional Feedback
    
    This endpoint tracks all AI interactions and optionally handles feedback submission
    when users provide feedback on AI-generated responses. It serves dual purposes:
    
    1. **Interaction Tracking**: Records every AI interaction for analytics and monitoring
    2. **Feedback Collection**: Captures user feedback when provided

    🔄 Two Usage Modes
    
    **Mode 1: Initial Interaction Tracking**
    - Called by AI services after generating responses
    - Records the interaction with optional immediate feedback
    - Creates new interaction record in database
    
    **Mode 2: Feedback Update**
    - Called by applications when users provide feedback
    - Updates existing interaction with feedback data
    - Requires interaction_id and update_mode=true
    
    📊 Analytics & Monitoring
    
    This unified approach enables:
    - Complete interaction tracking across all AI services
    - Feedback rate analysis (what percentage of interactions get feedback)
    - Service performance monitoring
    - User engagement metrics
    
    🎯 Multi-Service Support
    
    Supports all AI services:
    - `chatbot`: Conversational AI interactions
    - `report-generator`: Document generation services
    - `text-mining`: Text analysis services
    - Any AI service that generates user-facing content
    
    🔒 Data Privacy & Security
    
    - All interactions stored securely in DynamoDB
    - Environment-specific tables (test/prod separation)
    - Flexible context data structure
    - Optional feedback fields for privacy compliance
    """,
    response_description="Interaction tracked successfully with optional feedback",
    responses={
        200: {"model": AIInteractionResponse, "description": "Interaction tracked successfully"},
        400: {"model": ErrorResponse, "description": "Invalid interaction parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error. Interaction tracking failed"}
    }
)
async def track_interaction(interaction_request: AIInteractionRequest) -> AIInteractionResponse:
    """
    Track AI interaction and optionally submit feedback.
    
    This endpoint handles both initial interaction tracking and feedback updates
    for AI-generated responses across all AI services.
    """
    try:
        if interaction_request.update_mode:
            logger.info(f"🔄 Processing feedback update for interaction: {interaction_request.interaction_id}")
        else:
            logger.info(f"📝 Processing new AI interaction for service: {interaction_request.service_name}")
            
        logger.info(f"🔧 Service: {interaction_request.service_name}")
        logger.info(f"👤 User: {interaction_request.user_id}")
        logger.info(f"📊 Has Feedback: {interaction_request.feedback_type is not None}")
        logger.info(f"💭 Has Comment: {interaction_request.feedback_comment is not None}")
        
        response = ai_interaction_service.track_interaction(interaction_request)
        
        if interaction_request.update_mode:
            logger.info(f"✅ Interaction updated successfully: {response.interaction_id}")
        else:
            logger.info(f"✅ Interaction tracked successfully: {response.interaction_id}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error in interaction tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid interaction parameters",
                "details": str(e),
                "status": "error"
            }
        )
    except RuntimeError as e:
        logger.error(f"Runtime error in interaction tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Interaction tracking failed",
                "details": str(e),
                "status": "error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in interaction tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "details": "An unexpected error occurred while processing interaction",
                "status": "error"
            }
        )


@router.get(
    "/api/interactions/summary",
    response_model=InteractionSummary,
    tags=["Interactions"],
    summary="Get interaction analytics summary",
    description="""
    📊 Multi-Service Interaction Analytics
    
    Retrieve comprehensive analytics and summary statistics for AI interactions
    across all AI services or filtered by specific services.
    
    Analytics Include:
    - Total interaction counts by service
    - Feedback rates and satisfaction rates
    - Service performance comparison
    - Recent interaction samples
    - Time-based analytics
    
    Key Metrics:
    - **Total Interactions**: All AI interactions tracked
    - **Feedback Rate**: Percentage of interactions that received feedback
    - **Satisfaction Rate**: Percentage of positive feedback among feedback entries
    - **Service Breakdown**: Performance comparison across services
    
    Use Cases:
    - Monitor overall AI service usage and quality
    - Compare performance across different services
    - Identify services needing improvement
    - Track user engagement trends over time
    - Generate executive dashboards
    """)
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
) -> InteractionSummary:
    """Get comprehensive interaction analytics across AI services."""
    try:
        logger.info(f"📊 Generating interaction summary...")
        logger.info(f"🔍 Service filter: {service_name or 'All services'}")
        logger.info(f"📅 Date range: {start_date} to {end_date}")
        
        summary = ai_interaction_service.get_interaction_summary(
            service_name=service_name,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info("✅ Interaction summary generated successfully")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating interaction summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to generate interaction summary",
                "details": str(e),
                "status": "error"
            }
        )


@router.post(
    "/api/interactions/search",
    response_model=Dict[str, Any],
    tags=["Interactions"],
    summary="Search and retrieve interaction entries",
    description="""
    🔍 Advanced Interaction Search & Analytics
    
    Retrieve interaction entries with advanced filtering, sorting, and pagination
    capabilities across all AI services.
    
    Advanced Filtering Options:
    - Service Filters: Filter by service name
    - User Filters: Filter by user ID
    - Feedback Filters: Filter by type, comments, or presence of feedback
    - Performance Filters: Filter by response time, model performance
    - Time Filters: Date range filtering with flexible periods
    
    Sorting & Pagination:
    - Sort by timestamp, service, feedback type, response time
    - Configurable page size (up to 1000 entries)
    - Offset-based pagination for large datasets
    
    Response Format:
    ```json
    {
        "interaction_entries": [...],
        "pagination": {
            "total_count": 1250,
            "returned_count": 50,
            "offset": 0,
            "limit": 50,
            "has_more": true
        },
        "filters_applied": {...},
        "summary": {
            "interactions_with_feedback": 30,
            "feedback_rate": 60.0,
            "satisfaction_rate": 85.0
        }
    }
    ```
    
    Use Cases:
    - Investigate specific user interactions
    - Analyze interaction patterns by service
    - Export interaction data for external analysis
    - Research service performance trends
    - Generate detailed reports for stakeholders
    """)
async def search_interactions(search_request: GetInteractionRequest) -> Dict[str, Any]:
    """Search and retrieve interaction entries with advanced filtering and pagination."""
    try:
        logger.info(f"🔍 Searching interactions with advanced filters...")
        logger.info(f"🏷️ Service: {search_request.service_name or 'All'}")
        logger.info(f"👤 User: {search_request.user_id or 'All'}")
        logger.info(f"📊 Has Feedback: {search_request.has_feedback or 'All'}")
        logger.info(f"📊 Type: {search_request.feedback_type or 'All'}")
        
        # Get filtered results
        interaction_entries, total_count = ai_interaction_service.get_interactions(search_request)
        
        # Calculate summary statistics
        interactions_with_feedback = sum(1 for entry in interaction_entries if entry.get('has_feedback', False))
        positive_count = sum(1 for entry in interaction_entries if entry.get('feedback_type') == 'positive')
        negative_count = sum(1 for entry in interaction_entries if entry.get('feedback_type') == 'negative')
        
        feedback_rate = (interactions_with_feedback / len(interaction_entries) * 100) if interaction_entries else 0
        satisfaction_rate = (positive_count / interactions_with_feedback * 100) if interactions_with_feedback > 0 else 0
        
        # Prepare response with metadata
        response = {
            "interaction_entries": interaction_entries,
            "pagination": {
                "total_count": total_count,
                "returned_count": len(interaction_entries),
                "offset": search_request.offset,
                "limit": search_request.limit,
                "has_more": total_count > (search_request.offset + len(interaction_entries))
            },
            "filters_applied": {
                "service_name": search_request.service_name,
                "user_id": search_request.user_id,
                "feedback_type": search_request.feedback_type,
                "has_feedback": search_request.has_feedback,
                "has_comment": search_request.has_comment,
                "date_range": {
                    "start_date": search_request.start_date.isoformat() if search_request.start_date else None,
                    "end_date": search_request.end_date.isoformat() if search_request.end_date else None
                }
            },
            "summary": {
                "total_interactions": len(interaction_entries),
                "interactions_with_feedback": interactions_with_feedback,
                "positive_feedback": positive_count,
                "negative_feedback": negative_count,
                "feedback_rate": round(feedback_rate, 2),
                "satisfaction_rate": round(satisfaction_rate, 2)
            }
        }
        
        logger.info(f"✅ Found {len(interaction_entries)} interaction entries (total: {total_count})")
        return response
        
    except Exception as e:
        logger.error(f"Error searching interactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to search interactions",
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
        logger.info(f"🔧 ai_interaction_service object: {type(ai_interaction_service)}")
        
        services = ai_interaction_service.get_registered_services()
        logger.info(f"📋 Raw services data: {services}")
        
        logger.info(f"✅ Retrieved information for {len(services)} registered services")
        return {
            "services": services,
            "total_count": len(services),
            "service_names": list(services.keys())
        }
        
    except Exception as e:
        logger.error(f"❌ Detailed error in get_registered_services: {type(e).__name__}: {str(e)}")
        logger.error(f"❌ ai_interaction_service type: {type(ai_interaction_service)}")
        logger.error(f"❌ ai_interaction_service methods: {dir(ai_interaction_service)}")
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
        logger.info(f"🎯 Retrieving interactions for AI service: {service_name}")
        
        results = ai_interaction_service.get_service_feedback(service_name, limit)
        
        logger.info(f"✅ Found {len(results)} interaction entries for service: {service_name}")
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving service interactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"Failed to retrieve interactions for service: {service_name}",
                "details": str(e),
                "status": "error"
            }
        )