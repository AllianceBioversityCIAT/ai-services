"""
General AI Services Feedback Management System.

This service handles the collection, storage, and retrieval of user feedback
on AI-generated responses across different AI services for quality improvement 
and monitoring.

Supported AI Services:
- Chatbot services (conversational AI)
- Any other AI service that generates user-facing content

The service is designed to be service-agnostic and can adapt to different
types of AI interactions while maintaining consistent feedback collection
and analytics capabilities.
"""

import json
import uuid
import boto3
from decimal import Decimal
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from app.utils.config.config_util import BR
from boto3.dynamodb.conditions import Key, Attr
from typing import List, Dict, Optional, Any, Tuple
from app.utils.logger.logger_util import get_logger
from app.utils.microservices.send_email import send_negative_feedback_email
from app.api.models import (FeedbackRequest, FeedbackResponse, FeedbackSummary, GetFeedbackRequest)

logger = get_logger()


class AIFeedbackService:
    """
    General feedback service for AI services using DynamoDB.
    
    This service provides comprehensive feedback management capabilities
    for any AI service that generates user-facing content. It supports:
    
    - Multi-service feedback collection with dedicated tables
    - Flexible metadata storage
    - Service-specific analytics
    - Scalable DynamoDB storage architecture
    - Auto table creation per service
    """
    

    def __init__(self):
        """Initialize the AI feedback service with DynamoDB."""
        self.table_prefix = "ai-feedback"
        
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=BR['aws_access_key'],
            aws_secret_access_key=BR['aws_secret_key'],
            region_name=BR['region']
        )
        
        self.dynamodb_client = boto3.client(
            'dynamodb',
            aws_access_key_id=BR['aws_access_key'],
            aws_secret_access_key=BR['aws_secret_key'],
            region_name=BR['region']
        )
        
        self.registered_services = {}
        self.service_tables = {}
        
        self.register_service(
            service_name="chatbot",
            display_name="AICCRA Chatbot",
            description="Conversational AI for AICCRA data exploration",
            expected_context=["filters_applied"]
        )
        
        logger.info("🚀 AI Feedback Service initialized with DynamoDB multi-table support")
    

    def submit_feedback(self, feedback_request: FeedbackRequest) -> FeedbackResponse:
        """
        Submit user feedback for an AI service response.
        
        Args:
            feedback_request: The feedback data to store
            
        Returns:
            FeedbackResponse with confirmation details
            
        Raises:
            RuntimeError: If feedback submission fails
        """
        try:
            feedback_id = f"fb_{uuid.uuid4()}"
            timestamp = datetime.now(timezone.utc)
            
            logger.info(f"📝 Processing feedback submission for service: {feedback_request.service_name}")
            logger.info(f"🆔 Feedback ID: {feedback_id}")
            logger.info(f"👤 User: {feedback_request.user_id}")
            logger.info(f"📊 Type: {feedback_request.feedback_type}")
            
            service_info = self._get_service_info(feedback_request.service_name)
            table = self._get_service_table(feedback_request.service_name)
            
            feedback_record = self._create_feedback_record(
                feedback_id, timestamp, feedback_request, service_info
            )
            
            self._save_feedback_to_dynamodb(table, feedback_record)
            
            if self._is_negative_feedback(feedback_request.feedback_type):
                try:
                    logger.info(f"📧 Detected negative feedback, sending notification email...")
                    self._send_negative_feedback_notification(feedback_record, feedback_request)
                except Exception as email_error:
                    logger.error(f"❌ Failed to send negative feedback notification: {email_error}")

            logger.info(f"✅ Feedback submitted successfully: {feedback_id}")
            
            return FeedbackResponse(
                feedback_id=feedback_id,
                status="success",
                message=f"Feedback submitted successfully for {service_info['name']}. Thank you for helping us improve our AI services!",
                timestamp=timestamp,
                service_name=feedback_request.service_name
            )
            
        except Exception as e:
            logger.error(f"❌ Error submitting feedback: {e}")
            raise RuntimeError(f"Failed to submit feedback: {str(e)}")
    

    def get_feedback_summary(
        self, 
        service_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> FeedbackSummary:
        """
        Get summary statistics for feedback data.
        
        Args:
            service_name: Optional filter by service name
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            FeedbackSummary with statistics
        """
        try:
            logger.info(f"📊 Generating feedback summary...")
            logger.info(f"🔍 Service filter: {service_name or 'All services'}")
            logger.info(f"📅 Date range: {start_date} to {end_date}")
            
            all_feedback = self._read_feedback_from_dynamodb(
                service_name=service_name,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"📊 Found {len(all_feedback)} feedback entries for analysis")
            
            services_breakdown = {}
            total_positive = 0
            total_negative = 0
            response_times = []
            recent_feedback = []
            
            if service_name:
                services_breakdown[service_name] = {"positive": 0, "negative": 0}
            else:
                for service in self.registered_services.keys():
                    services_breakdown[service] = {"positive": 0, "negative": 0}

            for feedback in all_feedback:
                feedback_type = feedback.get('feedback_type', '').lower()
                service = feedback.get('service_name', 'unknown')

                if service not in services_breakdown:
                    services_breakdown[service] = {"positive": 0, "negative": 0}

                if feedback_type in ['positive', 'like', 'thumbs_up', 'good']:
                    total_positive += 1
                    services_breakdown[service]["positive"] += 1
                elif feedback_type in ['negative', 'dislike', 'thumbs_down', 'bad']:
                    total_negative += 1
                    services_breakdown[service]["negative"] += 1

                response_time = feedback.get('response_time_seconds')
                if response_time is not None:
                    if isinstance(response_time, Decimal):
                        response_time = float(response_time)
                    response_times.append(response_time)

                if len(recent_feedback) < 10:
                    feedback_comment = feedback.get('feedback_comment', '')

                    recent_feedback.append({
                        'service_name': service,
                        'feedback_type': feedback_type,
                        'timestamp': feedback.get('timestamp'),
                        'user_feedback': feedback_comment,
                        'has_comment': bool(feedback_comment and str(feedback_comment).strip())
                    })
            
            total_feedback = total_positive + total_negative
            satisfaction_rate = (total_positive / total_feedback * 100) if total_feedback > 0 else 0.0
            average_response_time = sum(response_times) / len(response_times) if response_times else None
            
            recent_feedback.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            summary = FeedbackSummary(
                service_name=service_name,
                total_feedback=total_feedback,
                positive_feedback=total_positive,
                negative_feedback=total_negative,
                satisfaction_rate=round(satisfaction_rate, 2),
                average_response_time=round(average_response_time, 2) if average_response_time else None,
                services_breakdown=services_breakdown,
                recent_feedback=recent_feedback[:10],
                time_period={
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            )
            
            logger.info(f"✅ Feedback summary generated: {total_feedback} total entries, {satisfaction_rate:.1f}% satisfaction")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating feedback summary: {e}")
            raise RuntimeError(f"Failed to generate feedback summary: {str(e)}")
    

    def get_feedback(self, request: GetFeedbackRequest) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve feedback entries based on filters.
        
        Args:
            request: Filtering and pagination parameters
            
        Returns:
            Tuple of (feedback_entries, total_count)
        """
        try:
            logger.info(f"🔍 Retrieving feedback with filters...")
            logger.info(f"🏷️ Service: {request.service_name or 'All'}")
            logger.info(f"👤 User: {request.user_id or 'All'}")
            logger.info(f"📊 Type: {request.feedback_type or 'All'}")
            logger.info(f"📄 Limit: {request.limit}, Offset: {request.offset}")
            
            all_feedback = self._read_feedback_from_dynamodb(
                service_name=request.service_name,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            filtered_feedback = []
            for feedback in all_feedback:
                if request.user_id and feedback.get('user_id') != request.user_id:
                    continue
                    
                if request.feedback_type and feedback.get('feedback_type') != request.feedback_type:
                    continue

                if request.has_comment is not None:
                    has_comment = feedback.get('has_comment', False)
                    if request.has_comment != has_comment:
                        continue

                if request.max_response_time is not None:
                    response_time = feedback.get('response_time_seconds')
                    if response_time is None or response_time > request.max_response_time:
                        continue
                
                filtered_feedback.append(feedback)
            
            if request.sort_by:
                reverse_order = request.sort_order == "desc"
                if request.sort_by == "timestamp":
                    filtered_feedback.sort(key=lambda x: x.get('timestamp', ''), reverse=reverse_order)
                elif request.sort_by == "feedback_type":
                    filtered_feedback.sort(key=lambda x: x.get('feedback_type', ''), reverse=reverse_order)
                elif request.sort_by == "service_name":
                    filtered_feedback.sort(key=lambda x: x.get('service_name', ''), reverse=reverse_order)
                elif request.sort_by == "response_time":
                    filtered_feedback.sort(key=lambda x: x.get('response_time_seconds', 0), reverse=reverse_order)
            
            total_count = len(filtered_feedback)
            
            start_index = request.offset
            end_index = start_index + request.limit
            feedback_entries = filtered_feedback[start_index:end_index]
            
            logger.info(f"✅ Retrieved {len(feedback_entries)} feedback entries (total: {total_count})")
            return feedback_entries, total_count
            
        except Exception as e:
            logger.error(f"❌ Error retrieving feedback: {e}")
            raise RuntimeError(f"Failed to retrieve feedback: {str(e)}")
    

    def get_service_feedback(
        self, 
        service_name: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific AI service.
        
        Args:
            service_name: The service name to filter by
            limit: Maximum number of entries to return
            
        Returns:
            List of feedback entries for the service
        """
        try:
            logger.info(f"🔍 Retrieving feedback for service: {service_name}")
            
            request = GetFeedbackRequest(service_name=service_name, limit=limit)
            feedback_entries, _ = self.get_feedback(request)
            
            return feedback_entries
            
        except Exception as e:
            logger.error(f"❌ Error retrieving service feedback: {e}")
            raise RuntimeError(f"Failed to retrieve service feedback: {str(e)}")
    

    def get_registered_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about registered AI services.
        
        Returns:
            Dictionary of registered services and their metadata
        """
        return self.registered_services.copy()
    

    def register_service(
        self, 
        service_name: str, 
        display_name: str, 
        description: str,
        expected_context: Optional[List[str]] = None
    ) -> bool:
        """
        Register a new AI service for feedback collection.
        
        Args:
            service_name: Unique identifier for the service
            display_name: Human-readable name
            description: Service description
            expected_context: Expected context fields
            
        Returns:
            True if registration successful
        """
        try:
            self.registered_services[service_name] = {
                "name": display_name,
                "description": description,
                "expected_context": expected_context or []
            }
            
            self._create_service_table(service_name)
            
            logger.info(f"✅ Registered new AI service: {service_name} ({display_name})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error registering service {service_name}: {e}")
            return False
    

    def _get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get service information, register if unknown."""
        if service_name in self.registered_services:
            return self.registered_services[service_name]
        else:
            logger.info(f"🆕 Auto-registering unknown service: {service_name}")
            display_name = service_name.replace("-", " ").replace("_", " ").title()
            description = f"AI service: {service_name}"
            
            self.register_service(
                service_name=service_name,
                display_name=display_name,
                description=description,
                expected_context=[]
            )
            
            return self.registered_services[service_name]
    

    def _get_service_table(self, service_name: str):
        """Get DynamoDB table for a service, create if not exists."""
        table_name = f"{self.table_prefix}-{service_name}"
        
        if service_name not in self.service_tables:
            self.service_tables[service_name] = self.dynamodb.Table(table_name)
        
        return self.service_tables[service_name]
    

    def _create_service_table(self, service_name: str) -> None:
        """Create DynamoDB table for a service if it doesn't exist."""
        table_name = f"{self.table_prefix}-{service_name}"
        
        try:
            self.dynamodb_client.describe_table(TableName=table_name)
            logger.info(f"🏷️ Table {table_name} already exists")
            return
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise e
        
        try:
            logger.info(f"🏗️ Creating DynamoDB table: {table_name}")
            
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'feedback_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'timestamp',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'feedback_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'feedback_type',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'user-timestamp-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'timestamp',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    },
                    {
                        'IndexName': 'feedback-type-timestamp-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'feedback_type',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'timestamp',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            table.wait_until_exists()
            
            logger.info(f"✅ Table {table_name} created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating table {table_name}: {e}")
            raise
    

    def _create_feedback_record(
        self, 
        feedback_id: str, 
        timestamp: datetime, 
        request: FeedbackRequest,
        service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive feedback record."""
        
        input_length = len(request.user_input) if request.user_input else 0
        output_length = len(request.ai_output) if request.ai_output else 0
        comment_length = len(request.feedback_comment) if request.feedback_comment else 0
        
        return {
            # Core feedback data
            "feedback_id": feedback_id,
            "timestamp": timestamp.isoformat(),
            "feedback_type": request.feedback_type,
            "feedback_comment": request.feedback_comment,
            "has_comment": request.feedback_comment is not None,

            # User and session context
            "user_id": request.user_id,
            "session_id": request.session_id,
            "platform": request.platform,
            
            # Service information
            "service_name": request.service_name,
            "service_display_name": service_info["name"],
            "service_description": service_info["description"],
            
            # AI interaction data
            "user_input": request.user_input,
            "ai_output": request.ai_output,
            "input_length": input_length,
            "output_length": output_length,
            
            # Performance metrics
            "response_time_seconds": request.response_time_seconds,
            
            # Service-specific context
            "context": request.context,
            
            # Computed metadata
            "metadata": {
                "comment_length": comment_length,
                "has_session": request.session_id is not None,
                "has_performance_data": request.response_time_seconds is not None,
                "context_fields": list(request.context.keys()) if request.context else []
            }
        }
    

    def _clean_record_for_dynamodb(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean record for DynamoDB by removing None values, empty strings, and converting floats to Decimal."""
        cleaned = {}
        
        for key, value in record.items():
            if value is None:
                continue
            elif isinstance(value, str) and value == "":
                continue
            elif isinstance(value, float):
                cleaned[key] = Decimal(str(value))
            elif isinstance(value, int):
                cleaned[key] = value
            elif isinstance(value, dict):
                cleaned_dict = self._clean_record_for_dynamodb(value)
                if cleaned_dict:
                    cleaned[key] = cleaned_dict
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = self._clean_record_for_dynamodb(item)
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    elif isinstance(item, float):
                        cleaned_list.append(Decimal(str(item)))
                    elif item is not None and item != "":
                        cleaned_list.append(item)
                
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value
        
        return cleaned
    

    def _save_feedback_to_dynamodb(self, table, feedback_record: Dict[str, Any]) -> None:
        """Save feedback record to DynamoDB."""
        try:
            cleaned_record = self._clean_record_for_dynamodb(feedback_record)
            
            logger.info(f"💾 Saving feedback to DynamoDB table: {table.name}")
            logger.debug(f"🔍 Cleaned record keys: {list(cleaned_record.keys())}")

            table.put_item(Item=cleaned_record)
            
            logger.info(f"💾 Feedback saved to DynamoDB table: {table.name}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to DynamoDB: {e}")
            logger.error(f"🔍 Record that failed: {json.dumps(feedback_record, default=str, indent=2)}")
            raise
    

    def _read_feedback_from_dynamodb(
        self, 
        service_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read feedback data from DynamoDB.
        
        Args:
            service_name: Optional filter by service name
            start_date: Optional start date filter
            end_date: Optional end_date filter
            
        Returns:
            List of feedback records
        """
        try:
            all_feedback = []
            
            if service_name:
                services_to_query = [service_name]
            else:
                services_to_query = self._discover_feedback_services()
            
            logger.info(f"📋 Services to query: {services_to_query}")
            
            for service in services_to_query:
                try:
                    table = self._get_service_table(service)
                    
                    filter_expression = None
                    
                    if start_date:
                        start_str = start_date.isoformat()
                        filter_expression = Attr('timestamp').gte(start_str)
                    
                    if end_date:
                        end_str = end_date.isoformat()
                        if filter_expression:
                            filter_expression = filter_expression & Attr('timestamp').lte(end_str)
                        else:
                            filter_expression = Attr('timestamp').lte(end_str)
                    
                    scan_kwargs = {}
                    if filter_expression:
                        scan_kwargs['FilterExpression'] = filter_expression
                    
                    response = table.scan(**scan_kwargs)
                    
                    service_feedback = response.get('Items', [])
                    logger.info(f"📊 Found {len(service_feedback)} items for service: {service}")
                    
                    while 'LastEvaluatedKey' in response:
                        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                        response = table.scan(**scan_kwargs)
                        service_feedback.extend(response.get('Items', []))
                    
                    all_feedback.extend(service_feedback)
                    
                except Exception as service_error:
                    logger.warning(f"⚠️ Error querying DynamoDB for service {service}: {service_error}")
                    continue
            
            logger.info(f"📊 Retrieved {len(all_feedback)} feedback entries from DynamoDB")
            return all_feedback
            
        except Exception as e:
            logger.error(f"❌ Error reading feedback from DynamoDB: {e}")
            return []


    def _discover_feedback_services(self) -> List[str]:
        """
        Discover all existing feedback tables in DynamoDB.
        
        Returns:
            List of service names that have feedback tables
        """
        try:
            response = self.dynamodb_client.list_tables()
            all_tables = response.get('TableNames', [])
            
            while 'LastEvaluatedTableName' in response:
                response = self.dynamodb_client.list_tables(
                    ExclusiveStartTableName=response['LastEvaluatedTableName']
                )
                all_tables.extend(response.get('TableNames', []))
            
            feedback_tables = [
                table for table in all_tables 
                if table.startswith(f"{self.table_prefix}-")
            ]
            
            services = []
            for table in feedback_tables:
                service_name = table.replace(f"{self.table_prefix}-", "")
                services.append(service_name)
                
                if service_name not in self.registered_services:
                    logger.info(f"🔄 Auto-registering discovered service: {service_name}")
                    display_name = service_name.replace("-", " ").replace("_", " ").title()
                    self.registered_services[service_name] = {
                        "name": display_name,
                        "description": f"Auto-discovered AI service: {service_name}",
                        "expected_context": []
                    }
            
            logger.info(f"🔍 Discovered {len(services)} feedback services: {services}")
            return services
            
        except Exception as e:
            logger.error(f"❌ Error discovering feedback services: {e}")
            return list(self.registered_services.keys())
    

    def _is_negative_feedback(self, feedback_type: str) -> bool:
        """
        Determine if feedback is negative based on feedback type.
        
        Args:
            feedback_type: The type of feedback
            
        Returns:
            True if feedback is considered negative
        """
        negative_types = ['negative', 'dislike', 'thumbs_down', 'bad', 'poor', 'unsatisfied']
        return feedback_type.lower() in negative_types


    def _send_negative_feedback_notification(self, feedback_record: Dict[str, Any], feedback_request: FeedbackRequest) -> None:
        """
        Send email notification for negative feedback using the email microservice.
        
        Args:
            feedback_record: The complete feedback record
            feedback_request: The original feedback request
        """
        try:            
            logger.info(f"📧 Sending negative feedback notification for: {feedback_record['feedback_id']}")
            
            # Preparar los datos más importantes para el email
            email_data = {
                'feedback_id': feedback_record['feedback_id'],
                'feedback_type': feedback_record['feedback_type'],
                'feedback_comment': feedback_record.get('feedback_comment', 'No comment provided'),
                'user_id': feedback_record['user_id'],
                'service_name': feedback_record['service_name'],
                'service_display_name': feedback_record['service_display_name'],
                'timestamp': feedback_record['timestamp'],
                'user_input': feedback_record.get('user_input', ''),
                'ai_output': feedback_record.get('ai_output', ''),
                'session_id': feedback_record.get('session_id', ''),
                'platform': feedback_record.get('platform', ''),
                'response_time_seconds': feedback_record.get('response_time_seconds', 0),
                'context': feedback_record.get('context', {})
            }
            
            # Llamar al microservicio de email
            send_negative_feedback_email(email_data)
            
            logger.info(f"✅ Negative feedback notification sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error sending negative feedback notification: {e}")
            raise


# Global feedback service instance
ai_feedback_service = AIFeedbackService()