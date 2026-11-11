"""Structured outputs requested from the model, one per prompt family and field kind.

All map to the same ``NormalizedSuggestion``; the signal colour is computed in code.

v1 keeps the previous helper's JSON keys exactly as its prompts ask for them (aliases below), so
the prompt text and the enforced schema agree. ``Evidence Quote`` is the only key added: the signal
needs a passage that can be checked against the evidence.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

MAX_EXPLANATION_WORDS = 50

_V1_REASONING = (
    "Please first reflect on the key pieces of information that will later on justify your decision, "
    "do not decide just yet, gather facts and key pieces of information to inform you"
)
_V1_QUOTE = (
    "One passage copied character for character from the evidence (Content) that best supports the "
    "decision, at least one full sentence. Empty string if no passage supports it."
)


@dataclass(frozen=True)
class NormalizedSuggestion:
    value: int
    explanation: str
    """Shown to the assessor (v1: Short Justification)."""
    evidence_quote: str
    component: str | None
    """Impact Areas: component(s) when the value is 2. IRL/IUL: the prime innovation."""
    evidence_source_index: int | None


class _V1Base(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    reasoning: str = Field(alias="Reasoning", description=_V1_REASONING)


class V1ImpactAreaOutput(_V1Base):
    short_justification: str = Field(
        alias="Short Justification", description="<concise justification, max 50 words>"
    )
    score: int = Field(alias="Score", description="0 | 1 | 2")
    component: str = Field(alias="Component (if Score = 2)", description="Component(s), or N/A")
    evidence_quote: str = Field(alias="Evidence Quote", description=_V1_QUOTE)

    def normalized(self) -> NormalizedSuggestion:
        component = None if self.component.strip().upper() in ("", "N/A", "NA") else self.component
        return NormalizedSuggestion(self.score, self.short_justification, self.evidence_quote, component, None)


class _V1InnovationBase(_V1Base):
    prime_innovation: str = Field(
        alias="Prime Innovation", description="<one-line description of the main innovation>"
    )
    short_justification: str = Field(
        alias="Short Justification", description="<concise justification, max 50 words>"
    )


class V1ReadinessOutput(_V1InnovationBase):
    level: int = Field(alias="Innovation Readiness Level", description="0|1|2|3|4|5|6|7|8|9")
    evidence_quote: str = Field(alias="Evidence Quote", description=_V1_QUOTE)

    def normalized(self) -> NormalizedSuggestion:
        return NormalizedSuggestion(
            self.level, self.short_justification, self.evidence_quote, self.prime_innovation or None, None
        )


class V1UseOutput(_V1InnovationBase):
    level: int = Field(alias="Innovation Use Level", description="0|1|2|3|4|5|6|7|8|9")
    evidence_quote: str = Field(alias="Evidence Quote", description=_V1_QUOTE)

    def normalized(self) -> NormalizedSuggestion:
        return NormalizedSuggestion(
            self.level, self.short_justification, self.evidence_quote, self.prime_innovation or None, None
        )


class SuggestionOutputV2(BaseModel):
    reasoning: str = Field(description="Brief reasoning: key facts from the evidence, then the decision.")
    value: int = Field(description="Recommended value, an integer on the field's scale.")
    component: str | None = Field(description="Component as the system prompt defines it, or null.")
    evidence_quote: str = Field(
        description="Passage copied character for character from one evidence source. Empty if none."
    )
    evidence_source_index: int | None = Field(
        description="Index of the evidence source the quote comes from, or null."
    )
    explanation: str = Field(description="Explanation for the assessor, in English, at most 50 words.")

    def normalized(self) -> NormalizedSuggestion:
        return NormalizedSuggestion(
            self.value, self.explanation, self.evidence_quote, self.component, self.evidence_source_index
        )


SuggestionOutput = V1ImpactAreaOutput | V1ReadinessOutput | V1UseOutput | SuggestionOutputV2

OUTPUT_MODELS: dict[str, type[SuggestionOutput]] = {
    "v1_impact_area": V1ImpactAreaOutput,
    "v1_readiness_level": V1ReadinessOutput,
    "v1_use_level": V1UseOutput,
    "v2": SuggestionOutputV2,
}


def normalize(output: SuggestionOutput) -> NormalizedSuggestion:
    return output.normalized()


def word_count(text: str) -> int:
    return len(text.split())
