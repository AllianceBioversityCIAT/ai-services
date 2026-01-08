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
TIMEOUT_SECONDS = 360  # 6 minutes - longer than proxy timeout to receive the 502 response
MAX_RETRIES = 2  # Reduced retries since we only need to confirm request acceptance
RETRY_DELAY = 30  # Delay between retries
MIN_REQUEST_TIME = 240  # 4 minutes - if request lasts this long, server is processing in background


def make_chatbot_data_update_request():
    """
    Makes a POST request to update the data used by the Chatbot module

    This function triggers the data refresh process that ensures the Chatbot
    has access to the most current information for generating responses.
    
    Note: This is a "fire-and-forget" request. The server processes the data update
    in the background, which may take longer than the proxy timeout. A 502 error or
    timeout after the server accepts the request is considered successful, as the
    background job continues running on the server.

    Returns:
        bool: True if the data update request was accepted, False otherwise
    """    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request_start = time.time()
            logger.info(f"Attempt {attempt}/{MAX_RETRIES}: Starting Chatbot data update process")
            logger.info(f"Endpoint: {ENDPOINT_URL}")
            logger.info(f"Timeout: {TIMEOUT_SECONDS} seconds (fire-and-forget mode)")

            response = requests.post(
                ENDPOINT_URL,
                timeout=TIMEOUT_SECONDS,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Chatbot-Service-Cronjob/1.0',
                    'Connection': 'close'
                }
            )
            
            request_duration = time.time() - request_start
            
            if response.status_code == 200:
                logger.info(f"✅ Request successful. Status code: {response.status_code}")
                logger.info(f"Response: {response.text[:500]}...")
                return True
            elif response.status_code in [502, 504]:
                # Check if it's a proxy timeout (background job running) or real error
                response_text = response.text.lower()
                is_proxy_timeout = (
                    "proxy error" in response_text or 
                    "error reading from remote server" in response_text
                )
                
                if request_duration >= MIN_REQUEST_TIME and is_proxy_timeout:
                    logger.info(f"ℹ️ Received proxy {response.status_code} after {request_duration:.1f}s")
                    logger.info(f"✅ Request accepted - background job is processing on server")
                    logger.info(f"Note: Proxy timeout is expected for long-running data updates")
                    return True
                else:
                    # Could be real server error or quick failure
                    logger.warning(f"⚠️ Server error {response.status_code} on attempt {attempt}")
                    logger.warning(f"Request duration: {request_duration:.1f}s | Is proxy timeout: {is_proxy_timeout}")
                    if not is_proxy_timeout:
                        logger.warning(f"Response indicates potential server issue: {response.text[:200]}")
                    if attempt < MAX_RETRIES:
                        logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        logger.error(f"❌ Max retries reached. Server may be unavailable")
                        logger.error(f"Final response: {response.text[:500]}")
                        return False
            elif response.status_code == 503:
                logger.warning(f"⚠️ Service unavailable (503) on attempt {attempt}")
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    logger.error(f"❌ Max retries reached. Service unavailable")
                    return False
            else:
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            request_duration = time.time() - request_start
            # Timeout after server accepted request = background job is running
            if request_duration >= MIN_REQUEST_TIME:
                logger.info(f"ℹ️ Request timed out after {request_duration:.1f}s")
                logger.info(f"✅ Request accepted - background job is processing on server")
                logger.info(f"Note: Timeout is expected for long-running data updates")
                return True
            else:
                logger.warning(f"⚠️ Quick timeout on attempt {attempt} (may indicate connection issue)")
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    logger.error(f"❌ Max retries reached. Unable to connect to server")
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