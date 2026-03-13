"""FastAPI application for AICCRA Report Generator Service."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.utils.logger.logger_util import get_logger

logger = get_logger()

# Create FastAPI application
app = FastAPI(
    title="AICCRA Report Generator API",
    description="""
    🌟 AICCRA Report Generator Service
    
    An AI-powered REST API service for generating comprehensive reports for AICCRA
    (Accelerating Impacts of CGIAR Climate Research for Africa). 
    
    This service combines automated report generation capabilities with vector databases 
    and Large Language Models to produce high-quality, data-driven narratives.
    
    🎯 Report Types Available
    
    Mid-Year Progress Reports (`/api/generate`)
    - Focus on interim progress assessment and milestone tracking
    - Covers January-June achievements and progress towards annual targets
    - Includes risk assessment and course correction recommendations
    - Ideal for progress monitoring and mid-year strategic reviews
    
    Annual Reports (`/api/generate-annual`)  
    - Comprehensive year-end performance and impact assessment
    - Covers complete January-December achievements and outcomes
    - Includes detailed impact analysis, disaggregated targets, and lessons learned
    - Perfect for donor reporting, annual reviews, and strategic planning
    
    Challenges and Lessons Learned Reports (`/api/generate-challenges`)
    - Cross-cluster analysis of implementation challenges and adaptive strategies
    - Synthesizes insights from all regional and thematic clusters
    - Identifies best practices and strategic recommendations
    - Essential for learning and development, adaptive management
    
    Annual Indicator Summary Tables (`/api/generate-annual-tables`)
    - Consolidated overview tables for all indicators grouped by type
    - Quantitative targets, achievements, and AI-generated brief overviews
    - Perfect for executive dashboards and performance monitoring
    
    🖥️ Web User Interface
    
    Access the intuitive web interface at `/web` for easy report generation without API calls.
    The web UI provides the same functionality as the API endpoints with a user-friendly interface.
    
    🚀 Key Features
    
    - 📊 Automated Report Generation: AI-generated Mid-Year Progress and comprehensive Annual Reports
    - 🔍 Vector Search: Integration with Amazon OpenSearch Service for context retrieval
    - 📈 Multi-Indicator Support: Handles both IPI and PDO indicators
    - 💾 Database Integration: SQL Server connectivity for retrieving structured data
    - 🤖 AWS Bedrock Integration: Uses Claude 3.7 Sonnet for report generation
    - 📋 Multiple Report Types: Mid-year progress, annual assessments, challenges analysis, and summary tables
    - 🖥️ Web Interface: User-friendly web UI for non-technical users
    
    📋 Supported Indicators
    
    Intermediate Performance Indicators (IPI)
    - IPI 1.1 - IPI 1.4: Climate information and early warning systems
    - IPI 2.1 - IPI 2.3: Agricultural technologies and practices
    - IPI 3.1 - IPI 3.4: Institutional capacity and partnerships
    
    Project Development Objective (PDO) Indicators  
    - PDO Indicator 1-5: Various project outcome metrics
    
    🏗️ Technology Stack
    
    - AI/ML: AWS Bedrock (Claude 3.7 Sonnet)
    - Vector Database: Amazon OpenSearch Service
    - Traditional Database: SQL Server
    - Cloud Services: AWS S3, AWS Bedrock Knowledge Base
    - Frontend: HTML5, CSS3, JavaScript (ES6+)
    
    🔒 Authentication
    
    This API uses AWS IAM authentication for accessing backend services.
    No API key is required for the HTTP endpoints.
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
            "name": "Reports",
            "description": "Operations related to AICCRA report generation",
        },
        {
            "name": "Health",
            "description": "Service health and status endpoints",
        },
        {
            "name": "UI",
            "description": "Web user interface access and redirects",
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount static files for the web UI
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/web", 
         tags=["UI"],
         summary="Web UI Redirect",
         description="Redirect to the AICCRA Report Generator Web UI",
)
async def serve_ui_alt():
    return FileResponse('web/index.html')


@app.get(
    "/",
    tags=["Health"],
    summary="API Information",
    description="Get basic information about the AICCRA Report Generator API",
    response_description="API metadata and available endpoints"
)
async def root():
    """Root endpoint providing comprehensive API information."""
    return {
        "service": "AICCRA Report Generator API",
        "version": "1.0.0",
        "description": "REST API for AICCRA AI report generator service with AWS Bedrock integration",
        "web_interface": {
            "url": "/web",
            "description": "User-friendly web interface for generating AICCRA reports",
            "features": ["Annual Reports", "Summary Tables", "Challenges Reports", "Download capabilities"]
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "POST /api/generate": "Generate AICCRA Mid-Year Progress Report for specific indicator and year",
            "POST /api/generate-annual": "Generate comprehensive AICCRA Annual Report for specific indicator and year",
            "POST /api/generate-annual-tables": "Generate comprehensive AICCRA Annual Report tables for specific year",
            "POST /api/generate-challenges": "Generate AICCRA Challenges and Lessons Learned Report for specific year",
            "GET /health": "Health check endpoint",
            "GET /web": "Access the AICCRA Report Generator Web UI"
        },
        "supported_indicators": {
            "IPI": ["IPI 1.1", "IPI 1.2", "IPI 1.3", "IPI 1.4", "IPI 2.1", "IPI 2.2", "IPI 2.3", "IPI 3.1", "IPI 3.2", "IPI 3.3", "IPI 3.4"],
            "PDO": ["PDO Indicator 1", "PDO Indicator 2", "PDO Indicator 3", "PDO Indicator 4", "PDO Indicator 5"]
        },
        "supported_years": "2021-2025",
        "technology_stack": ["FastAPI", "AWS Bedrock", "OpenSearch", "SQL Server", "HTML5", "CSS3", "JavaScript"]
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the AICCRA Report Generator API service",
    response_description="Service health status and metadata"
)
async def health():
    """Health check endpoint with detailed service status."""
    try:
        return {
            "status": "healthy",
            "service": "AICCRA Report Generator API",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "AICCRA Report Generator API",
            "error": str(e)
        }


# Global exception handler
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