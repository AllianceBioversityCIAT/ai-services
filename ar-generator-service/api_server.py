"""
AWS Lambda handler for AICCRA Report Generator Service.

This module provides the Lambda handler using Mangum to wrap the FastAPI application.
For local development with uvicorn, use main.py instead.
"""

from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv

# Load environment variables from .env file if it exists (for local development)
# In Lambda, environment variables are configured in the function settings
load_dotenv(override=False)

# Create Mangum handler for AWS Lambda
handler = Mangum(app, lifespan="off")