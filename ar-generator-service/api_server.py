"""
AWS Lambda handler for AICCRA Report Generator Service.

This module provides the Lambda handler using Mangum to wrap the FastAPI application.
For local development with uvicorn, use main.py instead.
"""

from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")