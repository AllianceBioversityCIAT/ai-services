"""FastAPI application for AICCRA Chatbot Service."""

from fastapi import FastAPI
from app.api.routes import router
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.utils.logger.logger_util import get_logger

logger = get_logger()

app = FastAPI(
    title="AICCRA Chatbot API",
    description="""
    🤖 AICCRA AI Chatbot Service
    
    An intelligent conversational AI service for exploring AICCRA
    (Accelerating Impacts of CGIAR Climate Research for Africa) data and insights.
    
    This service provides an interactive chatbot interface that can answer questions about
    AICCRA's activities, deliverables, innovations, and performance indicators using
    natural language processing and vector search capabilities.
    
    🚀 Key Features
    
    - 💬 **Conversational Interface**: Natural language interaction with AICCRA data
    - 🧠 **Memory-Enabled**: Remembers conversation context across sessions
    - 🔍 **Smart Filtering**: Apply filters by phase, indicator, and section
    - 📊 **Data-Driven Insights**: Provides insights from real AICCRA reporting data
    - 🎯 **Contextual Responses**: Builds upon previous questions for comprehensive answers
    - 🔗 **Rich Citations**: Includes links to relevant documents and reports
    - 🔄 **Data Refresh**: Option to reload fresh data from the database
    - 📝 **Feedback System**: Collect user feedback for continuous improvement
    
    🔄 Data Management
    
    The service supports two data access modes:
    
    **Standard Mode (insert_data=false)**
    - Uses existing knowledge base data for fast responses (~3-5 seconds)
    - Recommended for most queries and regular usage
    - Data is typically refreshed weekly
    
    **Fresh Data Mode (insert_data=true)**
    - Reloads data directly from SQL Server database (~3-5 minutes)
    - Processes all database views and uploads to knowledge base
    - Use when you need the absolute latest information
    - Recommended after major database updates

    📝 Feedback System
    
    **Continuous Improvement Through User Feedback**
    
    The service includes a feedback system to collect user opinions on AI responses:
    
    - **Positive Feedback (👍)**: When responses are helpful and accurate
    - **Negative Feedback (👎)**: When responses need improvement, with optional detailed comments
    - **Session Tracking**: Links feedback to specific conversations
    - **Metadata Collection**: Captures context like filters used and response characteristics
    - **Secure Storage**: Feedback stored in AWS S3 with unique tracking IDs
    
    **Feedback Features:**
    - Unique tracking IDs for each feedback submission
    - Session and user context preservation
    - Optional detailed comments for negative feedback
    - Automatic metadata capture (timestamps, response length, filters used)
    - Secure S3 storage with organized folder structure
    
    🗣️ What You Can Ask
    
    **Progress & Achievements**
    - "What progress has been made on IPI 1.1 in 2025?"
    - "Show me achievements for PDO Indicator 3"
    - "How are clusters performing this year?"
    
    **Deliverables & Research**
    - "What deliverables were published by the Kenya cluster?"
    - "Show me recent publications on climate information services"
    - "What research outputs are available for Theme 2?"
    
    **Innovations & Technologies**
    - "What innovations were developed for climate-smart agriculture?"
    - "Show me tools created for early warning systems"
    - "What technology readiness levels have been achieved?"
    
    **Outcomes & Impact**
    - "What outcomes have been documented in OICRs?"
    - "Show me impact case reports from Eastern Africa"
    - "What real-world impacts has AICCRA achieved?"
    
    📋 Supported Data Types
    
    **Performance Indicators**
    - **IPI 1.1-1.4**: Climate information and early warning systems
    - **IPI 2.1-2.3**: Agricultural technologies and practices
    - **IPI 3.1-3.4**: Institutional capacity and partnerships
    - **PDO Indicator 1-5**: Project outcome and impact metrics
    
    **Data Sections**
    - **Deliverables**: Research outputs, publications, tools, and datasets
    - **Contributions**: Cluster activities, milestone progress, and narratives
    - **Innovations**: Technology developments, platforms, and practices
    - **OICRs**: Outcome Impact Case Reports documenting real-world impacts
    
    **Reporting Phases**
    - **AWPB**: Annual Work Plan and Budget (planning phase)
    - **Progress**: Mid-year progress reports
    - **AR**: Annual Reports (achievements and outcomes)
    
    🏗️ Technology Stack
    
    - **AI/ML**: AWS Bedrock (Claude 3.7 Sonnet) with Amazon Bedrock Agents
    - **Memory**: Amazon Bedrock Knowledge Base with session management
    - **Vector Search**: Amazon OpenSearch Service for semantic search
    - **Database**: SQL Server for structured data
    - **Cloud Services**: AWS S3, AWS Bedrock Knowledge Base
    - **Feedback Storage**: AWS S3 with organized structure
    
    🔒 Authentication
    
    This API uses AWS IAM authentication for accessing backend services.
    No API key is required for the HTTP endpoints.
    
    ⚠️ **Data Reload Notice**
    
    When using `insert_data=true`, the following process occurs:
    1. Connects to SQL Server and queries all AICCRA views
    2. Processes thousands of records from multiple tables
    3. Uploads data files to S3 bucket
    4. Synchronizes AWS Bedrock Knowledge Base
    5. Completes the chat request with fresh data
    
    This ensures you get the most up-to-date information but takes significantly longer.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "CGIAR MARLO AICCRA",
        "url": "https://aiccra.marlo.cgiar.org/",
        "email": "MARLOSupport@cgiar.org"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Chat",
            "description": "Conversational AI operations for AICCRA data exploration",
        },
        {
            "name": "Feedback", 
            "description": "User feedback collection and analytics for AI response quality",
        },
        {
            "name": "Health",
            "description": "Service health and status endpoints",
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get(
    "/",
    tags=["Health"],
    summary="API Information",
    description="Get basic information about the AICCRA Chatbot API",
    response_description="API metadata and available endpoints"
)
async def root():
    """Root endpoint providing comprehensive API information."""
    return {
        "service": "AICCRA Chatbot API",
        "version": "1.0.0",
        "description": "REST API for AICCRA AI chatbot service with AWS Bedrock Agents integration",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "POST /api/chat": "Send message to AICCRA chatbot",
            "POST /api/feedback": "Submit feedback on AI responses",
            "GET /health": "Health check endpoint"
        },
        "supported_indicators": {
            "IPI": ["IPI 1.1", "IPI 1.2", "IPI 1.3", "IPI 1.4", "IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4"],
            "PDO": ["PDO Indicator 1", "PDO Indicator 2", "PDO Indicator 3", "PDO Indicator 4", "PDO Indicator 5"]
        },
        "supported_years": "2021-2025",
        "data_sections": ["Deliverables", "Contributions", "Innovations", "OICRs"],
        "data_modes": {
            "standard": {
                "insert_data": False,
                "response_time": "3-5 seconds",
                "description": "Uses existing knowledge base data"
            },
            "fresh_data": {
                "insert_data": True,
                "response_time": "3-5 minutes",
                "description": "Reloads data from database before responding"
            }
        },
        "feedback_system": {
            "feedback_types": ["positive", "negative"],
            "features": ["Session tracking", "User identification", "Comment support", "Metadata collection"],
            "storage": "AWS S3",
            "tracking": "Unique feedback IDs for each submission"
        },
        "technology_stack": ["FastAPI", "AWS Bedrock Agents", "Amazon OpenSearch", "SQL Server"],
        "capabilities": [
            "Natural language conversation",
            "Session-based memory", 
            "Context-aware responses",
            "Smart data filtering",
            "Citation and linking",
            "Real-time data refresh"
        ]
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the AICCRA Chatbot API service",
    response_description="Service health status and metadata"
)
async def health():
    """Health check endpoint with detailed service status."""
    try:
        return {
            "status": "healthy",
            "service": "AICCRA Chatbot API",
            "version": "1.0.0",
            "capabilities": {
                "chat": "available",
                "memory": "enabled",
                "filters": "active",
                "vector_search": "operational",
                "data_reload": "available",
                "feedback_system": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "AICCRA Chatbot API",
            "error": str(e)
        }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "details": "An unexpected error occurred. Please check the logs or contact support.",
            "support": "MARLOSupport@cgiar.org"
        }
    )