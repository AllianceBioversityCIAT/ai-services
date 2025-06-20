import requests
import os
from typing import Dict, Any
from app.utils.logger.logger_util import get_logger
from app.utils.notification.notification_service import NotificationService

logger = get_logger()
notification_service = NotificationService()

icon: str = ":ai: :warning:"

class AuthMiddleware:
    def __init__(self):
        self.ms_name = os.getenv('MS_NAME', 'Mining Microservice')

    async def authenticate(self, message: Dict[str, Any]) -> bool:
        """Authenticate incoming message with access token"""
        logger.debug(f"Authenticating message: {message}")
        token = message.get('token')
        environmentUrl = message.get('environmentUrl') + 'authorization/validate-token'
        logger.debug(f"Environment URL: {environmentUrl}")

        if not token:
            logger.error("No token provided in the request")
            await notification_service.send_slack_notification(
                emoji=icon,
                app_name=self.ms_name,
                color="#FF0000",
                title="Authentication Error",
                message=f"Authentication failed for {self.ms_name}",
                priority="High"
            )
            return False

        logger.debug(f"Validating token for {self.ms_name}")
        return await self.validate_token(token, environmentUrl)

    async def validate_token(self, token: str, environmentUrl: str) -> bool:
        """Validate the access token using the management API"""
        if not environmentUrl:
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
            logger.debug(f"Sending token validation request to: {environmentUrl}")
            response = requests.patch(environmentUrl, headers=headers)
            logger.debug(
                f"Response from token validation: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                is_valid = data.get("data", {}).get("isValid", False)
                logger.debug(f"Token is valid: {is_valid}")
                return is_valid
            else:
                logger.error(
                    f"Token validation failed with status: {response.status_code}")
                await notification_service.send_slack_notification(
                    emoji=icon,
                    app_name=self.ms_name,
                    color="#FF0000",
                    title="Token Validation Error",
                    message=f"Token validation failed for {self.ms_name} with status code {response.status_code}",
                    priority="High"
                )
                return False

        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            await notification_service.send_slack_notification(
                emoji=icon,
                app_name=self.ms_name,
                color="#FF0000",
                title="Token Validation Error",
                message=f"Error validating token for {self.ms_name}: {str(e)}",
                priority="High"
            )
            return False