import sys
import json
import boto3
import logging
from dotenv import load_dotenv
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from app.utils.logger.logger_util import get_logger
from app.utils.notification.notification_service import NotificationService
from app.text_mining.star_mining.mining import process_document as process_with_llm
from app.text_mining.prms_mining import process_document_prms as process_with_llm_prms
from app.middleware.star_auth_middleware import AuthMiddleware as StarAuthMiddleware
from app.text_mining.bulk_upload.upload_capdev import process_document_capdev as process_bulk_capdev
from app.text_mining.aiccra_mining.aiccra_mining import process_document_aiccra as process_with_llm_aiccra

load_dotenv()
logger = get_logger()

for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream') and handler.stream == sys.stdout:
        logger.removeHandler(handler)

star_auth_middleware = StarAuthMiddleware()
notification_service = NotificationService()

mcp = FastMCP("DocumentProcessor")

s3_client = boto3.client("s3")
bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")


async def authenticate_star(key: str, bucket: str, token: str, environmentUrl: str, require_roles: bool = False):
    try:
        payload = {
            "token": token,
            "key": key,
            "bucket": bucket,
            "environmentUrl": environmentUrl
        }
        return await star_auth_middleware.authenticate(payload, require_roles=require_roles)
    except Exception as e:
        logger.error(f"Auth error (STAR): {str(e)}")
        return None


@mcp.tool()
async def process_document(bucket: str, key: str, token: Any, environmentUrl: str, user_id: str = None) -> dict:
    logger.info("✅ process_document invoked via MCP")

    try:
        is_authenticated = await authenticate_star(key, bucket, token, environmentUrl)
        logger.info(f"Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("Authentication failed")

        logger.info(f"Processing document: {key} from bucket: {bucket}")
        logger.info(f"👤 User ID for tracking: {user_id}")

        result = process_with_llm(
            bucket_name=bucket, file_key=key, user_id=user_id)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI Text Mining Service (STAR)",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\n*Bucket:* {bucket}\n*User:* {user_id or 'N/A'}",
            time_taken=f"*Time taken:* {result['time_taken']} seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            response = {
                "json_content": result["json_content"],
                "interaction_id": result["interaction_id"]
            }

            return response
        else:
            return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="AI Text Mining Service (STAR)",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\n*Error:* {str(e)}\n*User:* {user_id or 'N/A'}",
            time_taken="*Time taken:* N/A",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}


@mcp.tool()
async def process_document_prms(
    bucket: Optional[str] = None,
    keys: Optional[list[str]] = None,
    text: Optional[str] = None,
    audio_keys: Optional[list[str]] = None,
    user_id: Optional[str] = None,
) -> dict:
    logger.info("✅ process_document_prms invoked via MCP")

    try:
        logger.info(
            "Processing PRMS sources keys=%s audio_keys=%s text=%s bucket=%s user=%s",
            len(keys or []),
            len(audio_keys or []),
            bool((text or "").strip()),
            bucket,
            user_id or "N/A",
        )

        result = process_with_llm_prms(
            bucket_name=bucket,
            keys=keys,
            text=text,
            audio_keys=audio_keys,
            user_id=user_id,
        )

        source_counts = result.get("source_counts") or {}
        results_count = len((result.get("json_content") or {}).get("results") or [])
        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI Text Mining Service (PRMS)",
            color="#36a64f",
            title="PRMS Sources Processed",
            message=(
                f"Successfully processed PRMS sources\n"
                f"*Sources:* docs={source_counts.get('document', 0)} "
                f"audio={source_counts.get('audio', 0)} "
                f"free_text={source_counts.get('free_text', 0)}\n"
                f"*Results:* {results_count}\n"
                f"*User:* {user_id or 'N/A'}"
            ),
            time_taken=f"*Time taken:* {result['time_taken']} seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            return {
                "json_content": result["json_content"],
                "interaction_id": result["interaction_id"]
            }
        return result["json_content"]

    except Exception as e:
        failure_stage = getattr(e, "category", None) or "unknown"
        logger.error("Unexpected error in PRMS processing stage=%s: %s", failure_stage, str(e))
        try:
            await notification_service.send_slack_notification(
                emoji=":ai: :pick: :alert:",
                app_name="AI Text Mining Service (PRMS)",
                color="#FF0000",
                title="PRMS Document Processing Failed",
                message=(
                    f"Error processing PRMS sources\n"
                    f"*Stage:* {failure_stage}\n"
                    f"*Error:* {str(e)}\n"
                    f"*Sources:* docs={len(keys or [])} audio={len(audio_keys or [])} "
                    f"free_text={1 if (text or '').strip() else 0}\n"
                    f"*User:* {user_id or 'N/A'}"
                ),
                time_taken="*Time taken:* N/A",
                priority="High"
            )
        except Exception as slack_exc:
            logger.error("Slack failure notification failed: %s", slack_exc)

        error_payload = {
            "status": "error",
            "error": str(e),
            "project": "PRMS",
            "stage": failure_stage,
            "http_status": getattr(e, "http_status", 500),
        }
        if keys:
            error_payload["keys"] = keys[:5]
        return error_payload


@mcp.tool()
async def process_document_capdev(bucket: str, key: str, token: Any, environmentUrl: str, skip_ids: list = None, user_id: str = None, user_name: str = None) -> dict:
    logger.info("✅ process_document_capdev invoked via MCP")

    try:
        is_authenticated = await authenticate_star(key, bucket, token, environmentUrl, require_roles=True)
        logger.info(f"Authenticated: {is_authenticated}")
        if not is_authenticated:
            raise ValueError("Authentication failed")

        logger.info(f"Processing document: {key} from bucket: {bucket}")
        logger.info(f"👤 User ID for tracking: {user_id} | Name: {user_name}")

        result = process_bulk_capdev(
            bucket_name=bucket, file_key=key, skip_ids=skip_ids or [], user_id=user_id, user_name=user_name)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="Bulk upload via Mining Service (STAR)",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\n*Bucket:* {bucket}\n*User:* {user_name or user_id or 'N/A'}",
            time_taken=f"*Time taken:* {result['time_taken']} seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            parsed = json.loads(result["json_content"])
            parsed["interaction_id"] = result["interaction_id"]
            return parsed
        else:
            return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="Bulk upload via Mining Service (STAR)",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\n*Error:* {str(e)}\n*User:* {user_name or user_id or 'N/A'}",
            time_taken="*Time taken:* N/A",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}


@mcp.tool()
async def process_document_aiccra(bucket: str, key: str, token: Any, environmentUrl: Any, user_id: str = None, prompt: str = None) -> dict:
    logger.info("✅ process_document_aiccra invoked via MCP")

    try:
        logger.info(f"Processing document: {key} from bucket: {bucket}")
        logger.info(f"👤 User ID for tracking: {user_id}")
        if prompt:
            logger.info(f"🎯 Using custom prompt: {prompt[:100]}..." if len(prompt) > 100 else f"🎯 Using custom prompt: {prompt}")
        else:
            logger.info("📝 Using default AICCRA prompt")

        result = process_with_llm_aiccra(
            bucket_name=bucket, file_key=key, user_id=user_id, prompt=prompt)

        await notification_service.send_slack_notification(
            emoji=":ai: :pick:",
            app_name="AI-MCP Mining Service (AICCRA)",
            color="#36a64f",
            title="Document Processed",
            message=f"Successfully processed document: *{key}*\n*Bucket:* {bucket}\n*User:* {user_id or 'N/A'}",
            time_taken=f"*Time taken:* {result['time_taken']} seconds",
            priority="Low"
        )

        if "interaction_id" in result:
            response = {
                "json_content": result["json_content"],
                "interaction_id": result["interaction_id"]
            }

            return response
        else:
            return result["json_content"]

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await notification_service.send_slack_notification(
            emoji=":ai: :pick: :alert:",
            app_name="AI Text Mining Service (AICCRA)",
            color="#FF0000",
            title="Document Processing Failed",
            message=f"Error processing document: *{key}*\n*Error:* {str(e)}\n*User:* {user_id or 'N/A'}",
            time_taken="*Time taken:* N/A",
            priority="High"
        )
        return {"status": "error", "key": key, "error": str(e)}


if __name__ == "__main__":
    mcp.run()
