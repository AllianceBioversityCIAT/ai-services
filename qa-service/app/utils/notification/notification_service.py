import os
import ssl
import certifi
import logging
import aiohttp
from typing import Dict, Any, Optional


class NotificationService:
    def __init__(self):
        """Initialize notification service"""
        self.is_prod = os.getenv('IS_PROD', 'false').lower() == 'true'
        self.logger = logging.getLogger(__name__)
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')

    async def send_slack_notification(
        self,
        emoji: str,
        app_name: str,
        color: str,
        title: str,
        message: str,
        priority: str,
        time_taken: Optional[str]
    ) -> bool:
        """Send a notification to Slack"""
        if not self.slack_webhook:
            self.logger.warning(
                "Slack webhook URL not configured, notification skipped")
            return False

        try:
            env_tag = "🚀 Production 🚀" if self.is_prod else "🚧 Development 🚧"

            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{emoji} *{app_name}* | *Environment:* {env_tag}\n*{title}*\n{message}\n{time_taken}\n*Priority:* {priority}"
                        }
                    }
                ],
                "attachments": [
                    {
                        "color": color
                    }
                ]
            }

            ssl_context = ssl.create_default_context(cafile=certifi.where())

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
                async with session.post(self.slack_webhook, json=payload) as response:
                    if response.status != 200:
                        self.logger.error(
                            f"Failed to send Slack notification: {response.status}")
                        return False
                    self.logger.info("✅ Slack notification sent successfully")
                    return True

        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {str(e)}")
            return False
