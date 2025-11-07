"""
Utility functions for handling user feedback on AI responses.
"""

import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path

from app.utils.logger.logger_util import get_logger
from app.utils.s3.upload_file_to_s3 import upload_file_to_s3
from app.api.models import FeedbackRequest, FeedbackResponse

logger = get_logger()


def submit_feedback(feedback_request: FeedbackRequest) -> FeedbackResponse:
    """
    Submit user feedback for an AI response.
    
    Args:
        feedback_request: The feedback data to store
        
    Returns:
        FeedbackResponse with confirmation details
    """
    try:
        # Generate unique feedback ID
        feedback_id = f"fb_{uuid.uuid4()}"
        timestamp = datetime.now(timezone.utc)
        
        # Create comprehensive feedback record
        feedback_record = {
            "feedback_id": feedback_id,
            "timestamp": timestamp.isoformat(),
            "session_id": feedback_request.session_id,
            "memory_id": feedback_request.memory_id,
            "user_message": feedback_request.user_message,
            "ai_response": feedback_request.ai_response,
            "feedback_type": feedback_request.feedback_type,
            "feedback_comment": feedback_request.feedback_comment,
            "service_name": feedback_request.service_name,
            "filters_applied": feedback_request.filters_applied,
            "metadata": {
                "response_length": len(feedback_request.ai_response),
                "has_comment": feedback_request.feedback_comment is not None,
                "comment_length": len(feedback_request.feedback_comment) if feedback_request.feedback_comment else 0,
                "date": timestamp.strftime("%Y-%m-%d"),
                "hour": timestamp.strftime("%H")
            }
        }
        
        # Save to local file first
        local_feedback_dir = Path("chat_logs")
        local_feedback_dir.mkdir(exist_ok=True)
        
        filename = f"feedback_{timestamp.strftime('%H%M%S')}_{feedback_id[:11]}.json"
        local_path = local_feedback_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_record, f, indent=2, ensure_ascii=False)
        
        # Upload to S3
        s3_key = f"aiccra/chatbot/feedback/{timestamp.strftime('%Y%m%d')}/{filename}"
        upload_file_to_s3(s3_key, str(local_path))
        
        # Clean up local file
        os.remove(local_path)
        
        logger.info(f"✅ Feedback submitted successfully: {feedback_id}")
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            status="success",
            message="Feedback submitted successfully. Thank you for helping us improve!",
            timestamp=timestamp
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting feedback: {e}")
        raise RuntimeError(f"Failed to submit feedback: {str(e)}")