"""FastAPI application for AI Insights Service."""

import uvicorn
from fastapi import FastAPI
from api.routes import router
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from utils.logger.logger_util import get_logger
from utils.config.config_util import is_lambda_runtime

logger = get_logger()

app = FastAPI(
    title="AI Insights API",
    description="""
    **AI Insights Service**

    A REST API that processes documents stored in Amazon S3 and generates structured insights
    using large language models (LLM) via AWS Bedrock.

    **Use cases:**
    - Generate comprehensive project overviews from up to 3 documents per project
    - Extract key findings, recommendations, and metadata from project reports
    - Support multiple document formats: PDF, DOCX, TXT, XLSX, PPTX
    - Parallel text extraction with Amazon Textract for PDFs and images

    **Tech Stack**
    - FastAPI
    - AWS Bedrock (Claude)
    - Amazon Textract
    - Amazon S3
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
            "name": "Document Overview",
            "description": "Generate structured project overviews from documents stored in an S3 folder"
        },
        {
            "name": "Health",
            "description": "Service health and status endpoints"
        }
    ]
)

# Lambda Function URL handles CORS at the edge; adding it here too duplicates headers
# (e.g. * vs a specific origin) and browsers block the response.
if not is_lambda_runtime():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)


@app.get(
    "/",
    tags=["Health"],
    summary="API Information",
    description="Get basic information about the AI Insights API service",
    response_description="Service metadata and available endpoints"
)
async def root():
    """Root endpoint providing service metadata."""
    return {
        "service": "AI Insights API",
        "version": "1.0.0",
        "description": "REST API for project document analysis and insight generation using LLMs",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "POST /api/document-overview": "Generate a structured overview from 1-3 project documents in an S3 folder",
            "GET /api/document-overview": "Retrieve a cached project overview from response.json in S3",
            "GET /health": "Health check endpoint"
        },
        "technology_stack": ["FastAPI", "AWS Bedrock (Claude)", "Amazon Textract", "Python 3.13"]
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check the health status of the AI Insights API service",
    response_description="Service status"
)
async def health():
    try:
        return {
            "status": "healthy",
            "service": "AI Insights API",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "AI Insights API",
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")