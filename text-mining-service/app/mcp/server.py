from mcp.server.fastmcp import FastMCP
import boto3
from app.middleware.auth_middleware import AuthMiddleware
from app.utils.notification.notification_service import NotificationService
from typing import Any
from dotenv import load_dotenv
from app.llm.mining import process_document as process_with_llm
from app.utils.logger.logger_util import get_logger

load_dotenv()
logger = get_logger()

auth_middleware = AuthMiddleware()
notification_service = NotificationService()

mcp = FastMCP("DocumentProcessor")

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")


async def authenticate(key: str, bucket: str, token: str):
    try:
        payload = {
            "token": token,
            "key": key,
            "bucket": bucket
        }
        return await auth_middleware.authenticate(payload)
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return None


@mcp.tool()
async def process_document(bucket: str, key: str, token: Any) -> dict:
    logger.info("✅ process_document invoked via MCP")
    
    try:
        is_authenticated = await authenticate(key, bucket, token)
        print(f"Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("Authentication failed")

        logger.info(f"Processing document: {key} from bucket: {bucket}")

        result = process_with_llm(
            bucket_name=bucket, file_key=key)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI-MCP Mining Service",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\nBucket: *{bucket}*",
            time_taken=f"Time taken: *{result['time_taken']}* seconds",
            priority="Low"
        )

        return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="AI-MCP Mining Service",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\nError: *{str(e)}*",
            time_taken="Time taken: *N/A*",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}

if __name__ == "__main__":
    mcp.run()
