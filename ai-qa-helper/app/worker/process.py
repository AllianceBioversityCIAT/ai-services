"""One job: (snapshot, field, promptVersion) -> one stored suggestion.

Order: skip if already stored -> criteria -> snapshot -> evidence (no readable evidence: unavailable,
no model call) -> model -> quote check -> signal -> conditional write + run counter.

Transient problems raise ``RetryLater`` (the handler reports the message as failed so SQS redelivers
it). On the last delivery the job is stored as ``unavailable/failed`` instead, so the run counters
account for every expected job and the field shows "not available" rather than staying pending.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal

from app.contract.fields import field_spec
from app.contract.items import (
    ELECTRODB_ENTITY_SUGGESTION,
    ELECTRODB_VERSION,
    AiSuggestionItem,
    suggestion_pk,
    suggestion_sk,
)
from app.contract.messages import AiJobMessage, UnavailableReason
from app.evidence.extractor import EvidenceExtractor, EvidenceOutcome
from app.llm.provider import Effort, LlmProvider, LlmUsage, RetryableLlmError
from app.prompts.builder import ResultContext, build_request
from app.prompts.loader import PromptSpec, UnknownPromptVersion, get_prompt
from app.signal.quote import is_quote_in_evidence
from app.signal.signal import SignalInput, compute_signal
from app.utils.logger.logger_util import get_logger
from app.worker.snapshot import SnapshotReader, read_field_input
from app.worker.store import Counter, SuggestionStore

logger = get_logger()

Outcome = Literal["produced", "unavailable", "failed", "duplicate"]

_ID_NAMESPACE = uuid.UUID("3b0c5c55-6a4f-4f0e-9d0a-2f3918a1c0de")


class RetryLater(Exception):
    """Transient: let SQS redeliver the message."""


@dataclass
class JobDeps:
    snapshots: SnapshotReader
    store: SuggestionStore
    extractor: EvidenceExtractor
    provider: LlmProvider
    effort: Effort
    max_tokens: int
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))
    max_tokens_retry: int = 8000
    """One retry with this cap when the first answer is truncated (thinking counts toward max_tokens)."""


@dataclass
class JobReport:
    """Safe to log: identifiers, counts and reasons only."""

    outcome: Outcome
    reason: str = ""
    signal: str = ""
    usage: list[LlmUsage] = field(default_factory=list)
    evidence_counts: dict[str, int] = field(default_factory=dict)


def process_job(msg: AiJobMessage, deps: JobDeps, final_attempt: bool) -> JobReport:
    job = _Job(msg, deps)
    existing = deps.store.lookup(job.pk, job.sk)
    if existing == "done":
        return JobReport("duplicate")
    job.replaces_failed = existing == "failed"

    spec = field_spec(msg.fieldKey)
    try:
        prompt = get_prompt(msg.promptVersion, msg.fieldKey)
    except UnknownPromptVersion:
        logger.error("job: unknown promptVersion=%s", msg.promptVersion)
        return job.unavailable("failed", detail="unknown_prompt_version")
    if spec is None or prompt is None:
        return job.unavailable("no_criteria_for_field")

    values = deps.snapshots.values(job.result_code, msg.snapKey)
    if values is None:
        if not final_attempt:
            raise RetryLater("snapshot_not_found")
        return job.unavailable("failed", detail="snapshot_not_found")
    fi = read_field_input(values, msg.fieldKey, spec)

    evidence = deps.extractor.extract(fi.links)
    report_counts = dict(evidence.counts)
    if not evidence.readable:
        if evidence.counts.get("error") and not final_attempt:
            raise RetryLater("evidence_transient")
        reason: UnavailableReason = evidence.unavailable_reason or "no_readable_evidence"
        rep = job.unavailable(reason, reportedValue=fi.reported)
        rep.evidence_counts = report_counts
        return rep

    rep = _suggest(job, prompt, spec, fi, evidence, final_attempt)
    rep.evidence_counts = report_counts
    return rep


def record_failure(msg: AiJobMessage, deps: JobDeps, detail: str) -> JobReport:
    """Last-resort write used by the handler after an unexpected error on the final attempt."""
    job = _Job(msg, deps)
    job.replaces_failed = deps.store.lookup(job.pk, job.sk) == "failed"
    return job.unavailable("failed", detail=detail)


def _suggest(job, prompt: PromptSpec, spec, fi, evidence: EvidenceOutcome, final_attempt: bool) -> JobReport:
    deps = job.deps
    built = build_request(prompt, ResultContext(fi.title, fi.description), evidence.sources, deps.effort, deps.max_tokens)
    usage: list[LlmUsage] = []
    try:
        result = deps.provider.suggest(built.request)
        usage.append(result.usage)
        if result.kind == "truncated":
            retry = replace(built.request, max_tokens=deps.max_tokens_retry)
            result = deps.provider.suggest(retry)
            usage.append(result.usage)
    except RetryableLlmError as err:
        if not final_attempt:
            raise RetryLater(f"llm_retryable_{err.status}") from err
        return job.unavailable("failed", detail="llm_retryable_exhausted", usage=usage)

    if result.kind == "refusal":
        return job.unavailable("model_declined", modelId=result.model_id, usage=usage)
    if result.kind != "ok" or result.output is None:
        return job.unavailable("invalid_output", modelId=result.model_id, usage=usage)

    norm = result.output.normalized()
    verified = is_quote_in_evidence(norm.evidence_quote, built.evidence_text)
    try:
        signal = compute_signal(
            SignalInput(spec, fi.reported, norm.value, verified, evidence.partial)
        )
    except ValueError:
        return job.unavailable("invalid_output", modelId=result.model_id, usage=usage)

    source_index, source_url = _quote_source(norm.evidence_source_index, norm.evidence_quote, evidence)
    item = job.item(
        status="available",
        signal=signal,
        explanation=norm.explanation,
        evidenceQuote=norm.evidence_quote,
        evidenceSource=source_url,
        evidenceSourceIndex=source_index,
        suggestedValue=norm.value,
        reportedValue=fi.reported,
        quoteVerified=verified,
        partialEvidence=evidence.partial,
        modelId=result.model_id,
        evidenceHash=evidence.evidence_hash,
    )
    written = deps.store.write(item, "produced", job.replaces_failed)
    return JobReport("produced" if written else "duplicate", signal=signal, usage=usage)


def _quote_source(index: int | None, quote: str, evidence: EvidenceOutcome) -> tuple[int | None, str | None]:
    by_index = {s.index: s for s in evidence.sources}
    if index is not None and index in by_index:
        return index, by_index[index].url
    for s in evidence.sources:
        if s.status == "text" and s.text and is_quote_in_evidence(quote, s.text):
            return s.index, s.url
    return None, None


class _Job:
    def __init__(self, msg: AiJobMessage, deps: JobDeps):
        self.msg = msg
        self.deps = deps
        self.result_code = int(msg.resultCode)
        self.pk = suggestion_pk(self.result_code)
        self.sk = suggestion_sk(msg.snapKey, msg.fieldKey, msg.promptVersion)
        self.replaces_failed = False

    def item(self, **fields) -> AiSuggestionItem:
        return AiSuggestionItem.model_validate(
            {
                "pk": self.pk,
                "sk": self.sk,
                "__edb_e__": ELECTRODB_ENTITY_SUGGESTION,
                "__edb_v__": ELECTRODB_VERSION,
                "resultCode": self.result_code,
                "snapKey": self.msg.snapKey,
                "fieldKey": self.msg.fieldKey,
                "promptVersion": self.msg.promptVersion,
                "suggestionId": str(uuid.uuid5(_ID_NAMESPACE, f"{self.pk}|{self.sk}")),
                "runId": self.msg.runId,
                "createdAt": self.deps.clock().isoformat().replace("+00:00", "Z"),
                **fields,
            }
        )

    def unavailable(
        self, reason: UnavailableReason, detail: str = "", usage: list[LlmUsage] | None = None, **fields
    ) -> JobReport:
        counter: Counter = "failed" if reason == "failed" else "unavailable"
        if reason == "failed" and self.replaces_failed:
            return JobReport("failed", reason=detail or reason, usage=usage or [])  # already stored as failed
        written = self.deps.store.write(
            self.item(status="unavailable", unavailableReason=reason, **fields), counter, self.replaces_failed
        )
        outcome: Outcome = ("failed" if reason == "failed" else "unavailable") if written else "duplicate"
        return JobReport(outcome, reason=detail or reason, usage=usage or [])
