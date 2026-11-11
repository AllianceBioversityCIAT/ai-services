"""Structured outputs requested from the model, one per prompt version family.

Both map to the same ``NormalizedSuggestion``; the signal colour is computed in code.
"""

from dataclasses import dataclass

from pydantic import BaseModel, Field

MAX_EXPLANATION_WORDS = 50


class SuggestionOutputV1(BaseModel):
    """v1: the previous helper's output keys, plus evidence_quote as the only addition."""

    reasoning: str = Field(description="Reasoning as requested by the prompt.")
    short_justification: str = Field(description="Short justification, as requested by the prompt.")
    score: int = Field(description="Score or level, as requested by the prompt.")
    component: str | None = Field(description="Component, as requested by the prompt, or null.")
    evidence_quote: str = Field(
        description="Verbatim passage copied from the evidence that supports the score. Empty if none."
    )


class SuggestionOutputV2(BaseModel):
    reasoning: str = Field(description="Brief reasoning against the rubric, citing the evidence.")
    value: int = Field(description="Proposed value for the field, within the rubric range.")
    component: str | None = Field(
        description="Rubric component or tag that justifies the value, or null if none applies."
    )
    evidence_quote: str = Field(
        description="Verbatim passage copied from the evidence that supports the value. Empty if none."
    )
    evidence_source_index: int | None = Field(
        description="Index of the evidence source the quote comes from, or null."
    )
    explanation: str = Field(description="Explanation for the assessor, in English, at most 50 words.")


@dataclass(frozen=True)
class NormalizedSuggestion:
    value: int
    explanation: str
    """Shown to the assessor (v1: short_justification)."""
    evidence_quote: str
    component: str | None
    evidence_source_index: int | None


def normalize(output: SuggestionOutputV1 | SuggestionOutputV2) -> NormalizedSuggestion:
    if isinstance(output, SuggestionOutputV1):
        return NormalizedSuggestion(
            value=output.score,
            explanation=output.short_justification,
            evidence_quote=output.evidence_quote,
            component=output.component,
            evidence_source_index=None,
        )
    return NormalizedSuggestion(
        value=output.value,
        explanation=output.explanation,
        evidence_quote=output.evidence_quote,
        component=output.component,
        evidence_source_index=output.evidence_source_index,
    )


def word_count(text: str) -> int:
    return len(text.split())
