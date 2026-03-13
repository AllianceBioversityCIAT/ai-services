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


load_dotenv(override=False)

logger = get_logger()

mangum_handler = Mangum(app, lifespan="off")


def is_eventbridge_job(event: Dict[str, Any]) -> bool:
    """
    Check if the event is from EventBridge Scheduler (a scheduled job).
    
    EventBridge Scheduler sends events with a simple JSON structure like:
    {"job": "update_ar_data"}
    
    Function URL and API Gateway events have different structures with keys like:
    - "requestContext", "headers", "body", "rawPath", "rawQueryString", etc.
    
    Args:
        event: Lambda event dictionary
        
    Returns:
        True if this looks like an EventBridge job, False otherwise
    """
    if not isinstance(event, dict):
        return False
    
    if "requestContext" in event:
        return False
    
    function_url_keys = {"rawPath", "rawQueryString", "headers", "requestContext", "body", "isBase64Encoded"}
    if any(key in event for key in function_url_keys):
        return False
    
    api_gateway_keys = {"httpMethod", "path", "headers", "requestContext", "body", "pathParameters", "queryStringParameters"}
    if any(key in event for key in api_gateway_keys):
        return False
    
    if "job" in event and isinstance(event.get("job"), str):
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
        
        result = await execute_scheduled_job(job_name)
        
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
    - HTTP/Function URL requests → Mangum (FastAPI)
    - EventBridge Scheduler jobs → Direct job execution
    
    Args:
        event: Lambda event (can be Function URL or EventBridge)
        context: Lambda context
        
    Returns:
        Response appropriate for the event type
    """
    if is_eventbridge_job(event):
        logger.info("🔍 Detected EventBridge Scheduler job event")
        try:
            return asyncio.run(handle_scheduled_job(event, context))
        except Exception as e:
            logger.error(f"❌ Unexpected error in handler: {str(e)}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "status": "error",
                    "message": f"Handler error: {str(e)}"
                })
            }
    else:
        try:
            logger.info(f"🔍 Processing HTTP/Function URL request")
            logger.debug(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
            
            response = mangum_handler(event, context)
            
            if isinstance(response, dict):
                logger.info(f"✅ Mangum returned response with keys: {list(response.keys())}")
                logger.debug(f"Response statusCode: {response.get('statusCode', 'N/A')}")
                if 'body' in response:
                    body_preview = str(response['body'])[:200] if response['body'] else 'Empty'
                    logger.debug(f"Response body preview: {body_preview}...")
            else:
                logger.warning(f"⚠️ Mangum returned non-dict response: {type(response)}")
            
            return response
        except Exception as e:
            logger.error(f"❌ Error in Mangum handler: {str(e)}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "status": "error",
                    "message": f"Internal server error: {str(e)}"
                })
            }