"""Pure core of a suggestion: request -> model -> quote check -> signal. No storage.

Shared by the worker (``process.py``) and the offline comparison (``eval/``), so the evaluation
measures exactly the production path. ``RetryableLlmError`` propagates to the caller.
"""

from dataclasses import dataclass, field, replace
from typing import Literal

from app.contract.fields import FieldSpec
from app.contract.messages import Signal
from app.evidence.extractor import EvidenceOutcome
from app.llm.output_schema import NormalizedSuggestion
from app.llm.provider import Effort, LlmProvider, LlmUsage
from app.prompts.builder import ResultContext, build_request
from app.prompts.loader import PromptSpec
from app.signal.quote import is_quote_in_evidence
from app.signal.signal import SignalInput, compute_signal


@dataclass(frozen=True)
class SuggestParams:
    effort: Effort
    max_tokens: int
    max_tokens_retry: int = 8000
    """One retry with this cap when the first answer is truncated (thinking counts toward max_tokens)."""


@dataclass
class Suggestion:
    kind: Literal["ok", "model_declined", "invalid_output"]
    model_id: str = ""
    usage: list[LlmUsage] = field(default_factory=list)
    output: NormalizedSuggestion | None = None
    signal: Signal | None = None
    quote_verified: bool = False
    source_index: int | None = None
    source_url: str | None = None


def suggest(
    provider: LlmProvider,
    prompt: PromptSpec,
    spec: FieldSpec,
    result: ResultContext,
    reported: int | None,
    evidence: EvidenceOutcome,
    params: SuggestParams,
) -> Suggestion:
    built = build_request(prompt, result, evidence.sources, params.effort, params.max_tokens)
    usage: list[LlmUsage] = []
    res = provider.suggest(built.request)
    usage.append(res.usage)
    if res.kind == "truncated":
        res = provider.suggest(replace(built.request, max_tokens=params.max_tokens_retry))
        usage.append(res.usage)

    if res.kind == "refusal":
        return Suggestion("model_declined", res.model_id, usage)
    if res.kind != "ok" or res.output is None:
        return Suggestion("invalid_output", res.model_id, usage)

    norm = res.output.normalized()
    verified = is_quote_in_evidence(norm.evidence_quote, built.evidence_text)
    try:
        signal = compute_signal(SignalInput(spec, reported, norm.value, verified, evidence.partial))
    except ValueError:
        return Suggestion("invalid_output", res.model_id, usage)
    index, url = quote_source(norm.evidence_source_index, norm.evidence_quote, evidence)
    return Suggestion("ok", res.model_id, usage, norm, signal, verified, index, url)


def quote_source(index: int | None, quote: str, evidence: EvidenceOutcome) -> tuple[int | None, str | None]:
    by_index = {s.index: s for s in evidence.sources}
    if index is not None and index in by_index:
        return index, by_index[index].url
    for s in evidence.sources:
        if s.status == "text" and s.text and is_quote_in_evidence(quote, s.text):
            return s.index, s.url
    return None, None
