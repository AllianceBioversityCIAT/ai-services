"""Shared models for LLM provider invocations."""

from pydantic import BaseModel


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ModelInvocationResult(BaseModel):
    text: str
    usage: ModelUsage
    stop_reason: str
    model_id: str
    duration_seconds: float


class ModelInvocationError(Exception):
    """Raised when a Bedrock (or other) model invocation fails."""

    category: str = "model_extraction"
    http_status: int = 502

    def __init__(self, message: str):
        super().__init__(message)
