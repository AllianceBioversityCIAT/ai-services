#!/usr/bin/env python
"""
AR Generator Data Update Cronjob

This cronjob is responsible for updating the information used by the AR generator module.
It sends a POST request to the annual report generation endpoint to trigger the refresh
of data that feeds into the AR generation process. This ensures the AR generator module
always works with the most current and up-to-date information.

The script is designed to run as a weekly cronjob to maintain data freshness without
overloading the system with frequent updates.

Usage:
    python update_ar_data.py
"""

import json
import sys
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


ENDPOINT_URL = "https://ia.prms.cgiar.org/api/generate-annual"
REQUEST_PAYLOAD = {
    "indicator": "IPI 1.3",
    "year": 2025,
    "insert_data": "True"
}
TIMEOUT_SECONDS = 1200  # 20 minutes timeout - allows for data update processing time


def make_annual_report_request():
    """
    Makes a POST request to update the data used by the AR generator module
    
    This function triggers the data refresh process that ensures the AR generator
    has access to the most current information for generating annual reports.
    
    Returns:
        bool: True if the data update request was successful, False otherwise
    """
    try:
        logger.info("Starting AR generator data update process")
        logger.info(f"Endpoint: {ENDPOINT_URL}")
        logger.info(f"Payload: {json.dumps(REQUEST_PAYLOAD, indent=2)}")

        response = requests.post(
            ENDPOINT_URL,
            json=REQUEST_PAYLOAD,
            timeout=TIMEOUT_SECONDS,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'AR-Generator-Service-Cronjob/1.0'
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
            app_name="AR Generator Service",
            color="#36a64f",
            title="AR Generator Data Update Completed",
            message=f"Successfully updated data for AR generator module",
            priority="Low",
            time_taken=None
        )
    else:
        await notification_service.send_slack_notification(
            emoji="⚠️",
            app_name="AR Generator Service",
            color="#FF0000",
            title="Error in AR Generator Data Update",
            message=f"Error updating data for AR generator module: {error_msg}",
            priority="High",
            time_taken=None
        )


def main():
    """Main function to execute the AR generator data update cronjob"""
    try:
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting AR generator data update cronjob")
        logger.info(f"Execution time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        success = make_annual_report_request()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if success:
            try:
                asyncio.run(send_notification(success))
            except Exception as e:
                logger.error(f"❌ Error sending notification: {str(e)}")

            logger.info("AR generator data update completed successfully")
            logger.info(f"Total execution time: {duration.total_seconds():.2f} seconds")
            return 0
        
        else:
            try:
                asyncio.run(send_notification(success, error_msg="Data update request failed"))
            except Exception as e:
                logger.error(f"❌ Error sending notification: {str(e)}")
            
            logger.error("AR generator data update failed")
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