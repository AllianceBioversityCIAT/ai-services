"""REST API endpoints for Fast Response Service."""

import traceback
from app.llm.mining import return_response
from app.utils.logger.logger_util import get_logger
from fastapi import APIRouter, HTTPException, status
from app.api.models import FastRequest, FastResponse, ErrorResponse

logger = get_logger()
router = APIRouter()


@router.post(
    "/api/fast-response",
    response_model=FastResponse,
    tags=["Fast Responses"],
    summary="Generate a fast response",
    description="""
    ⚡ Generate a fast response using a language model (LLM).

    Send a prompt and input text, and receive an AI-generated response.
    Example use cases:
    - Summarize texts
    - Improve writing
    - Rewrite content
    - Generate automatic replies

    Example usage:
    ```bash
    curl -X POST "http://localhost:8000/api/fast-response" \\
         -H "Content-Type: application/json" \\
         -d '{
           "prompt": "Summarize the following text in 3 lines.",
           "input_text": "Sustainable agriculture is key for rural development..."
         }'
    ```
    """,
    response_description="Successfully generated response",
    responses={
        200: {
            "description": "Successfully generated response",
            "model": FastResponse,
            "content": {
                "application/json": {
                    "example": {
                        "prompt": "Summarize the following text in 3 lines.",
                        "input_text": "Sustainable agriculture is key for rural development...",
                        "output": "Sustainable agriculture drives rural development, improves productivity, and protects the environment.",
                        "status": "success"
                    }
                }
            }
        },
        400: {
            "description": "Invalid parameters",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid parameters",
                        "status": "error"
                    }
                }
            }
        },
        500: {
            "description": "Internal error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Internal error",
                        "status": "error"
                    }
                }
            }
        }
    }
)
async def fast_response(request: FastRequest) -> FastResponse:
    """
    Generate a fast response using an LLM.
    - prompt: Instruction for the AI (e.g., "Summarize the text", "Improve the writing", etc.)
    - input_text: Text to apply the prompt to.
    """
    try:
        logger.info(f"⚡ Generating fast response for prompt: {request.prompt[:50]}...")
        logger.debug(f"Full request: prompt='{request.prompt}', input_text length={len(request.input_text)}")
        
        # Validation
        if not request.prompt.strip():
            raise ValueError("Prompt cannot be empty")
        if not request.input_text.strip():
            raise ValueError("Input text cannot be empty")
        
        output = return_response(request.prompt, request.input_text)
        
        logger.info("✅ Fast response generated successfully")
        return FastResponse(
            prompt=request.prompt,
            input_text=request.input_text,
            output=output,
            status="success"
        )
    
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid parameters", "details": str(e), "status": "error"}
        )
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal error", "details": str(e), "status": "error"}
        )