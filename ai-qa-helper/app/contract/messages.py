"""Canonical contract between this worker and the QA API (onecgiar_qa).

Published as JSON Schema in ``contract/schema/`` (see ``scripts/export_schemas.py``) so the
NestJS side can validate its copy in a contract test.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Signal = Literal["green", "amber", "red"]

UnavailableReason = Literal[
    "no_readable_evidence",
    "private_link",
    "model_declined",
    "invalid_output",
    "no_criteria_for_field",
    "no_supporting_quote",
    "out_of_scope_funding",
    "failed",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AiJobMessage(_Strict):
    """SQS message: one job per (snapshot, AI-input field). Produced by the QA API sync hook."""

    runId: str = Field(min_length=1)
    resultCode: str = Field(min_length=1)
    snapKey: str = Field(min_length=1)
    fieldKey: str = Field(min_length=1)
    promptVersion: str = Field(min_length=1)


class AvailableSuggestionView(_Strict):
    status: Literal["available"]
    fieldKey: str
    suggestionId: str
    signal: Signal
    suggestedValue: int = Field(ge=0, le=9)
    """Level on the field's scale: Impact Areas 0-2, IRL/IUL 0-9 (level number, not a catalog id)."""
    explanation: str
    evidenceQuote: str
    """For IRL/IUL always non-empty and found verbatim in the evidence (else the field is unavailable)."""
    quoteVerified: bool
    evidenceSource: str | None
    promptVersion: str
    modelId: str
    # Present only for the TPB role.
    copiedByReviewer: bool | None = None
    editedByReviewer: bool | None = None


class UnavailableSuggestionView(_Strict):
    status: Literal["unavailable"]
    fieldKey: str
    unavailableReason: UnavailableReason


class PendingSuggestionView(_Strict):
    status: Literal["pending"]
    fieldKey: str


AiSuggestionView = Annotated[
    AvailableSuggestionView | UnavailableSuggestionView | PendingSuggestionView,
    Field(discriminator="status"),
]
"""One item of ``GET /results/:code/snapshots/:snapKey/ai-suggestions`` (served by the QA API).

A user whose only role on the result is PPU gets 403 and no body.
"""


class AiUsageEvent(_Strict):
    """Copy/comment usage. Whether the comment was edited is computed server-side."""

    action: Literal["shown", "copied", "comment_saved"]
    commentId: str | None = None


class AiValidatedAboveEvent(_Strict):
    """The assessor validated a level at least 2 above the AI's level (IRL/IUL).

    Requires ``validatedLevel - aiLevel >= 2`` (JSON Schema cannot express it: the API must check it,
    and that ``aiLevel`` equals the suggestion's stored ``suggestedValue``). Measures the AI only (AC9):
    never aggregated per reviewer.
    """

    action: Literal["validated_above_ai"]
    aiLevel: int = Field(ge=0, le=9)
    validatedLevel: int = Field(ge=0, le=9)
    reason: str = Field(min_length=1, max_length=200, pattern=r"^[^\r\n]+$")
    """One line, at most 200 characters."""

    @model_validator(mode="after")
    def _at_least_two_above(self) -> "AiValidatedAboveEvent":
        if self.validatedLevel - self.aiLevel < 2:
            raise ValueError("validatedLevel must be at least 2 above aiLevel")
        return self


AiSuggestionEvent = Annotated[AiUsageEvent | AiValidatedAboveEvent, Field(discriminator="action")]
"""``POST /ai-suggestions/:suggestionId/events``."""
