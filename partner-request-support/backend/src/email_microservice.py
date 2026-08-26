"""
Email microservice integration using RabbitMQ.
"""
import os
import json
import uuid
import pika
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from config.config_util import RABBITMQ
from logger.logger_util import get_logger

logger = get_logger()


class EmailServiceRabbitMQ:
    """RabbitMQ client for the shared email microservice."""

    def __init__(self):
        self.rabbitmq_url = RABBITMQ.get("url")
        self.queue_name = RABBITMQ.get("email_queue_name")
        self.auth = {
            "username": RABBITMQ.get("auth_username"),
            "password": RABBITMQ.get("auth_password"),
        }
        self.from_email = RABBITMQ.get("from_email")
        self.from_name = RABBITMQ.get("from_name")

        self.connection = None
        self.channel = None

    def is_configured(self) -> bool:
        return bool(self.rabbitmq_url and self.queue_name)

    def is_connected(self) -> bool:
        return bool(
            self.connection and not self.connection.is_closed
            and self.channel and self.channel.is_open
        )

    def connect(self) -> bool:
        try:
            if not self.is_configured():
                logger.warning(
                    "⚠️  RabbitMQ not configured (RABBITMQ_URL / EMAIL_QUEUE_NAME missing) "
                    "— email notifications will be simulated/logged only."
                )
                return False

            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)

            logger.info(f"✅ Connected to RabbitMQ email queue '{self.queue_name}'")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False

    def disconnect(self) -> None:
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            logger.warning(f"⚠️  Error disconnecting from RabbitMQ: {e}")

    def send_email(
        self,
        subject: str,
        to: List[str],
        text: str,
        cc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Publish an email-send request to the shared email microservice queue.
        Never raises — a notification failure must never break the caller's flow.
        """
        to = [addr for addr in (to or []) if addr]
        if not to:
            return {"sent": False, "simulated": False, "error": "no recipient provided"}

        if not self.is_configured():
            logger.info(f"📧 [simulated email] to={to} subject={subject!r}\n{text}")
            return {"sent": False, "simulated": True}

        try:
            if not self.is_connected():
                if not self.connect():
                    return {"sent": False, "simulated": True, "error": "RabbitMQ connection unavailable"}

            config_message_dto = {
                "from": {"email": self.from_email, "name": self.from_name},
                "emailBody": {
                    "subject": subject,
                    "to": to,
                    "cc": cc or [],
                    "bcc": None,
                    "message": {"text": text, "socketFile": None},
                },
            }
            payload = {
                "pattern": "send",
                "data": {
                    "auth": self.auth,
                    "data": config_message_dto
                }
            }

            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(payload, default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    message_id=str(uuid.uuid4()),
                    timestamp=int(datetime.now(timezone.utc).timestamp())
                )
            )

            logger.info(f"✅ Email queued via RabbitMQ — to={to} subject={subject!r}")
            return {"sent": True, "simulated": False}

        except Exception as e:
            logger.warning(f"⚠️  Failed to publish email to RabbitMQ: {e}")
            return {"sent": False, "simulated": False, "error": str(e)}


email_service = EmailServiceRabbitMQ()
