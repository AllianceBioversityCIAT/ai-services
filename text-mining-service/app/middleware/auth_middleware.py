import requests
import os
from typing import Dict, Any
from app.utils.logger.logger_util import get_logger
from app.utils.notification.notification_service import NotificationService
from app.utils.clarisa.clarisa_service import ClarisaService

logger = get_logger()
notification_service = NotificationService()
clarisa_service = ClarisaService()

icon: str = ":ai: :warning:"

class AuthMiddleware:
    def __init__(self):
        self.is_prod = os.getenv('IS_PROD', 'false').lower() == 'true'
        self.ms_name = os.getenv('MS_NAME', 'Mining Microservice')
        self.star_endpoint_test = os.getenv('STAR_ENDPOINT_TEST')
        self.star_endpoint_prod = os.getenv('STAR_ENDPOINT_PROD')
        self.star_endpoint = self.star_endpoint_prod if is_prod else self.star_endpoint_test
        logger.info(f"Initial configuration: Using {'PRODUCTION' if is_prod else 'TEST'} STAR endpoint")
        logger.debug(f"Initial STAR endpoint configured: {self.star_endpoint}")

    async def validate_token(self, token: str) -> bool:
        """Validate the access token using the management API"""
        if not self.star_endpoint:
            logger.error("STAR endpoint URL is not configured")
            await notification_service.send_slack_notification(
                emoji=icon,
                app_name=self.ms_name,
                color="#FF0000",
                title="Configuration Error",
                message=f"STAR endpoint URL is not configured for {self.ms_name}",
                priority="High"
            )
            return False

        headers = {
            "access-token": token,
            "Content-Type": "application/json"
        }

        try:
            logger.debug(f"Sending token validation request to: {self.star_endpoint}")
            timeout = aiohttp.ClientTimeout(total=10)  # 10 segundos de timeout total
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.patch(self.star_endpoint, headers=headers) as response:
                    logger.debug(f"Response from token validation: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        is_valid = data.get("data", {}).get("isValid", False)
                        logger.debug(f"Token is valid: {is_valid}")
                        return is_valid
                    else:
                        error_text = await response.text()
                        logger.error(f"Token validation failed with status: {response.status}, response: {error_text}")
                        await notification_service.send_slack_notification(
                            emoji=icon,
                            app_name=self.ms_name,
                            color="#FF0000",
                            title="Token Validation Error",
                            message=f"Token validation failed for {self.ms_name} with status code {response.status}",
                            priority="High"
                        )
                        return False

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error validating token: {str(e)}")
            await notification_service.send_slack_notification(
                emoji=icon,
                app_name=self.ms_name,
                color="#FF0000",
                title="Token Validation Error",
                message=f"HTTP error validating token for {self.ms_name}: {str(e)}",
                priority="High"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            await notification_service.send_slack_notification(
                emoji=icon,
                app_name=self.ms_name,
                color="#FF0000",
                title="Token Validation Error",
                message=f"Error validating token for {self.ms_name}: {str(e)}",
                priority="High"
            )
            return False