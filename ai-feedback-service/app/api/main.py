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

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("🚀 AI Services Feedback API starting up...")
    logger.info("✅ Multi-service feedback collection system ready")
    logger.info("📊 Analytics and monitoring capabilities active")
    logger.info("🔧 Service auto-registration enabled")
    
    yield
    
    # Shutdown
    logger.info("🛑 AI Services Feedback API shutting down...")
    logger.info("💾 All feedback data safely stored")


app = FastAPI(
    lifespan=lifespan,
    title="AI Services Feedback API",
    description="""
    🔄 **AI Feedback Collection System**
    
    A comprehensive feedback management service for collecting, storing, and analyzing
    user feedback on AI-generated responses across multiple AI services and applications.
    
    ## 🎯 **Multi-Service Architecture**
    
    This service is designed to handle feedback from any AI service:
    
    **Currently Supported AI Services:**
    - **Chatbot Service**: Conversational AI interactions
    
    ## 🚀 **Key Features**
    
    - 📝 **Feedback Collection**: Works with any AI service
    - 🔍 **Advanced Analytics**: Service-specific and cross-service insights
    - 📊 **Real-time Monitoring**: Track AI service performance and user satisfaction
    - 🔒 **Secure Storage**: AWS S3 with future database migration support
    - 📈 **Scalable Design**: Built to handle feedback from multiple services
    - 🎛️ **Rich Context Support**: Flexible metadata for service-specific insights
    
    ## 🔧 **Integration Examples**
    
    **Chatbot Service Integration:**
    ```python
    import requests
    
    # Submit chatbot feedback
    feedback_response = requests.post('/api/feedback', json={
        'feedback_type': 'positive',
        'feedback_comment': 'Great response with detailed information',
        'service_name': 'chatbot',
        'user_id': 'user@example.com',
        'session_id': 'chat-session-123',
        'user_input': 'What is the weather like today?',
        'ai_output': 'Today is sunny with 22°C...',
        'context': {
            'conversation_turn': 3,
            'filters_applied': {'location': 'London'}
        },
        'response_time_seconds': 2.5,
        'confidence_score': 0.95
    })
    ```
    
    ## 📊 **Analytics & Monitoring**
    
    **Cross-Service Analytics:**
    - Compare satisfaction rates across different AI services
    - Identify which services need improvement
    - Track performance trends over time
    - Monitor user experience across the AI ecosystem
    
    **Service-Specific Insights:**
    - Context-aware analytics based on service type
    - Performance metrics tailored to each AI service
    - Custom reporting for different stakeholder needs
    - Improvement recommendations based on feedback patterns
    
    ## 🏗️ **Service Registration**
    
    **Automatic Service Discovery:**
    - New AI services are automatically registered when first encountered
    - Service metadata is stored for analytics and monitoring
    - Context fields are tracked for service-specific insights
    
    **Manual Service Registration:**
    Services can also be explicitly registered with detailed metadata for
    enhanced analytics and monitoring capabilities.
    
    ## 📈 **Future Enhancements**
    
    - **Database Migration**: Moving from S3 to DynamoDB for better querying
    - **Real-time Dashboards**: Live monitoring of AI service performance
    - **Machine Learning Insights**: Predictive analytics on feedback patterns
    - **API Integrations**: Webhooks and real-time notifications
    - **Advanced Filtering**: Complex queries across multiple dimensions
    
    ## 🔒 **Security & Privacy**
    
    - **Secure Storage**: All feedback encrypted and stored in AWS S3
    - **Access Control**: IAM-based access control for sensitive operations
    - **Data Privacy**: Configurable data retention and anonymization
    - **Audit Trails**: Complete tracking of all feedback operations
    
    ## 📝 **Data Structure**
    
    **Comprehensive Feedback Records:**
    Each feedback entry captures:
    - Core feedback (type, comments, ratings)
    - Service information (name)
    - User context (ID, session, platform)
    - AI interaction data (input, output, performance)
    - Service-specific context (flexible metadata)
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
            "name": "Feedback",
            "description": "Universal feedback collection and management for AI services",
        },
        {
            "name": "Analytics",
            "description": "Cross-service analytics and performance monitoring",
        },
        {
            "name": "Services",
            "description": "AI service registration and discovery",
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
        "service": "AI Services Feedback API",
        "version": "1.0.0",
        "description": "Feedback collection system for AI services",
        "purpose": "Collect, store, and analyze user feedback on AI-generated responses across multiple AI services",
        
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        
        "core_endpoints": {
            "POST /api/feedback": "Submit feedback for any AI service",
            "GET /api/feedback/summary": "Get cross-service analytics summary",
            "POST /api/feedback/search": "Advanced feedback search and filtering",
            "GET /api/feedback/services": "Get registered AI services information",
            "GET /api/feedback/service/{service_name}": "Get service-specific feedback"
        },
        
        "supported_ai_services": {
            "chatbot": {
                "description": "Conversational AI interactions",
                "context_fields": ["filters_applied"],
                "metrics": ["response_time", "user_satisfaction", "context_retention"]
            },
        },
        
        "feedback_capabilities": {
            "feedback_types": ["positive", "negative"],
            "comment_support": "Optional detailed feedback with 5000 character limit",
            "context_flexibility": "Service-specific metadata and context",
            "performance_tracking": "Response time, confidence scores, model information",
            "user_tracking": "Session-based and user-based feedback correlation"
        },
        
        "analytics_features": {
            "cross_service_comparison": "Compare satisfaction across AI services",
            "service_specific_insights": "Detailed analytics per AI service",
            "time_based_trends": "Track performance and satisfaction over time",
            "user_experience_monitoring": "Session and user journey analytics",
            "improvement_identification": "Identify areas needing enhancement"
        },
        
        "integration_guide": {
            "step_1": "Choose your AI service name (e.g., 'my-ai-service')",
            "step_2": "Structure your feedback data according to FeedbackRequest model",
            "step_3": "Include service-specific context in the 'context' field",
            "step_4": "POST to /api/feedback endpoint",
            "step_5": "Monitor your service performance via analytics endpoints"
        },
        
        "storage_architecture": {
            "current": "AWS S3 with organized folder structure",
            "future": "DynamoDB for enhanced querying capabilities",
            "backup": "Multi-region replication for data safety",
            "retention": "Configurable data retention policies"
        },
        
        "technology_stack": {
            "api_framework": "FastAPI with Pydantic validation",
            "storage": "AWS S3 (current), DynamoDB (planned)",
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
    description="Check the health status of the AI Services Feedback API",
    response_description="Service health status, capabilities, and system information"
)
async def health():
    """Health check endpoint with detailed service status."""
    try:
        from app.utils.feedback.feedback_util import ai_feedback_service
        
        # Get service statistics
        registered_services = ai_feedback_service.get_registered_services()
        
        return {
            "status": "healthy",
            "service": "AI Services Feedback API",
            "version": "1.0.0",
            "timestamp": "2025-01-21T12:00:00Z",
            
            "capabilities": {
                "feedback_collection": "operational",
                "multi_service_support": "active",
                "analytics": "available",
                "search": "operational",
                "storage": "aws_s3_active",
                "service_registration": "automatic"
            },
            
            "registered_services": {
                "count": len(registered_services),
                "services": list(registered_services.keys()),
                "auto_registration": "enabled"
            },
            
            "system_info": {
                "feedback_storage": "AWS S3",
                "future_storage": "DynamoDB (planned)",
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
            "service": "AI Services Feedback API",
            "error": str(e),
            "timestamp": "2025-01-21T12:00:00Z"
        }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception in AI Feedback Service: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "service": "AI Services Feedback API",
            "details": "An unexpected error occurred while processing your request.",
            "support": {
                "documentation": "/docs",
                "health_check": "/health"
            }
        }
    )