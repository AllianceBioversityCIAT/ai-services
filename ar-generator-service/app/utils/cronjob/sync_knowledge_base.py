#!/usr/bin/env python
"""
Knowledge Base Synchronization Cronjob

This cronjob is responsible for automatically synchronizing the AWS Bedrock Knowledge Base
after data updates. It triggers the ingestion process to ensure the Knowledge Base reflects
the most current information from the S3 data sources.

The script starts an ingestion job and confirms it was initiated successfully.
AWS Bedrock continues the synchronization process in the background.

Usage:
    python sync_knowledge_base.py
"""

import os
import sys
import boto3
import asyncio
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(ROOT))

from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import KNOWLEDGE_BASE
from app.utils.notification.notification_service import NotificationService

logger = get_logger()
notification_service = NotificationService()


bedrock_agent = boto3.client(
    service_name='bedrock-agent',
    region_name='us-east-1'
)


def get_kb_config():    
    kb_id = KNOWLEDGE_BASE.get("knowledge_base_id")
    ds_id = KNOWLEDGE_BASE.get("data_source_id")
    
    logger.info(f"📋 Knowledge Base ID: {kb_id}")
    logger.info(f"📋 Data Source ID: {ds_id}")
    
    return kb_id, ds_id


def sync_knowledge_base(knowledge_base_id, data_source_id):
    try:
        logger.info(f"🔄 Starting Knowledge Base synchronization: {knowledge_base_id}")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            description="Automatic synchronization after data update"
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"✅ Synchronization job started: {ingestion_job_id}")
        
        return ingestion_job_id
        
    except Exception as e:
        logger.error(f"❌ Error starting synchronization: {e}")
        raise


async def send_notification_async(success, error_msg=None):
    try:
        if success:
            await notification_service.send_slack_notification(
                emoji="🔄",
                app_name="Chatbot Service",
                color="#36a64f",
                title="Knowledge Base Synchronization Completed",
                message=f"Successfully synchronized data for Knowledge Base",
                priority="Low",
                time_taken=None
            )
        else:
            await notification_service.send_slack_notification(
                emoji="⚠️",
                app_name="Chatbot Service",
                color="#FF0000",
                title="Error in Knowledge Base Synchronization",
                message=f"Error synchronizing data for Knowledge Base: {error_msg}",
                priority="High",
                time_taken=None
            )
    except Exception as e:
        logger.error(f"❌ Error sending notification: {e}")


def run_sync_job():
    """
    Executes the complete synchronization process of the Knowledge Base
    
    Returns:
        bool: True if the synchronization was successful, False otherwise
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"🚀 Starting Knowledge Base synchronization cronjob")
    logger.info(f"⏰ Date and time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        kb_id, ds_id = get_kb_config()

        ingestion_job_id = sync_knowledge_base(kb_id, ds_id)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        message = (
            f"✅ Knowledge Base synchronization job started successfully\n\n"
            f"📋 Knowledge Base ID: {kb_id}\n"
            f"📋 Data Source ID: {ds_id}\n"
            f"🆔 Job ID: {ingestion_job_id}\n"
            f"⏱️ Duration: {duration:.2f} seconds\n"
            f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"ℹ️ AWS Bedrock will continue processing in the background."
        )
        logger.info(message)
        
        try:
            asyncio.run(send_notification_async(True, None))
        except Exception as e:
            logger.error(f"❌ Error sending success notification: {e}")
        
        logger.info("="* 80)
        logger.info("✅ Cronjob completed successfully")
        logger.info("="* 80)
        return True
            
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        error_message = f"Critical error in synchronization cronjob: {str(e)}"
        
        logger.error("=" * 80)
        logger.error(f"❌ {error_message}")
        logger.error(f"⏱️ Duration: {duration:.2f} seconds")
        logger.error(f"⏰ Failed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.error("=" * 80)

        try:
            asyncio.run(send_notification_async(False, error_message))
        except Exception as notification_error:
            logger.error(f"❌ Error sending critical error notification: {notification_error}")
        
        return False


if __name__ == "__main__":
    try:
        success = run_sync_job()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Execution interrupted by the user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)