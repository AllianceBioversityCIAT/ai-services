"""
Scheduled Jobs Execution Module

This module provides functions to execute scheduled jobs that are triggered
by AWS EventBridge Scheduler. These jobs replace the previous EC2 cronjobs
and run directly within the Lambda function.

Supported jobs:
- update_ar_data: Updates AR generator data by running the annual report pipeline with data insertion
- update_chatbot_data: Updates chatbot knowledge base data sources
- sync_knowledge_base: Synchronizes AWS Bedrock Knowledge Base
"""

import boto3
from typing import Dict, Any
from app.llm.vectorize_annual import run_pipeline
from db_conn.sql_connection import load_full_data
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import KNOWLEDGE_BASE, AWS
from app.utils.notification.notification_service import NotificationService

logger = get_logger()
notification_service = NotificationService()


async def execute_update_ar_data() -> Dict[str, Any]:
    """
    Execute the AR data update job.
    
    This job runs the annual report generation pipeline with data insertion
    to refresh the data used by the AR generator module.
    
    Returns:
        Dict with status and message
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting AR data update job")
        logger.info("=" * 80)

        indicator = "IPI 1.3"
        year = 2025
        insert_data = True

        logger.info(
            f"📊 Running pipeline for indicator: {indicator}, "
            f"year: {year}, insert_data: {insert_data}"
        )

        result = run_pipeline(indicator, year, insert_data=insert_data)

        if result is None or (
            isinstance(result, str) and result.startswith("# Report Generation Error")
        ):
            error_msg = "AR data update pipeline failed"
            logger.error(f"❌ {error_msg}")

            try:
                await notification_service.send_slack_notification(
                    emoji="⚠️",
                    app_name="AR Generator Service",
                    color="#FF0000",
                    title="Error in AR Generator Data Update",
                    message=f"Error updating data for AR generator module: {error_msg}",
                    priority="High",
                    time_taken=None
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to send notification: {e}")
            
            return {
                "status": "error",
                "message": error_msg,
                "job": "update_ar_data"
            }
        
        logger.info("✅ AR data update completed successfully")
        
        try:
            await notification_service.send_slack_notification(
                emoji="🔄",
                app_name="AR Generator Service",
                color="#36a64f",
                title="AR Generator Data Update Completed",
                message="Successfully updated data for AR generator module",
                priority="Low",
                time_taken=None
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to send notification: {e}")
        
        return {
            "status": "success",
            "message": "AR data update completed successfully",
            "job": "update_ar_data"
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in AR data update: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        
        try:
            await notification_service.send_slack_notification(
                emoji="⚠️",
                app_name="AR Generator Service",
                color="#FF0000",
                title="Error in AR Generator Data Update",
                message=f"Error updating data for AR generator module: {error_msg}",
                priority="High",
                time_taken=None
            )
        except Exception as notif_error:
            logger.warning(f"⚠️ Failed to send notification: {notif_error}")
        
        return {
            "status": "error",
            "message": error_msg,
            "job": "update_ar_data"
        }


async def execute_update_chatbot_data() -> Dict[str, Any]:
    """
    Execute the chatbot data update job.
    
    This job updates all AICCRA data sources that feed into the chatbot's
    knowledge base by calling load_full_data for each table.
    
    Returns:
        Dict with status and message
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting AICCRA chatbot knowledge base data update")
        logger.info("=" * 80)
        
        tables_to_process = [
            "vw_ai_project_contribution",
            "vw_ai_deliverables",
            "vw_ai_questions",
            "vw_ai_oicrs",
            "vw_ai_innovations"
        ]
        
        processed_tables = []
        files_generated = {}
        
        for table_name in tables_to_process:
            try:
                logger.info(f"🔄 Processing table: {table_name}")
                
                df = load_full_data(table_name)
                
                if not df.empty:
                    processed_tables.append(table_name)
                    files_generated[table_name] = [
                        f"{table_name}.jsonl",
                        f"{table_name}.csv"
                    ]
                    logger.info(f"✅ Successfully processed {table_name} - {len(df)} records")
                else:
                    logger.warning(f"⚠️ No data returned for {table_name}")
                    
            except Exception as table_error:
                logger.error(f"❌ Error processing table {table_name}: {str(table_error)}", exc_info=True)
                continue
        
        if processed_tables:
            logger.info(f"✅ Chatbot data update completed successfully")
            logger.info(f"📊 Processed {len(processed_tables)} tables: {', '.join(processed_tables)}")
            
            try:
                await notification_service.send_slack_notification(
                    emoji="🔄",
                    app_name="Chatbot Service",
                    color="#36a64f",
                    title="Chatbot Data Update Completed",
                    message=f"Successfully updated data for Chatbot module. Processed {len(processed_tables)} tables.",
                    priority="Low",
                    time_taken=None
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to send notification: {e}")
            
            return {
                "status": "success",
                "message": f"Chatbot data update completed. Processed {len(processed_tables)} tables.",
                "job": "update_chatbot_data",
                "tables_processed": processed_tables,
                "files_generated": files_generated
            }
        else:
            error_msg = "No chatbot data tables were successfully processed"
            logger.error(f"❌ {error_msg}")
            
            try:
                await notification_service.send_slack_notification(
                    emoji="⚠️",
                    app_name="Chatbot Service",
                    color="#FF0000",
                    title="Error in Chatbot Data Update",
                    message=f"Error updating data for Chatbot module: {error_msg}",
                    priority="High",
                    time_taken=None
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to send notification: {e}")
            
            return {
                "status": "error",
                "message": error_msg,
                "job": "update_chatbot_data"
            }
            
    except Exception as e:
        error_msg = f"Unexpected error in chatbot data update: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        
        try:
            await notification_service.send_slack_notification(
                emoji="⚠️",
                app_name="Chatbot Service",
                color="#FF0000",
                title="Error in Chatbot Data Update",
                message=f"Error updating data for Chatbot module: {error_msg}",
                priority="High",
                time_taken=None
            )
        except Exception as notif_error:
            logger.warning(f"⚠️ Failed to send notification: {notif_error}")
        
        return {
            "status": "error",
            "message": error_msg,
            "job": "update_chatbot_data"
        }


async def execute_sync_knowledge_base() -> Dict[str, Any]:
    """
    Execute the knowledge base synchronization job.
    
    This job triggers the AWS Bedrock Knowledge Base ingestion process
    to synchronize the knowledge base with the latest data sources.
    
    Returns:
        Dict with status and message
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting Knowledge Base synchronization job")
        logger.info("=" * 80)
        
        kb_id = KNOWLEDGE_BASE.get("knowledge_base_id")
        ds_id = KNOWLEDGE_BASE.get("data_source_id")
        
        if not kb_id or not ds_id:
            error_msg = "Knowledge Base ID or Data Source ID not configured"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "job": "sync_knowledge_base"
            }
        
        logger.info(f"📋 Knowledge Base ID: {kb_id}")
        logger.info(f"📋 Data Source ID: {ds_id}")
        
        try:
            bedrock_agent = boto3.client(
                service_name='bedrock-agent',
                region_name=AWS.get('region', 'us-east-1')
            )
        except Exception:
            bedrock_agent = boto3.client(
                service_name='bedrock-agent',
                aws_access_key_id=AWS.get('aws_access_key'),
                aws_secret_access_key=AWS.get('aws_secret_key'),
                region_name=AWS.get('region', 'us-east-1')
            )
        
        logger.info(f"🔄 Starting Knowledge Base synchronization: {kb_id}")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            description="Automatic synchronization after data update"
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"✅ Synchronization job started: {ingestion_job_id}")
        logger.info(f"ℹ️ AWS Bedrock will continue processing in the background")

        try:
            await notification_service.send_slack_notification(
                emoji="🔄",
                app_name="Chatbot Service",
                color="#36a64f",
                title="Knowledge Base Synchronization Completed",
                message=f"Successfully synchronized data for Knowledge Base.",
                priority="Low",
                time_taken=None
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to send notification: {e}")
        
        return {
            "status": "success",
            "message": f"Knowledge Base synchronization job started successfully",
            "job": "sync_knowledge_base",
            "ingestion_job_id": ingestion_job_id,
            "knowledge_base_id": kb_id,
            "data_source_id": ds_id
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in knowledge base synchronization: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)

        try:
            await notification_service.send_slack_notification(
                emoji="⚠️",
                app_name="Chatbot Service",
                color="#FF0000",
                title="Error in Knowledge Base Synchronization",
                message=f"Error synchronizing data for Knowledge Base: {error_msg}",
                priority="High",
                time_taken=None
            )
        except Exception as notif_error:
            logger.warning(f"⚠️ Failed to send notification: {notif_error}")
        
        return {
            "status": "error",
            "message": error_msg,
            "job": "sync_knowledge_base"
        }


JOB_HANDLERS = {
    "update_ar_data": execute_update_ar_data,
    "update_chatbot_data": execute_update_chatbot_data,
    "sync_knowledge_base": execute_sync_knowledge_base,
}


async def execute_scheduled_job(job_name: str) -> Dict[str, Any]:
    """
    Execute a scheduled job by name.
    
    Args:
        job_name: Name of the job to execute
        
    Returns:
        Dict with status, message, and job information
        
    Raises:
        ValueError: If job_name is not supported
    """
    if job_name not in JOB_HANDLERS:
        supported_jobs = ", ".join(JOB_HANDLERS.keys())
        error_msg = f"Unknown job: {job_name}. Supported jobs: {supported_jobs}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "job": job_name,
            "supported_jobs": list(JOB_HANDLERS.keys())
        }
    
    logger.info(f"📅 Executing scheduled job: {job_name}")
    handler = JOB_HANDLERS[job_name]
    return await handler()