"""
Entry point for AWS Lambda deployment of the AI Feedback Service.

This service provides comprehensive feedback management capabilities
for any AI service that generates user-facing content.
"""

from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv

load_dotenv()

handler = Mangum(app)