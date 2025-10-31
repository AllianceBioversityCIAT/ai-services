"""FastAPI application for PRMS QA Service."""

from fastapi import FastAPI
from app.api.routes import router
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.utils.logger.logger_util import get_logger

logger = get_logger()

app = FastAPI(
    title="PRMS QA API",
    description="""
    🔍 PRMS QA Service

    A REST API service that processes CGIAR result metadata for PRMS using language models (LLM) to improve titles, descriptions, and short names for better clarity and compliance with standards.

    Use cases:
    - Enhance result metadata for non-specialist audiences
    - Generate QA improvements based on result type and level
    - Track interactions for analytics

    🚀 Key Features

    - 🔍 LLM-powered QA for PRMS documents
    - 🤖 Integration with AWS Bedrock Claude
    - 📊 Optional interaction tracking via external service
    - 📦 Simple API for PRMS metadata processing

    🏗️ Tech Stack

    - FastAPI
    - AWS Bedrock (Claude)
    - Python 3.13
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
            "name": "PRMS QA",
            "description": "Operations for processing PRMS result metadata with LLM QA"
        },
        {
            "name": "Health",
            "description": "Service health and status endpoints"
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
    description="Get basic information about the PRMS QA API service",
    response_description="Metadata and available endpoints"
)
async def root():
    """Root endpoint providing comprehensive API information."""
    return {
        "service": "PRMS QA API",
        "version": "1.0.0",
        "description": "REST API for PRMS result metadata QA using LLMs",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "POST /api/prms-qa": "Process PRMS result metadata for QA improvements",
            "GET /health": "Health check endpoint"
        },
        "technology_stack": ["FastAPI", "AWS Bedrock", "Python 3.13"]
    }

@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the PRMS QA API service",
    response_description="Service status and metadata"
)
async def health():
    try:
        return {
            "status": "healthy",
            "service": "PRMS QA API",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "PRMS QA API",
            "error": str(e)
        }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "details": "An unexpected error occurred. Please check the logs or contact support."
        }
    )