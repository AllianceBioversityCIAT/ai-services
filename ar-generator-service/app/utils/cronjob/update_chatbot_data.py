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

import json
import sys
import asyncio
import requests
from datetime import datetime
from app.utils.logger.logger_util import get_logger
from app.utils.notification.notification_service import NotificationService

logger = get_logger()
notification_service = NotificationService()


ENDPOINT_URL = "http://localhost:8000/api/chat"
REQUEST_PAYLOAD = {
    "user_input": "Update the data used by the chatbot",
    "session_id": "Not applicable",
    "memory_id": "Not applicable",
    "insert_data": "True"
}
TIMEOUT_SECONDS = 3600  # 60 minutes timeout - allows for data update processing time


def make_chatbot_data_update_request():
    """
    Makes a POST request to update the data used by the Chatbot module

    This function triggers the data refresh process that ensures the Chatbot
    has access to the most current information for generating responses.

    Returns:
        bool: True if the data update request was successful, False otherwise
    """
    try:
        logger.info("Starting Chatbot data update process")
        logger.info(f"Endpoint: {ENDPOINT_URL}")
        logger.info(f"Payload: {json.dumps(REQUEST_PAYLOAD, indent=2)}")

        response = requests.post(
            ENDPOINT_URL,
            json=REQUEST_PAYLOAD,
            timeout=TIMEOUT_SECONDS,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Chatbot-Service-Cronjob/1.0'
            }
        )
        
        response.raise_for_status()
        
        logger.info(f"Request successful. Status code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        return True
        
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {TIMEOUT_SECONDS} seconds")
        return False
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to {ENDPOINT_URL}")
        return False
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        logger.error(f"Response status code: {response.status_code}")
        logger.error(f"Response content: {response.text}")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed with exception: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        return False
    

async def send_notification(success, error_msg=None):
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
                logger.error(f"❌ Error sending notification: {str(e)}")

            logger.info("Chatbot data update completed successfully")
            logger.info(f"Total execution time: {duration.total_seconds():.2f} seconds")
            return 0
        
        else:
            try:
                asyncio.run(send_notification(success, error_msg="Data update request failed"))
            except Exception as e:
                logger.error(f"❌ Error sending notification: {str(e)}")

            logger.error("Chatbot data update failed")
            logger.error(f"Total execution time: {duration.total_seconds():.2f} seconds")
            return 1
            
    except Exception as e:
        try:
            asyncio.run(send_notification(False, error_msg=str(e)))
        except Exception as ne:
            logger.error(f"❌ Error sending notification: {str(ne)}")
        
        logger.error(f"Cronjob execution failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())