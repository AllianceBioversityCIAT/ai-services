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
from boto3.dynamodb.conditions import Key, Attr
from app.utils.config.config_util import BR, ENV
from typing import List, Dict, Optional, Any, Tuple
from app.utils.logger.logger_util import get_logger
from app.utils.microservices.send_email import send_negative_feedback_email
from app.api.models import (AIInteractionRequest, AIInteractionResponse, InteractionSummary, GetInteractionRequest)

logger = get_logger()


class AIInteractionService:
    """
    AI Interaction tracking service using DynamoDB.
    
    This service provides comprehensive interaction tracking capabilities
    for any AI service that generates user-facing content. It supports:
    
    - All AI interaction tracking with optional feedback
    - Single table architecture for all services
    - Environment-based table separation (test/prod)
    - Flexible metadata storage
    - Service-specific analytics
    - Feedback update capabilities
    """
    

    def __init__(self):
        """Initialize the AI interaction service with DynamoDB."""
        self.table_name = f"ai-requests-{ENV}"
        
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
        self.table = None
        
        self._initialize_table()
        
        self.register_service(
            service_name="chatbot",
            display_name="AICCRA Chatbot",
            description="Conversational AI for AICCRA data exploration",
            expected_context=["filters_applied"]
        )


    def _initialize_table(self) -> None:
        """Initialize the single DynamoDB table for all interactions."""
        try:
            # Check if table exists
            self.table = self.dynamodb.Table(self.table_name)
            self.table.load()
            logger.info(f"✅ Connected to existing table: {self.table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                self._create_interaction_table()
            else:
                logger.error(f"❌ Error connecting to table: {e}")
                raise


    def _create_interaction_table(self) -> None:
        """Create the single DynamoDB table for all AI interactions."""
        try:
            logger.info(f"� Creating DynamoDB table: {self.table_name}")
            
            self.table = self.dynamodb.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'interaction_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'service_name',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'interaction_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'service_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'ServiceTimestampIndex',
                        'KeySchema': [
                            {
                                'AttributeName': 'service_name',
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
            
            # Wait for table to be created
            logger.info(f"⏳ Waiting for table creation to complete...")
            self.table.wait_until_exists()
            
            logger.info(f"✅ Table {self.table_name} created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating table {self.table_name}: {e}")
            raise


    def _get_interaction_record(self, interaction_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        """Get interaction record by ID and service name."""
        try:
            response = self.table.get_item(
                Key={
                    'interaction_id': interaction_id,
                    'service_name': service_name
                }
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"❌ Error getting interaction record: {e}")
            return None
    

    def track_interaction(self, interaction_request: AIInteractionRequest) -> AIInteractionResponse:
        """
        Track AI interaction and optionally update with feedback.
        
        Args:
            interaction_request: The interaction data to track or update
            
        Returns:
            AIInteractionResponse with confirmation details
            
        Raises:
            RuntimeError: If interaction tracking fails
        """
        try:
            # Check if this is an update operation
            if interaction_request.update_mode and interaction_request.interaction_id:
                # Update existing interaction with feedback
                return self._update_interaction_with_feedback(interaction_request)
            
            # Create new interaction tracking
            interaction_id = f"req_{uuid.uuid4()}"
            timestamp = datetime.now(timezone.utc)
            
            logger.info(f"📝 Processing AI interaction for service: {interaction_request.service_name}")
            logger.info(f"🆔 Interaction ID: {interaction_id}")
            logger.info(f"👤 User: {interaction_request.user_id}")
            logger.info(f"📊 Has Feedback: {interaction_request.feedback_type is not None}")
            
            service_info = self._get_service_info(interaction_request.service_name)
            
            interaction_record = self._create_interaction_record(
                interaction_id, timestamp, interaction_request, service_info
            )
            
            self._save_interaction_to_dynamodb(interaction_record)
            
            # Send negative feedback notification if applicable
            if interaction_request.feedback_type and self._is_negative_feedback(interaction_request.feedback_type):
                try:
                    logger.info(f"📧 Detected negative feedback, sending notification email...")
                    self._send_negative_feedback_notification(interaction_record, interaction_request)
                except Exception as email_error:
                    logger.error(f"❌ Failed to send negative feedback notification: {email_error}")
                    # No lanzamos excepción aquí para no afectar el flujo principal

            logger.info(f"✅ Interaction tracked successfully: {interaction_id}")
            
            return AIInteractionResponse(
                interaction_id=interaction_id,
                status="success",
                message=f"AI interaction tracked successfully for {service_info['name']}" + 
                       (" with feedback" if interaction_request.feedback_type else ""),
                timestamp=timestamp,
                service_name=interaction_request.service_name,
                has_feedback=interaction_request.feedback_type is not None
            )
            
        except Exception as e:
            logger.error(f"❌ Error tracking interaction: {e}")
            raise RuntimeError(f"Failed to track interaction: {str(e)}")
    

    def _update_interaction_with_feedback(self, interaction_request: AIInteractionRequest) -> AIInteractionResponse:
        """
        Update existing interaction with feedback data.
        
        Args:
            interaction_request: Request containing feedback update
            
        Returns:
            AIInteractionResponse with update confirmation
        """
        try:
            logger.info(f"🔄 Updating interaction {interaction_request.interaction_id} with feedback")
            
            timestamp = datetime.now(timezone.utc)
            
            # Prepare update expression
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            updates = []
            
            if interaction_request.feedback_type:
                updates.append("#feedback_type = :feedback_type")
                expression_attribute_names["#feedback_type"] = "feedback_type"
                expression_attribute_values[":feedback_type"] = interaction_request.feedback_type
                
                updates.append("has_feedback = :has_feedback")
                expression_attribute_values[":has_feedback"] = True
            
            if interaction_request.feedback_comment:
                updates.append("feedback_comment = :feedback_comment")
                expression_attribute_values[":feedback_comment"] = interaction_request.feedback_comment
                
                updates.append("has_comment = :has_comment")
                expression_attribute_values[":has_comment"] = True
            
            updates.append("feedback_timestamp = :feedback_timestamp")
            expression_attribute_values[":feedback_timestamp"] = timestamp.isoformat()
            
            update_expression += ", ".join(updates)
            
            # Update the item
            self.table.update_item(
                Key={
                    'interaction_id': interaction_request.interaction_id,
                    'service_name': interaction_request.service_name
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names if expression_attribute_names else None
            )
            
            # Send negative feedback notification if applicable
            if interaction_request.feedback_type and self._is_negative_feedback(interaction_request.feedback_type):
                try:
                    # Get the full record for email notification
                    interaction_record = self._get_interaction_record(interaction_request.interaction_id, interaction_request.service_name)
                    if interaction_record:
                        logger.info(f"📧 Detected negative feedback in update, sending notification email...")
                        self._send_negative_feedback_notification(interaction_record, interaction_request)
                except Exception as email_error:
                    logger.error(f"❌ Failed to send negative feedback notification: {email_error}")
            
            logger.info(f"✅ Interaction updated successfully with feedback: {interaction_request.interaction_id}")
            
            return AIInteractionResponse(
                interaction_id=interaction_request.interaction_id,
                status="updated",
                message="Interaction updated with feedback successfully",
                timestamp=timestamp,
                service_name=interaction_request.service_name,
                has_feedback=True
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating interaction with feedback: {e}")
            raise RuntimeError(f"Failed to update interaction: {str(e)}")


    def get_interaction_summary(
        self, 
        service_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> InteractionSummary:
        """
        Get summary statistics for interaction data.
        
        Args:
            service_name: Optional filter by service name
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            InteractionSummary with statistics
        """
        try:
            logger.info(f"📊 Generating interaction summary...")
            logger.info(f"🔍 Service filter: {service_name or 'All services'}")
            logger.info(f"📅 Date range: {start_date} to {end_date}")
            
            all_interactions = self._read_interactions_from_dynamodb(
                service_name=service_name,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"📊 Found {len(all_interactions)} interaction entries for analysis")
            
            services_breakdown = {}
            total_positive = 0
            total_negative = 0
            total_interactions = len(all_interactions)
            interactions_with_feedback = 0
            response_times = []
            recent_interactions = []
            
            if service_name:
                services_breakdown[service_name] = {
                    "total_interactions": 0,
                    "positive": 0, 
                    "negative": 0,
                    "no_feedback": 0
                }
            else:
                for service in self.registered_services.keys():
                    services_breakdown[service] = {
                        "total_interactions": 0,
                        "positive": 0, 
                        "negative": 0,
                        "no_feedback": 0
                    }

            for interaction in all_interactions:
                service = interaction.get('service_name', 'unknown')
                
                # Initialize service breakdown if not exists
                if service not in services_breakdown:
                    services_breakdown[service] = {
                        "total_interactions": 0,
                        "positive": 0, 
                        "negative": 0,
                        "no_feedback": 0
                    }
                
                services_breakdown[service]["total_interactions"] += 1
                
                # Count feedback
                has_feedback = interaction.get('has_feedback', False)
                if has_feedback:
                    interactions_with_feedback += 1
                    feedback_type = interaction.get('feedback_type', '').lower()
                    if feedback_type in ['positive', 'like', 'thumbs_up', 'good']:
                        total_positive += 1
                        services_breakdown[service]["positive"] += 1
                    elif feedback_type in ['negative', 'dislike', 'thumbs_down', 'bad']:
                        total_negative += 1
                        services_breakdown[service]["negative"] += 1
                else:
                    services_breakdown[service]["no_feedback"] += 1

                response_time = interaction.get('response_time_seconds')
                if response_time is not None:
                    if isinstance(response_time, Decimal):
                        response_time = float(response_time)
                    response_times.append(response_time)

                if len(recent_interactions) < 10:
                    feedback_comment = interaction.get('feedback_comment', '')

                    recent_interactions.append({
                        'interaction_id': interaction.get('interaction_id'),
                        'service_name': service,
                        'feedback_type': interaction.get('feedback_type'),
                        'timestamp': interaction.get('timestamp'),
                        'user_id': interaction.get('user_id'),
                        'has_feedback': has_feedback,
                        'has_comment': bool(feedback_comment and str(feedback_comment).strip())
                    })
            
            # Calculate rates
            feedback_rate = (interactions_with_feedback / total_interactions * 100) if total_interactions > 0 else 0.0
            satisfaction_rate = (total_positive / interactions_with_feedback * 100) if interactions_with_feedback > 0 else 0.0
            average_response_time = sum(response_times) / len(response_times) if response_times else None
            
            recent_interactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            summary = InteractionSummary(
                service_name=service_name,
                total_interactions=total_interactions,
                interactions_with_feedback=interactions_with_feedback,
                positive_feedback=total_positive,
                negative_feedback=total_negative,
                feedback_rate=round(feedback_rate, 2),
                satisfaction_rate=round(satisfaction_rate, 2),
                average_response_time=round(average_response_time, 2) if average_response_time else None,
                services_breakdown=services_breakdown,
                recent_interactions=recent_interactions[:10],
                time_period={
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            )
            
            logger.info(f"✅ Interaction summary generated: {total_interactions} total interactions, {feedback_rate:.1f}% feedback rate, {satisfaction_rate:.1f}% satisfaction")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating interaction summary: {e}")
            raise RuntimeError(f"Failed to generate interaction summary: {str(e)}")
    

    def get_interactions(self, request: GetInteractionRequest) -> Tuple[List[Dict[str, Any]], int]:
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
            
            request = GetInteractionRequest(service_name=service_name, limit=limit)
            feedback_entries, _ = self.get_interactions(request)
            
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
        Register a new AI service for interaction tracking.
        
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
    
    
    def _create_interaction_record(
        self, 
        interaction_id: str, 
        timestamp: datetime, 
        request: AIInteractionRequest,
        service_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive interaction record."""
        
        input_length = len(request.user_input) if request.user_input else 0
        output_length = len(request.ai_output) if request.ai_output else 0
        comment_length = len(request.feedback_comment) if request.feedback_comment else 0
        has_feedback = request.feedback_type is not None
        
        record = {
            # Primary keys
            "interaction_id": interaction_id,
            "service_name": request.service_name,
            "timestamp": timestamp.isoformat(),
            
            # Feedback data (optional)
            "feedback_type": request.feedback_type,
            "feedback_comment": request.feedback_comment,
            "has_feedback": has_feedback,
            "has_comment": request.feedback_comment is not None,
            
            # User and session data
            "user_id": request.user_id,
            "session_id": request.session_id,
            "platform": request.platform,
            
            # Service metadata
            "service_display_name": service_info["name"],
            "service_description": service_info["description"],
            
            # AI interaction data
            "user_input": request.user_input,
            "ai_output": request.ai_output,
            "input_length": input_length,
            "output_length": output_length,
            
            # Performance data
            "response_time_seconds": request.response_time_seconds,
            
            # Context data
            "context": request.context,
            
            # Metadata
            "metadata": {
                "comment_length": comment_length,
                "has_session": request.session_id is not None,
                "has_performance_data": request.response_time_seconds is not None,
                "context_fields": list(request.context.keys()) if request.context else [],
                "is_update": request.update_mode or False
            }
        }
        
        # Add feedback timestamp if this has feedback
        if has_feedback:
            record["feedback_timestamp"] = timestamp.isoformat()
        
        return record
    

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
    

    def _save_interaction_to_dynamodb(self, interaction_record: Dict[str, Any]) -> None:
        """Save interaction record to DynamoDB."""
        try:
            cleaned_record = self._clean_record_for_dynamodb(interaction_record)
            
            self.table.put_item(Item=cleaned_record)
            
            logger.info(f"✅ Interaction saved to DynamoDB: {interaction_record['interaction_id']}")
            
        except Exception as e:
            logger.error(f"❌ Error saving interaction to DynamoDB: {e}")
            raise
    

    def _read_feedback_from_dynamodb(
        self, 
        service_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read interaction data from the single DynamoDB table.
        
        Args:
            service_name: Optional filter by service name
            start_date: Optional start date filter
            end_date: Optional end_date filter
            
        Returns:
            List of interaction records
        """
        return self._read_interactions_from_dynamodb(service_name, start_date, end_date)
    

    def _read_interactions_from_dynamodb(
        self, 
        service_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Read interaction data from the single DynamoDB table.
        
        Args:
            service_name: Optional filter by service name
            start_date: Optional start date filter
            end_date: Optional end_date filter
            
        Returns:
            List of interaction records
        """
        try:
            logger.info(f"📊 Reading interactions from table: {self.table_name}")
            
            # Build filter expressions
            filter_expressions = []
            
            if service_name:
                filter_expressions.append(Attr('service_name').eq(service_name))
            
            if start_date:
                start_str = start_date.isoformat()
                filter_expressions.append(Attr('timestamp').gte(start_str))
            
            if end_date:
                end_str = end_date.isoformat()
                filter_expressions.append(Attr('timestamp').lte(end_str))
            
            # Combine filter expressions
            filter_expression = None
            if filter_expressions:
                filter_expression = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    filter_expression = filter_expression & expr
            
            # Scan the table
            scan_kwargs = {}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_kwargs)
            all_interactions = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = self.table.scan(**scan_kwargs)
                all_interactions.extend(response.get('Items', []))
            
            logger.info(f"📊 Retrieved {len(all_interactions)} interaction entries from single table")
            return all_interactions
            
        except Exception as e:
            logger.error(f"❌ Error reading interactions from DynamoDB: {e}")
            return []
    

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


    def _send_negative_feedback_notification(self, interaction_record: Dict[str, Any], interaction_request: AIInteractionRequest) -> None:
        """
        Send email notification for negative feedback using the email microservice.
        
        Args:
            interaction_record: The complete interaction record
            interaction_request: The original interaction request
        """
        try:            
            logger.info(f"📧 Sending negative feedback notification for: {interaction_record['interaction_id']}")
            
            email_data = {
                'interaction_id': interaction_record['interaction_id'],
                'feedback_type': interaction_record['feedback_type'],
                'feedback_comment': interaction_record.get('feedback_comment', 'No comment provided'),
                'user_id': interaction_record['user_id'],
                'service_name': interaction_record['service_name'],
                'service_display_name': interaction_record['service_display_name'],
                'timestamp': interaction_record['timestamp'],
                'user_input': interaction_record.get('user_input', ''),
                'ai_output': interaction_record.get('ai_output', ''),
                'session_id': interaction_record.get('session_id', ''),
                'platform': interaction_record.get('platform', ''),
                'response_time_seconds': interaction_record.get('response_time_seconds', 0),
                'context': interaction_record.get('context', {})
            }
            
            send_negative_feedback_email(email_data)
            
            logger.info(f"✅ Negative feedback notification sent successfully")
            
        except Exception as e:
            logger.error(f"❌ Error sending negative feedback notification: {e}")
            raise


# Global interaction service instance
ai_interaction_service = AIInteractionService()