"""FastAPI application for AICCRA Report Generator Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.utils.logger.logger_util import get_logger

logger = get_logger()

# Create FastAPI application
app = FastAPI(
    title="AICCRA Report Generator API",
    description="REST API for AICCRA AI chatbot service with AWS Bedrock integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "service": "AICCRA Report Generator API",
        "version": "1.0.0",
        "description": "REST API for AICCRA AI chatbot service with AWS Bedrock integration",
        "docs": "/docs",
        "endpoints": [
            "POST /api/generate - Generate AICCRA report",
            "POST /api/chat - Chat with AICCRA assistant (alias for /api/generate)"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AICCRA Report Generator API"}


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
            "details": "An unexpected error occurred"
        }
    )