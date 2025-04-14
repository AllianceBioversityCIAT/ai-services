import json
import logging
import os
from typing import Dict, Any, Optional, Callable, Awaitable
from app.utils.clarisa.clarisa_service import ClarisaService
from app.utils.clarisa.dto.clarisa_connection_dto import ResClarisaValidateConnectionDto
from app.utils.notification.notification_service import NotificationService
from app.utils.logger.logger_util import logger


class AuthMiddleware:
    def __init__(self):
        """Initialize authentication middleware"""
        self.clarisa_service = ClarisaService()
        self.notification_service = NotificationService()
        self.ms_name = os.getenv('MS_NAME', 'Mining Microservice')

    async def authenticate(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate incoming message with CLARISA credentials"""
        try:
            credentials = message.get('credentials', '{}')
            if isinstance(credentials, str):
                payload = json.loads(credentials)
            else:
                payload = credentials

            username = payload.get('username')
            password = payload.get('password')

            logger.debug(
                f"Client {username} is trying to access {self.ms_name}")

            auth_data = await self.clarisa_service.authorization(username, password)

            if not auth_data.valid:
                await self.notification_service.send_slack_notification(
                    emoji=':alert:',
                    app_name=self.ms_name,
                    color='#FF0000',
                    title='Invalid credentials',
                    message=f"User {username} tried to access {self.ms_name} with invalid credentials",
                    priority='Medium'
                )
                logger.error(f"Authentication failed for user {username}")
                return None

            validated_data = auth_data.data

            actual_data = validated_data
            if isinstance(validated_data, dict) and 'response' in validated_data:
                actual_data = validated_data['response']

            logger.debug(f"Validated data structure: {actual_data}")

            sender_mis = actual_data.get('sender_mis', {})
            receiver_mis = actual_data.get('receiver_mis', {})

            new_data = {
                **message,
                'user': {
                    **payload,
                    'environment': receiver_mis.get('environment'),
                    'sender': actual_data
                }
            }

            logger.info(f"🚀 - Sender info: {sender_mis}")
            logger.info(f"📡 - Receiver info: {receiver_mis}")

            sender_name = sender_mis.get('name', 'unknown')
            sender_env = sender_mis.get('environment', 'unknown')

            logger.info(
                f"Client {sender_name} in {sender_env} "
                f"environment is authorized to access {self.ms_name}"
            )

            return new_data

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await self.notification_service.send_slack_notification(
                emoji=':alert:',
                app_name=self.ms_name,
                color='#FF0000',
                title='Authentication Error',
                message=f"Error during authentication process: {str(e)}",
                priority='High'
            )
            return None

    def wrap_handler(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        """Create a wrapper that authenticates before calling the original handler"""
        async def wrapped_handler(message: Dict[str, Any]) -> None:
            authenticated_message = await self.authenticate(message)
            if authenticated_message:
                await handler(authenticated_message)
            else:
                logger.error(
                    "Authentication failed, message processing skipped")

        return wrapped_handler
