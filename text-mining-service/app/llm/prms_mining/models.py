"""Internal domain models and exceptions for PRMS multisource mining."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from app.llm.shared.models import ModelInvocationError, ModelInvocationResult, ModelUsage


__all__ = [
    "PrmsSourceType",
    "PrmsSource",
    "ExtractedPrmsSource",
    "ModelUsage",
    "ModelInvocationResult",
    "ModelInvocationError",
    "PrmsMiningError",
    "EmptySourceSetError",
    "SourceLimitExceededError",
    "UnsupportedSourceTypeError",
    "SourceDownloadError",
    "SourceExtractionError",
    "AudioTranscriptionUnavailableError",
    "ModelOutputValidationError",
    "FieldMappingError",
    "SourceCounts",
    "StageDurations",
    "RETRIEVAL_QUERY_VERSION",
    "RETRIEVAL_QUERY",
    "SUPPORTED_INDICATORS",
]


class PrmsSourceType(str, Enum):
    DOCUMENT = "document"
    FREE_TEXT = "free_text"
    AUDIO = "audio"


class PrmsSource(BaseModel):
    source_id: str
    source_index: int
    source_type: PrmsSourceType
    bucket_name: Optional[str] = None
    object_key: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    text: Optional[str] = None


class ExtractedPrmsSource(BaseModel):
    source_id: str
    source_index: int
    source_type: PrmsSourceType
    content: str
    segments: list[str]
    page_count: Optional[int] = None
    character_count: int
    extraction_seconds: float
    file_name: Optional[str] = None
    eligible_as_formal_evidence: bool = False


class PrmsMiningError(Exception):
    """Base PRMS mining error with a stable category for notifications."""

    category: str = "unknown"
    http_status: int = 500

    def __init__(self, message: str, *, source_id: str | None = None):
        super().__init__(message)
        self.source_id = source_id


class EmptySourceSetError(PrmsMiningError):
    category = "validation"
    http_status = 400


class SourceLimitExceededError(PrmsMiningError):
    category = "validation"
    http_status = 413


class UnsupportedSourceTypeError(PrmsMiningError):
    category = "validation"
    http_status = 415


class SourceDownloadError(PrmsMiningError):
    category = "extraction"
    http_status = 422


class SourceExtractionError(PrmsMiningError):
    category = "extraction"
    http_status = 422


class AudioTranscriptionUnavailableError(PrmsMiningError):
    category = "extraction"
    http_status = 503


class ModelOutputValidationError(PrmsMiningError):
    category = "final_validation"
    http_status = 502


class FieldMappingError(PrmsMiningError):
    category = "mapping"
    http_status = 500


class SourceCounts(BaseModel):
    document: int = 0
    free_text: int = 0
    audio: int = 0

    def total(self) -> int:
        return self.document + self.free_text + self.audio


class StageDurations(BaseModel):
    source_extraction: float = 0.0
    slowest_source_extraction: float = 0.0
    chunking: float = 0.0
    embedding: float = 0.0
    retrieval: float = 0.0
    model_extraction: float = 0.0
    final_validation: float = 0.0
    field_mapping: float = 0.0
    total: float = 0.0


RETRIEVAL_QUERY_VERSION = "prms-retrieval-v1"
RETRIEVAL_QUERY = (
    "CGIAR PRMS bilateral results: Capacity Sharing for Development, Policy Change, "
    "Innovation Development, Innovation Use, Other Output, Other Outcome. "
    "Extract training, policy, innovation, adoption, output, and outcome evidence."
)

SUPPORTED_INDICATORS = [
    "Capacity Sharing for Development",
    "Policy Change",
    "Innovation Development",
    "Innovation Use",
    "Other Output",
    "Other Outcome",
]
