"""
FastAPI application for General AI Services Feedback System.

This service handles the collection, storage, and retrieval of user feedback
on AI-generated responses across different AI services for quality improvement 
and monitoring.
"""

from fastapi import FastAPI
from app.api.routes import router
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.utils.logger.logger_util import get_logger
from app.utils.feedback.feedback_util import ai_interaction_service

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("🚀 AI Interaction Tracking API starting up...")
    logger.info("✅ Multi-service interaction tracking system ready")
    logger.info("📊 Analytics and monitoring capabilities active")
    logger.info("🔧 Service auto-registration enabled")
    
    yield
    
    # Shutdown
    logger.info("🛑 AI Interaction Tracking API shutting down...")
    logger.info("💾 All interaction data safely stored")


app = FastAPI(
    lifespan=lifespan,
    title="AI Interaction Tracking API",
    description="""
    🔄 AI Interaction Tracking System
    
    A comprehensive interaction tracking service for monitoring, analyzing, and collecting
    feedback on AI-generated responses across multiple AI services and applications.
    
    🎯 Dual-Purpose Architecture
    
    This service handles two primary functions:
    
    1. Interaction Tracking
    - Records every AI interaction for analytics and monitoring
    - Tracks user inputs, AI outputs, and performance metrics
    - Provides comprehensive interaction history
    
    2. Feedback Collection 
    - Captures user feedback on AI responses when provided
    - Supports both immediate feedback and delayed feedback updates
    - Enables sentiment analysis and satisfaction tracking
    
    Currently Supported AI Services:
    - Chatbot Service: Conversational AI interactions
    - Text Mining: Text analysis and processing services
    
    🚀 Key Features
    
    - 📝 Tracking: Works with any AI service
    - 🔍 Advanced Analytics: Service-specific and cross-service insights
    - 📊 Real-time Monitoring: Track AI service performance and user engagement
    - 🔒 Secure Storage: DynamoDB with environment separation (test/prod)
    - 📈 Scalable Design: Built to handle interactions from multiple services
    - �️ Rich Context Support: Flexible metadata for service-specific insights
    
    📊 Analytics & Monitoring
    
    Cross-Service Analytics:
    - Compare interaction volumes and feedback rates across different AI services
    - Identify which services have the highest user engagement
    - Track performance trends over time
    - Monitor user experience across the AI ecosystem
    
    Service-Specific Insights:
    - Context-aware analytics based on service type
    - Performance metrics tailored to each AI service
    - Custom reporting for different stakeholder needs
    - Improvement recommendations based on interaction patterns
    
    �️ Service Registration
    
    Automatic Service Discovery:
    - New AI services are automatically registered when first encountered
    - Service metadata is stored for analytics and monitoring
    - Context fields are tracked for service-specific insights
    
    Manual Service Registration:
    Services can also be explicitly registered with detailed metadata for
    enhanced analytics and monitoring capabilities.
    
    📈 Future Enhancements
    
    - Real-time Dashboards: Live monitoring of AI service performance
    - Machine Learning Insights: Predictive analytics on interaction patterns
    - API Integrations: Webhooks and real-time notifications
    - Advanced Filtering: Complex queries across multiple dimensions
    
    🔒 Security & Privacy
    
    - Secure Storage: All interactions encrypted and stored in DynamoDB
    - Access Control: IAM-based access control for sensitive operations
    - Data Privacy: Configurable data retention and anonymization
    - Audit Trails: Complete tracking of all interaction operations
    
    📝 Data Structure
    
    Comprehensive Interaction Records:
    Each interaction entry captures:
    - Core interaction data (input, output, performance)
    - Optional feedback (type, comments, ratings)
    - Service information (name, context)
    - User context (ID, session, platform)
    - Service-specific metadata (flexible context)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Interactions",
            "description": "Interaction tracking and feedback collection for AI services",
        },
        {
            "name": "Health",
            "description": "Service health and status monitoring",
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get(
    "/",
    tags=["Health"],
    summary="API Information",
    description="Get comprehensive information about the AI Services Feedback API",
    response_description="API metadata, capabilities, and integration guide"
)
async def root():
    """Root endpoint providing comprehensive API information."""
    return {
        "service": "AI Interaction Tracking API",
        "version": "1.0.0",
        "description": "Interaction tracking and feedback collection system for AI services",
        "purpose": "Track all AI interactions and collect optional user feedback across multiple AI services",
        
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        
        "core_endpoints": {
            "POST /api/interactions": "Track AI interactions and optionally submit feedback",
            "GET /api/interactions/summary": "Get cross-service analytics summary",
            "POST /api/interactions/search": "Advanced interaction search and filtering",
            "GET /api/feedback/services": "Get registered AI services information",
            "GET /api/feedback/service/{service_name}": "Get service-specific interactions"
        },
        
        "supported_ai_services": {
            "chatbot": {
                "description": "Conversational AI interactions",
                "context_fields": ["filters_applied"],
                "metrics": ["response_time", "user_satisfaction", "context_retention"]
            },
        },
        
        "interaction_capabilities": {
            "interaction_tracking": "Complete AI interaction recording",
            "feedback_collection": "Optional user feedback on interactions",
            "dual_mode_support": "Initial tracking + feedback updates",
            "feedback_types": ["positive", "negative"],
            "comment_support": "Optional detailed feedback with 5000 character limit",
            "context_flexibility": "Service-specific metadata and context",
            "performance_tracking": "Response time, confidence scores, model information",
            "user_tracking": "Session-based and user-based interaction correlation"
        },
        
        "analytics_features": {
            "interaction_volume_tracking": "Monitor AI service usage patterns",
            "feedback_rate_analysis": "Track what percentage of interactions receive feedback",
            "cross_service_comparison": "Compare performance across AI services",
            "service_specific_insights": "Detailed analytics per AI service",
            "time_based_trends": "Track performance and engagement over time",
            "user_experience_monitoring": "Session and user journey analytics",
            "satisfaction_analysis": "Sentiment and satisfaction tracking"
        },
        
        "integration_guide": {
            "step_1": "Choose your AI service name (e.g., 'my-ai-service')",
            "step_2": "Structure your interaction data according to AIInteractionRequest model",
            "step_3": "Include service-specific context in the 'context' field",
            "step_4": "POST to /api/interactions endpoint after each AI interaction",
            "step_5": "Optionally update with feedback using update_mode=true",
            "step_6": "Monitor your service performance via analytics endpoints"
        },
        
        "storage_architecture": {
            "current": "DynamoDB with single table design",
            "environment_separation": "Separate tables for test and production",
            "table_naming": "ai-requests-{environment}",
            "backup": "Multi-region replication for data safety",
            "retention": "Configurable data retention policies"
        },
        
        "technology_stack": {
            "api_framework": "FastAPI with Pydantic validation",
            "storage": "DynamoDB with single table design",
            "analytics": "Built-in aggregation and reporting",
            "deployment": "AWS Lambda with Mangum",
            "monitoring": "Comprehensive logging and error tracking"
        },
        
        "quality_assurance": {
            "data_validation": "Strict Pydantic model validation",
            "error_handling": "Comprehensive error tracking and recovery",
            "logging": "Detailed operation logging for debugging",
            "monitoring": "Health checks and performance monitoring"
        }
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the AI Interaction Tracking API",
    response_description="Service health status, capabilities, and system information"
)
async def health():
    """Health check endpoint with detailed service status."""
    try:
        # Get service statistics
        registered_services = ai_interaction_service.get_registered_services()
        
        return {
            "status": "healthy",
            "service": "AI Interaction Tracking API",
            "version": "1.0.0",
            "timestamp": "2025-01-21T12:00:00Z",
            
            "capabilities": {
                "interaction_tracking": "operational",
                "feedback_collection": "operational",
                "multi_service_support": "active",
                "analytics": "available",
                "search": "operational",
                "storage": "dynamodb_active",
                "service_registration": "automatic",
                "environment_separation": "enabled"
            },
            
            "registered_services": {
                "count": len(registered_services),
                "services": list(registered_services.keys()),
                "auto_registration": "enabled"
            },
            
            "system_info": {
                "interaction_storage": "DynamoDB",
                "table_design": "Single table with environment separation",
                "api_framework": "FastAPI",
                "deployment": "AWS Lambda ready",
                "cors": "enabled",
                "validation": "Pydantic models"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "AI Interaction Tracking API",
            "error": str(e),
            "timestamp": "2025-01-21T12:00:00Z"
        }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception in AI Interaction Tracking Service: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "service": "AI Interaction Tracking API",
            "details": "An unexpected error occurred while processing your request.",
            "support": {
                "documentation": "/docs",
                "health_check": "/health"
            }
        }
    )