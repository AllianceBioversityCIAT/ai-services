"""
AWS Lambda handler for AICCRA Report Generator Service.

This module provides a hybrid Lambda handler that supports:
1. HTTP/API Gateway requests via FastAPI + Mangum
2. EventBridge Scheduler jobs via direct function calls

For local development with uvicorn, use main.py instead.
"""

import json
import asyncio
from typing import Any, Dict
from mangum import Mangum
from app.api.main import app
from dotenv import load_dotenv
from app.utils.logger.logger_util import get_logger
from app.utils.scheduled_jobs import execute_scheduled_job

# Load environment variables from .env file if it exists (for local development)
# In Lambda, environment variables are configured in the function settings
load_dotenv(override=False)

logger = get_logger()

# Create Mangum handler for AWS Lambda HTTP requests
mangum_handler = Mangum(app, lifespan="off")


def is_eventbridge_job(event: Dict[str, Any]) -> bool:
    """
    Check if the event is from EventBridge Scheduler (a scheduled job).
    
    EventBridge Scheduler sends events with a simple JSON structure like:
    {"job": "update_ar_data"}
    
    API Gateway events have a different structure with keys like:
    - "httpMethod", "path", "headers", "body", etc.
    
    Args:
        event: Lambda event dictionary
        
    Returns:
        True if this looks like an EventBridge job, False otherwise
    """
    # Check if event is a dict and has the "job" key
    if not isinstance(event, dict):
        return False
    
    # EventBridge Scheduler jobs have a simple structure with "job" key
    if "job" in event and isinstance(event.get("job"), str):
        # Make sure it doesn't look like an HTTP event
        # API Gateway events have these keys
        http_keys = {"httpMethod", "path", "headers", "requestContext", "body", "pathParameters", "queryStringParameters"}
        if not any(key in event for key in http_keys):
            return True
    
    return False


async def handle_scheduled_job(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle a scheduled job event from EventBridge Scheduler.
    
    Args:
        event: Lambda event with job information
        context: Lambda context
        
    Returns:
        Response dictionary with status code and body
    """
    try:
        job_name = event.get("job")
        
        if not job_name:
            logger.error("❌ EventBridge job event missing 'job' field")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "status": "error",
                    "message": "Missing 'job' field in event",
                    "event": event
                })
            }
        
        logger.info(f"📅 Received scheduled job request: {job_name}")
        
        # Execute the job
        result = await execute_scheduled_job(job_name)
        
        # Determine status code based on result
        status_code = 200 if result.get("status") == "success" else 500
        
        logger.info(f"✅ Job '{job_name}' completed with status: {result.get('status')}")
        
        return {
            "statusCode": status_code,
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling scheduled job: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": f"Internal error executing job: {str(e)}",
                "job": event.get("job", "unknown")
            })
        }


def handler(event: Dict[str, Any], context: Any) -> Any:
    """
    Hybrid Lambda handler that routes events to either:
    - HTTP/API Gateway requests → Mangum (FastAPI)
    - EventBridge Scheduler jobs → Direct job execution
    
    Args:
        event: Lambda event (can be API Gateway or EventBridge)
        context: Lambda context
        
    Returns:
        Response appropriate for the event type
    """
    try:
        # Check if this is an EventBridge Scheduler job
        if is_eventbridge_job(event):
            logger.info("🔍 Detected EventBridge Scheduler job event")
            # Run async job handler
            return asyncio.run(handle_scheduled_job(event, context))
        else:
            # This is an HTTP/API Gateway event, use Mangum
            logger.debug("🔍 Detected HTTP/API Gateway event, routing to FastAPI")
            return mangum_handler(event, context)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error in handler: {str(e)}", exc_info=True)
        # Try to return a proper error response
        if is_eventbridge_job(event):
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "status": "error",
                    "message": f"Handler error: {str(e)}"
                })
            }
        else:
            # For HTTP events, let Mangum handle the error
            raise