"""Canonical contract between this worker and the QA API (onecgiar_qa).

Published as JSON Schema in ``contract/schema/`` (see ``scripts/export_schemas.py``) so the
NestJS side can validate its copy in a contract test.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

Signal = Literal["green", "amber", "red"]

UnavailableReason = Literal[
    "no_readable_evidence",
    "private_link",
    "model_declined",
    "invalid_output",
    "no_criteria_for_field",
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
    explanation: str
    evidenceQuote: str
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
    Union[AvailableSuggestionView, UnavailableSuggestionView, PendingSuggestionView],
    Field(discriminator="status"),
]
"""One item of ``GET /results/:code/snapshots/:snapKey/ai-suggestions`` (served by the QA API).

A user whose only role on the result is PPU gets 403 and no body.
"""


class AiSuggestionEvent(_Strict):
    """``POST /ai-suggestions/:suggestionId/events``. Whether the comment was edited is computed server-side."""

    action: Literal["shown", "copied", "comment_saved"]
    commentId: str | None = None
