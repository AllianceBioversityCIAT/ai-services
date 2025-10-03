"""
Email microservice integration using RabbitMQ.

This module handles communication with the email microservice through RabbitMQ
for sending notifications, particularly for negative feedback alerts.
"""

import json
import pika
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.utils.logger.logger_util import get_logger
from app.utils.config.config_util import RABBITMQ

logger = get_logger()


class EmailServiceRabbitMQ:
    """
    RabbitMQ client for email microservice communication.
    
    Handles connection management, message publishing, and error handling
    for email notifications through RabbitMQ message queue.
    """
    
    def __init__(self):
        """Initialize RabbitMQ connection parameters."""
        self.rabbitmq_url = RABBITMQ.get('url')
        self.queue_name = RABBITMQ.get('email_queue_name')
        self.exchange_name = ''

        self.auth_header_ms1 = {
            "username": RABBITMQ.get('auth_username'),
            "password": RABBITMQ.get('auth_password')
        }
        
        self.from_email = RABBITMQ.get('from_email')
        self.from_name = RABBITMQ.get('from_name')
        self.negative_feedback_recipients = RABBITMQ.get('feedback_recipients')

        self.connection = None
        self.channel = None
        
        logger.info("🐰 Initializing RabbitMQ Email Service")
        logger.info(f"🔗 Queue: {self.queue_name}")
        logger.info(f"🎯 Pattern: send")
        logger.info(f"👤 Auth User: {self.auth_header_ms1.get('username', 'Not configured')}")
        logger.info(f"📧 Recipients: {len(self.negative_feedback_recipients or [])} configured")


    def connect(self) -> bool:
        """
        Establish connection to RabbitMQ server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("🔌 Connecting to RabbitMQ server...")
            
            if not self.rabbitmq_url:
                logger.error("❌ RabbitMQ URL not configured")
                return False
            
            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            logger.info("✅ Successfully connected to RabbitMQ server")
            
            self._setup_queue()
            
            return True
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error connecting to RabbitMQ: {e}")
            return False


    def _setup_queue(self) -> None:
        """Setup queue for email notifications."""
        try:
            logger.info("⚙️ Setting up RabbitMQ queue...")
            
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            logger.info(f"✅ Queue '{self.queue_name}' setup completed")
            
        except Exception as e:
            logger.error(f"❌ Error setting up queue: {e}")
            raise


    def is_connected(self) -> bool:
        """
        Check if RabbitMQ connection is active.
        
        Returns:
            True if connected and channel is open
        """
        return (
            self.connection and 
            not self.connection.is_closed and 
            self.channel and 
            self.channel.is_open
        )


    def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            logger.info("🔌 Disconnecting from RabbitMQ...")
            
            if self.channel and self.channel.is_open:
                self.channel.close()
                logger.info("📡 Channel closed")
            
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("🔗 Connection closed")
            
            logger.info("✅ Disconnected from RabbitMQ successfully")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting from RabbitMQ: {e}")


    def send_email(self, config_message_dto: Dict[str, Any]) -> bool:
        """
        Send email via RabbitMQ following the microservice structure.
        
        Args:
            config_message_dto: Email configuration following ConfigMessageDto structure
            
        Returns:
            True if message sent successfully
        """
        try:
            logger.info("📤 Emitting email via RabbitMQ with pattern 'send'...")
            
            if not self.is_connected():
                logger.warning("⚠️ Not connected to RabbitMQ, attempting to reconnect...")
                if not self.connect():
                    logger.error("❌ Failed to reconnect to RabbitMQ")
                    return False
            
            payload = {
                "pattern": "send",
                "data": {
                    "auth": self.auth_header_ms1,
                    "data": config_message_dto
                }
            }

            message_body = json.dumps(payload, default=str)
            
            logger.info(f"📦 Payload structure: pattern='send' + auth + data")
            logger.info(f"🔐 Auth user: {self.auth_header_ms1.get('username')}")
            logger.info(f"📧 Recipients: {config_message_dto.get('emailBody', {}).get('to', [])}")
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    message_id=str(uuid.uuid4()),
                    timestamp=int(datetime.now(timezone.utc).timestamp())
                )
            )
            
            logger.info("✅ Email message emitted successfully to RabbitMQ")
            logger.info(f"📬 Queue: {self.queue_name}")
            logger.info(f"🎯 Pattern: send")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error emitting email via RabbitMQ: {e}")
            return False


email_service = EmailServiceRabbitMQ()


def send_negative_feedback_email(feedback_data: Dict[str, Any]) -> bool:
    """
    Send negative feedback notification email via RabbitMQ.
    
    Args:
        feedback_data: Feedback data to include in notification
        
    Returns:
        True if email queued successfully
    """
    try:
        logger.info(f"📧 Preparing negative feedback email for: {feedback_data.get('feedback_id')}")
        
        if not email_service.is_connected():
            logger.info("🔄 Email service not connected, connecting...")
            if not email_service.connect():
                logger.error("❌ Failed to connect to email service")
                return False

        service_name = feedback_data.get('service_display_name', feedback_data.get('service_name', 'AI Service'))
        subject = f"🚨 Negative Feedback Alert - {service_name}"
        
        email_text = _create_negative_feedback_email_text(feedback_data)
        
        config_message_dto = {
            "from": {
                "email": email_service.from_email,
                "name": email_service.from_name
            },
            "emailBody": {
                "subject": subject,
                "to": email_service.negative_feedback_recipients,
                "cc": [],
                "bcc": None,
                "message": {
                    "text": email_text,
                    "socketFile": None
                }
            }
        }
        
        logger.info(f"📋 Email structure:")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Recipients: {email_service.negative_feedback_recipients}")
        logger.info(f"   From: {email_service.from_email}")
        
        success = email_service.send_email(config_message_dto)
        
        if success:
            logger.info(f"✅ Negative feedback email queued: {feedback_data.get('feedback_id')}")
        else:
            logger.error(f"❌ Failed to queue negative feedback email: {feedback_data.get('feedback_id')}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error sending negative feedback email: {e}")
        return False


def _create_negative_feedback_email_text(feedback_data: Dict[str, Any]) -> str:
    """Create formatted email text for negative feedback notification."""
    timestamp = feedback_data.get('timestamp', 'Unknown')
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            pass
    
    email_text = f"""
🚨 NEGATIVE FEEDBACK ALERT 🚨

A user has submitted negative feedback for one of our AI services. Please review the details below:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 FEEDBACK DETAILS:
• Feedback ID: {feedback_data.get('feedback_id', 'N/A')}
• Feedback Type: {feedback_data.get('feedback_type', 'N/A').upper()}
• Timestamp: {timestamp}
• Service: {feedback_data.get('service_display_name', 'N/A')} ({feedback_data.get('service_name', 'N/A')})

👤 USER INFORMATION:
• User ID: {feedback_data.get('user_id', 'N/A')}
• Platform: {feedback_data.get('platform', 'N/A')}
• Session ID: {feedback_data.get('session_id', 'N/A')}

💬 USER COMMENT:
"{feedback_data.get('feedback_comment', 'No comment provided')}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 AI INTERACTION DETAILS:

📝 User Input:
{feedback_data.get('user_input', 'No input recorded')[:500]}{'...' if len(str(feedback_data.get('user_input', ''))) > 500 else ''}

🤖 AI Output:
{feedback_data.get('ai_output', 'No output recorded')[:500]}{'...' if len(str(feedback_data.get('ai_output', ''))) > 500 else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 ADDITIONAL CONTEXT:
{_format_context_data(feedback_data.get('context', {}))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 RECOMMENDED ACTIONS:
1. Review the AI output quality for this specific interaction
2. Analyze if this is a recurring issue with similar user inputs
3. Consider updating the AI model or prompts if needed
4. Follow up with the user if appropriate

This is an automated notification from the IBD AI Services Feedback System.
Please review and take appropriate action as needed.

Best regards,
IBD AI Services Team
    """.strip()
    
    return email_text


def _format_context_data(context: Dict[str, Any]) -> str:
    """Format context data for email display."""
    if not context:
        return "No additional context provided"
    
    formatted = []
    for key, value in context.items():
        formatted.append(f"• {key}: {value}")
    
    return '\n'.join(formatted) if formatted else "No additional context provided"