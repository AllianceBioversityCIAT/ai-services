"""REST API endpoints for AICCRA Chatbot Service."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import time
from typing import Iterator

from app.api.models import ChatRequest, ChatResponse, ErrorResponse
from app.utils.logger.logger_util import get_logger

logger = get_logger()

router = APIRouter()


def _get_chatbot_agent():
    """Lazy import of chatbot agent function to avoid initialization issues."""
    try:
        from app.llm.agents import run_agent_chatbot
        return run_agent_chatbot
    except Exception as e:
        logger.error(f"Failed to import chatbot agent: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Chatbot service configuration error",
                "details": "AWS Bedrock Agents service is not properly configured. Please check AWS credentials and configuration.",
                "status": "error"
            }
        )


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Chat with AICCRA AI Assistant",
    description="""
    🤖 Interactive Chat with AICCRA AI Assistant
    
    Send a message to the AICCRA AI chatbot and receive intelligent responses based on
    comprehensive AICCRA data including deliverables, contributions, innovations, and outcomes.
    
    🧠 How It Works
    
    1. **Message Processing**: Your question is analyzed for intent and context
    2. **Smart Filtering**: Optional filters are applied to focus on specific data subsets
    3. **Vector Search**: Relevant information is retrieved from the knowledge base
    4. **AI Generation**: AWS Bedrock Claude 3.7 Sonnet generates a contextual response
    5. **Memory Integration**: Session memory enables follow-up questions and context retention
    
    💬 Conversation Features
    
    - **Session Management**: Requires a unique session_id for each conversation to maintain context
    - **User Identification**: Requires the user's email address (memory_id) for personalized access
    - **Context-Aware**: Builds upon previous questions for comprehensive answers
    - **Smart Filtering**: Use filters to focus on specific phases, indicators, or sections
    - **Rich Citations**: Responses include links to relevant documents and reports
    - **Multi-Language**: Supports questions in multiple languages
    
    🎯 What You Can Ask
    
    **Progress Tracking**
    - "What progress has been made on IPI 1.1 in 2025?"
    - "How are the clusters performing against their targets?"
    - "Show me achievements for PDO Indicator 3"
    
    **Research & Deliverables**
    - "What publications were released by the Kenya cluster?"
    - "Show me deliverables related to climate information services"
    - "What research outputs are available for Theme 2?"
    
    **Innovations & Technology**
    - "What innovations were developed for climate-smart agriculture?"
    - "Show me tools created for early warning systems"
    - "What is the readiness level of AICCRA innovations?"
    
    **Impact & Outcomes**
    - "What real-world impacts has AICCRA achieved?"
    - "Show me outcome case reports from Western Africa"
    - "How has AICCRA contributed to farmer livelihoods?"
    
    🔧 Filtering Options
    
    Use optional filters to focus your queries:
    
    - **Phase**: Target specific reporting periods (AWPB, Progress, AR)
    - **Indicator**: Focus on specific performance indicators (IPI, PDO)
    - **Section**: Limit to specific data types (Deliverables, Innovations, etc.)
    
    ⚡ Performance Notes
    
    - **Initial Response**: ~3-5 seconds for new sessions
    - **Follow-up Questions**: ~2-3 seconds with conversation memory
    - **Complex Queries**: May take longer for comprehensive analysis
    
    📋 Example Usage
    
    ```bash
    curl -X POST "http://localhost:8000/api/chat" \\
         -H "Content-Type: application/json" \\
         -d '{
           "message": "What progress has been made on IPI 1.1 in 2025?",
           "phase": "Progress 2025",
           "indicator": "IPI 1.1",
           "section": "All sections",
           "session_id": "550e8400-e29b-41d4-a716-446655440000",
           "memory_id": "researcher@cgiar.org"
         }'
    ```
    
    ⚠️ **Important**: 
    - `session_id`: Unique identifier for each conversation session (e.g., UUID)
    - `memory_id`: User's email address for personalized knowledge base access
    """,
    response_description="Successfully processed chat message with AI-generated response",
    responses={
        200: {
            "description": "Chat message processed successfully",
            "model": ChatResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Based on the latest data, AICCRA has achieved significant progress on IPI 1.1 in 2025. The **Western Africa** cluster has contributed 45% of the total achievements, with 850 out of 1200 farmers trained representing 71% progress...",
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filters_applied": {
                            "phase": "Progress 2025",
                            "indicator": "IPI 1.1",
                            "section": "All sections"
                        },
                        "status": "success"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request parameters (validation error)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid request parameters",
                        "details": "Message cannot be empty",
                        "status": "error"
                    }
                }
            }
        },
        403: {
            "description": "Access denied (authentication/authorization error)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Access denied",
                        "details": "AWS Bedrock service access denied",
                        "status": "error"
                    }
                }
            }
        },
        422: {
            "description": "Validation error in request body",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation error",
                        "details": "User email (memory_id) is required and cannot be empty",
                        "status": "error"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Chatbot service error",
                        "details": "AWS Bedrock service temporarily unavailable",
                        "status": "error"
                    }
                }
            }
        }
    }
)
async def chat_with_assistant(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the AICCRA AI chatbot and receive an intelligent response.
    
    - message: Your question or message to the chatbot
    - phase: Optional filter for reporting phase (default: "All phases")
    - indicator: Optional filter for performance indicator (default: "All indicators")  
    - section: Optional filter for data section (default: "All sections")
    - session_id: Required unique session identifier for conversation continuity
    - memory_id: Required user email address for personalized knowledge base access
    
    Returns an AI-generated response with citations and relevant information.
    """
    start_time = time.time()
    
    try:
        logger.info(f"🤖 Processing chat message: {request.message[:100]}...")
        logger.info(f"🔗 Session ID: {request.session_id}")
        logger.info(f"👤 User Email: {request.memory_id}")
        
        # Lazy import the chatbot agent function
        run_agent_chatbot = _get_chatbot_agent()
        
        # Call the chatbot agent function
        logger.info("🔍 Executing chatbot agent...")
        response_stream = run_agent_chatbot(
            user_input=request.message,
            phase=request.phase,
            indicator=request.indicator,
            section=request.section,
            session_id=request.session_id,
            memory_id=request.memory_id
        )
        
        # Collect the streaming response into a single string
        full_response = ""
        for chunk in response_stream:
            full_response += chunk

        # Calculate processing time
        processing_time = round(time.time() - start_time, 2)
        
        logger.info(f"✅ Successfully processed chat message in {processing_time}s")
        
        return ChatResponse(
            message=full_response,
            session_id=request.session_id,
            filters_applied={
                "phase": request.phase,
                "indicator": request.indicator,
                "section": request.section
            },
            status="success"
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid request parameters", 
                "details": str(e), 
                "status": "error"
            }
        )
    except PermissionError as e:
        logger.error(f"Permission error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Access denied", 
                "details": str(e), 
                "status": "error"
            }
        )
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        # Check if it's a context limit error
        if "context limit" in str(e).lower() or "input is too long" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Message too complex", 
                    "details": "Your query is too complex. Please try a shorter, more specific question or start a new session.", 
                    "status": "error"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Chatbot service error", 
                    "details": str(e), 
                    "status": "error"
                }
            )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error", 
                "details": str(e), 
                "status": "error"
            }
        )