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

import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple

from app.utils.logger.logger_util import get_logger
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3
from app.api.models import (FeedbackRequest, FeedbackResponse, FeedbackSummary, GetFeedbackRequest)

logger = get_logger()


class AIFeedbackService:
    """
    General feedback service for AI services.
    
    This service provides comprehensive feedback management capabilities
    for any AI service that generates user-facing content. It supports:
    
    - Multi-service feedback collection
    - Flexible metadata storage
    - Service-specific analytics
    - Scalable storage architecture
    - Future database migration support
    """
    

    def __init__(self):
        """Initialize the AI feedback service."""
        self.local_feedback_dir = Path("feedback_logs")
        self.local_feedback_dir.mkdir(exist_ok=True)
        self.s3_feedback_prefix = "ai-feedback"
        
        self.registered_services = {}
        
        self.register_service(
            service_name="chatbot",
            display_name="AICCRA Chatbot",
            description="Conversational AI for AICCRA data exploration",
            expected_context=["filters_applied"]
        )
        
        logger.info("🚀 AI Feedback Service initialized with multi-service support")
    

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
            
            feedback_record = self._create_feedback_record(
                feedback_id, timestamp, feedback_request, service_info
            )
            
            self._save_feedback_record(feedback_record, timestamp, feedback_request.service_name)
            
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
            
            # TODO: Replace with actual S3/DynamoDB queries when implemented
            # For now, return structured mock data based on registered services
            
            services_breakdown = {}
            total_positive = 0
            total_negative = 0
            
            if service_name:
                services_breakdown[service_name] = {"positive": 0, "negative": 0}
            else:
                for service in self.registered_services.keys():
                    services_breakdown[service] = {"positive": 0, "negative": 0}
            
            total_feedback = total_positive + total_negative
            satisfaction_rate = (total_positive / total_feedback * 100) if total_feedback > 0 else 0.0
            
            summary = FeedbackSummary(
                service_name=service_name,
                total_feedback=total_feedback,
                positive_feedback=total_positive,
                negative_feedback=total_negative,
                satisfaction_rate=satisfaction_rate,
                average_response_time=None,
                services_breakdown=services_breakdown,
                recent_feedback=[],
                time_period={
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            
            logger.info(f"✅ Feedback summary generated: {total_feedback} total entries")
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
            
            # TODO: Replace with actual S3/DynamoDB queries when implemented
            # For now, return empty results with proper structure
            feedback_entries = []
            total_count = 0
            
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
            service_info = {
                "name": service_name.replace("-", " ").replace("_", " ").title(),
                "description": f"AI service: {service_name}",
                "expected_context": []
            }
            self.registered_services[service_name] = service_info
            return service_info
    

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
    

    def _save_feedback_record(
        self, 
        feedback_record: Dict[str, Any], 
        timestamp: datetime, 
        service_name: str
    ) -> None:
        """Save feedback record to local file and S3."""
        
        feedback_uuid = feedback_record['feedback_id'][:11]
        filename = f"feedback_{service_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{feedback_uuid}.json"
        local_path = self.local_feedback_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_record, f, indent=2, ensure_ascii=False)
        
        s3_key = f"{self.s3_feedback_prefix}/{service_name}/{timestamp.strftime('%Y%m%d')}/{filename}"
        upload_file_to_s3(s3_key, str(local_path))
        
        try:
            os.remove(local_path)
            logger.info(f"📤 Feedback saved to S3: {s3_key}")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove local file {local_path}: {e}")


# Global feedback service instance
ai_feedback_service = AIFeedbackService()