"""LlmProvider port. The worker depends on this, never on a concrete SDK."""

from dataclasses import dataclass, field
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

Effort = Literal["low", "medium", "high"]
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class TextEvidence:
    source_index: int
    label: str
    text: str


@dataclass(frozen=True)
class PdfEvidence:
    """OCR fallback: a PDF without a text layer, sent to the model as a document block."""

    source_index: int
    label: str
    data_base64: str


EvidencePart = TextEvidence | PdfEvidence


@dataclass(frozen=True)
class SuggestionRequest(Generic[OutputT]):
    system_prefix: str
    """Fixed prefix (rubric + guide). Identical across calls of a field so it can be cached."""
    task: str
    """Variable part: field, reported value, result context."""
    evidence: list[EvidencePart]
    output_model: type[OutputT]
    effort: Effort
    max_tokens: int


@dataclass(frozen=True)
class LlmUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass(frozen=True)
class SuggestionResult(Generic[OutputT]):
    kind: Literal["ok", "refusal", "truncated", "invalid_output"]
    model_id: str
    usage: LlmUsage = field(default_factory=LlmUsage)
    output: OutputT | None = None


class RetryableLlmError(Exception):
    """Errors worth retrying (throttling, 5xx, connection). Anything else is terminal."""

    def __init__(self, message: str, status: int | None):
        super().__init__(message)
        self.status = status


class LlmProvider(Protocol):
    def suggest(self, request: SuggestionRequest[OutputT]) -> SuggestionResult[OutputT]: ...
