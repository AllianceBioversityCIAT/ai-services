#!/usr/bin/env python
"""
Chatbot Data Update Cronjob

This cronjob is responsible for updating the information used by the chatbot module.
It sends a POST request to the chatbot endpoint to trigger the refresh
of data that feeds into the chatbot process. This ensures the chatbot module
always works with the most current and up-to-date information.

The script is designed to run as a weekly cronjob to maintain data freshness without
overloading the system with frequent updates.

Usage:
    python update_chatbot_data.py
"""

import sys
import time
import asyncio
import requests
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(ROOT))

from app.utils.logger.logger_util import get_logger
from app.utils.notification.notification_service import NotificationService

logger = get_logger()
notification_service = NotificationService()


ENDPOINT_URL = "https://ia.prms.cgiar.org/api/update-chatbot-data"
TIMEOUT_SECONDS = 3600  # 60 minutes timeout - allows for data update processing time
MAX_RETRIES = 3
RETRY_DELAY = 60


def make_chatbot_data_update_request():
    """
    Makes a POST request to update the data used by the Chatbot module

    This function triggers the data refresh process that ensures the Chatbot
    has access to the most current information for generating responses.
    Includes retry logic for handling temporary server issues.

    Returns:
        bool: True if the data update request was successful, False otherwise
    """    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempt {attempt}/{MAX_RETRIES}: Starting Chatbot data update process")
            logger.info(f"Endpoint: {ENDPOINT_URL}")
            logger.info(f"Timeout: {TIMEOUT_SECONDS} seconds")

            response = requests.post(
                ENDPOINT_URL,
                timeout=TIMEOUT_SECONDS,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Chatbot-Service-Cronjob/1.0',
                    'Connection': 'close'
                }
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Request successful. Status code: {response.status_code}")
                logger.info(f"Response: {response.text[:500]}...")
                return True
            elif response.status_code in [502, 503, 504]:
                logger.warning(f"⚠️ Server error {response.status_code} on attempt {attempt}")
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    logger.error(f"❌ Max retries reached. Final error: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
                    return False
            else:
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Request timed out after {TIMEOUT_SECONDS} seconds (attempt {attempt})")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                logger.error(f"❌ Max retries reached. Request timed out")
                return False
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Failed to connect to {ENDPOINT_URL} (attempt {attempt})")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                logger.error(f"❌ Max retries reached. Connection failed")
                return False
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP error occurred: {e}")
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed with exception: {e}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error occurred: {e}")
            return False
    
    return False
    

async def send_notification(success, error_msg=None):
    """Send notification with better error handling"""
    try:
        if success:
            await notification_service.send_slack_notification(
                emoji="🔄",
                app_name="Chatbot Service",
                color="#36a64f",
                title="Chatbot Data Update Completed",
                message=f"Successfully updated data for Chatbot module",
                priority="Low",
                time_taken=None
            )
        else:
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


def main():
    """Main function to execute the Chatbot data update cronjob"""
    try:
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting Chatbot data update cronjob")
        logger.info(f"Execution time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        success = make_chatbot_data_update_request()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if success:
            try:
                asyncio.run(send_notification(success))
            except Exception as e:
                logger.warning(f"⚠️ Notification failed but cronjob succeeded: {e}")

            logger.info("✅ Chatbot data update completed successfully")
            logger.info(f"Total execution time: {duration.total_seconds():.2f} seconds")
            return 0
        
        else:
            try:
                asyncio.run(send_notification(success, error_msg="Data update request failed"))
            except Exception as e:
                logger.warning(f"⚠️ Notification failed: {e}")

            logger.error("❌ Chatbot data update failed")
            logger.error(f"Total execution time: {duration.total_seconds():.2f} seconds")
            return 1
            
    except Exception as e:
        try:
            asyncio.run(send_notification(False, error_msg=str(e)))
        except Exception as ne:
            logger.warning(f"⚠️ Both cronjob and notification failed. Notification error: {ne}")
        
        logger.error(f"❌ Cronjob execution failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())