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
        self.ms_name = os.getenv('MS_NAME', 'Mining Microservice')
        self.star_endpoint_test = os.getenv('STAR_ENDPOINT_TEST')
        self.star_endpoint_prod = os.getenv('STAR_ENDPOINT_PROD')
        self.star_endpoint = self.star_endpoint_prod if is_prod else self.star_endpoint_test
        logger.info(f"Initial configuration: Using {'PRODUCTION' if is_prod else 'TEST'} STAR endpoint")
        logger.debug(f"Initial STAR endpoint configured: {self.star_endpoint}")

    async def authenticate(self, message: Dict[str, Any]) -> bool:
        """Authenticate incoming message with access token"""
        client_id = message.get('client_id')
        client_secret = message.get('client_secret')
        token = message.get('token')
        
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

        if client_id and client_secret:
            try:
                auth_result = await clarisa_service.authorization(client_id, client_secret)
                
                if auth_result.valid and auth_result.data:
                    sender_environment = auth_result.data.get("sender_mis", {}).get("environment", "")
                    logger.info(f"Detected sender environment from CLARISA: {sender_environment}")
                    
                    if sender_environment in ["DEV", "TEST"]:
                        self.star_endpoint = self.star_endpoint_test
                        logger.info(f"Using TEST STAR endpoint based on sender environment: {sender_environment}")
                    else:
                        self.star_endpoint = self.star_endpoint_prod
                        logger.info(f"Using PRODUCTION STAR endpoint based on sender environment: {sender_environment}")
            except Exception as e:
                logger.error(f"Error during CLARISA authentication: {str(e)}")

        logger.debug(f"Validating token for {self.ms_name}")
        return await self.validate_token(token)

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
            response = requests.patch(self.star_endpoint, headers=headers)
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