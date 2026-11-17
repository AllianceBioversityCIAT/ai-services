"""Canonical contract between this worker and the QA API (onecgiar_qa).

Published as JSON Schema in ``contract/schema/`` (see ``scripts/export_schemas.py``) so the
NestJS side can validate its copy in a contract test.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "2.0.1"
"""2.0.1 (2026-11-17): ``suggestionId`` pattern (32 lowercase hex, no hyphens).
2.0.0 (2026-11-17): indicative fields (result category, innovation use numbers), ``valueKind``,
typed ``suggestedValue``, ``coversFieldKeys`` and signal ``indicative``. 1.x had levels only."""

SuggestionId = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
"""uuid5 of ``pk|sk`` as 32 lowercase hex characters (QA stores it as char(32))."""

Signal = Literal["green", "amber", "red", "indicative"]
"""green/amber/red: scored fields (Impact Areas, IRL, IUL). indicative: no colour, the value is shown
for reference only (result category, innovation use numbers)."""

ValueKind = Literal["level", "category", "use_numbers"]

ResultCategory = Literal[
    "Innovation",
    "Knowledge Product",
    "Capacity Sharing for Development",
    "Routine Activity",
    "Other",
]
"""Prompt 06 output: ``is_innovation`` True -> "Innovation", else ``predicted_category_if_not``."""

Level = Annotated[int, Field(ge=0, le=9)]

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
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)


class UseNumberRow(_Strict):
    """One user group of prompt 09 (Innovation Use Numbers v3), keys exactly as the prompt returns them."""

    user: str
    user_type: str
    user_subtype: str | None
    quantity: int | float
    women: int | float | None
    youth_women: int | float | None
    non_youth_women: int | float | None
    men: int | float | None
    youth_men: int | float | None
    non_youth_men: int | float | None
    geolocation: str | None
    other_quantitative_measures: str | None


SuggestedValue = Level | ResultCategory | list[UseNumberRow]
"""level: 0-9 (Impact Areas 0-2); category: ResultCategory; use_numbers: list of rows (may be empty)."""


def check_value_kind(kind: ValueKind | None, value: object) -> None:
    ok = {
        "level": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "category": lambda v: isinstance(v, str),
        "use_numbers": lambda v: isinstance(v, list),
    }
    if kind is not None and value is not None and not ok[kind](value):
        raise ValueError(f"suggestedValue does not match valueKind {kind!r}")


class AiJobMessage(_Strict):
    """SQS message: one job per (snapshot, AI-input field). Produced by the QA API sync hook."""

    runId: str = Field(min_length=1)
    resultCode: str = Field(min_length=1)
    snapKey: str = Field(min_length=1)
    fieldKey: str = Field(min_length=1)
    promptVersion: str = Field(min_length=1)


class AvailableSuggestionView(_Strict):
    """A suggestion the assessor can see.

    Scored fields (Impact Areas, IRL, IUL): ``signal`` green/amber/red, ``valueKind`` "level",
    ``suggestedValue`` the level, ``evidenceQuote`` the supporting passage.

    Indicative fields: ``signal`` "indicative" (no colour), no ``evidenceQuote`` (prompts 06 and 09 are
    used verbatim and ask the model not to quote), and ``suggestedValue`` always present:
      - ``general.result_type``: ``valueKind`` "category", one of ResultCategory ("Innovation" or the
        alternative category prompt 06 predicts);
      - ``innovation_use.current_use.actors``: ``valueKind`` "use_numbers", the list of user groups of
        prompt 09 (``user`` "actors" | "organizations" | "other type" -> the catalog lists actors,
        organizations and measures; ``user_type``/``user_subtype`` the actor or institution type; the
        quantity and sex/age disaggregation). An empty list means the evidence reports no use numbers.
        ``coversFieldKeys`` lists organizations and measures: the chip says it covers actors,
        organizations and measures.
    """
    status: Literal["available"]
    fieldKey: str
    suggestionId: SuggestionId
    signal: Signal
    """``indicative`` exactly when the field is indicative (result category, innovation use numbers)."""
    valueKind: ValueKind
    suggestedValue: SuggestedValue
    """level: on the field's scale, Impact Areas 0-2, IRL/IUL 0-9 (level number, not a catalog id)."""
    explanation: str
    evidenceQuote: str | None = None
    """For IRL/IUL always non-empty and found verbatim in the evidence (else the field is unavailable).
    Indicative fields have none: their prompts (06, 09) ask the model not to quote."""
    quoteVerified: bool
    coversFieldKeys: list[str] | None = None
    """Set when one suggestion covers several catalog fields. Innovation use numbers is stored under
    ``innovation_use.current_use.actors`` and covers actors, organizations and measures."""
    evidenceSource: str | None
    promptVersion: str
    modelId: str
    # Present only for the TPB role.
    copiedByReviewer: bool | None = None
    editedByReviewer: bool | None = None

    @model_validator(mode="after")
    def _kind_matches(self) -> "AvailableSuggestionView":
        check_value_kind(self.valueKind, self.suggestedValue)
        if (self.signal == "indicative") != (self.valueKind != "level"):
            raise ValueError("signal 'indicative' goes with category/use_numbers values only")
        return self


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
