"""Deterministic grounding checks for PRMS extraction candidates.

The extraction prompt asks the model to return, for every candidate, a verbatim
``supporting_quote`` copied from the source and a ``confidence`` level. This
module verifies that the quote really exists in the source text (tolerating
whitespace, punctuation, and case differences introduced by PDF/DOCX
extraction) before any candidate reaches final validation. Candidates whose
quote cannot be located are treated as unsupported and dropped.

Every candidate also lists which of its MDS fields the source states
explicitly (``stated_fields``) and which the model inferred
(``inferred_fields``). Candidates whose share of stated fields is below the
configured minimum are dropped too, so a draft is only proposed when the
source itself fills most of its MDS.

Internal provenance fields are removed again before the response is returned,
so the public PRMS response contract does not change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.text_mining.prms_mining.models import ExtractedPrmsSource
from app.utils.logger.logger_util import get_logger

logger = get_logger()

# Fields produced by the extraction model or added by this module. They are
# used during the pipeline only and stripped before the response is returned.
QUOTE_FIELD = "supporting_quote"
CONFIDENCE_FIELD = "confidence"
CANDIDATE_ID_FIELD = "candidate_id"
SOURCE_ID_FIELD = "source_id"
STATED_FIELDS_FIELD = "stated_fields"
INFERRED_FIELDS_FIELD = "inferred_fields"
INTERNAL_FIELDS = (
    QUOTE_FIELD,
    CONFIDENCE_FIELD,
    CANDIDATE_ID_FIELD,
    SOURCE_ID_FIELD,
    STATED_FIELDS_FIELD,
    INFERRED_FIELDS_FIELD,
)

VALID_CONFIDENCE = ("high", "medium", "low")
REJECTED_CONFIDENCE = frozenset({"low"})

MIN_QUOTE_KEY_CHARS = 20
FUZZY_NGRAM_SIZE = 4
FUZZY_MATCH_MIN_RATIO = 0.8

_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_WORD = re.compile(r"[0-9a-z]+")
# Words split across lines by PDF hyphenation, e.g. "certifi-" + newline + "cation".
_LINE_BREAK_HYPHEN = re.compile(r"(?<=[a-z])-[ \t]*\r?\n[ \t]*(?=[a-z])")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class SourceIndex:
    """Normalized, searchable view of one source's text."""

    source_id: str
    content: str
    key: str
    key_to_content: list[int]
    ngram_spans: dict[tuple[str, ...], tuple[int, int]]


@dataclass(frozen=True)
class GroundingDecision:
    kept: bool
    reason: str
    context: str | None = None


def _field_names(value) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if isinstance(item, str) and item.strip()}


def mds_support_ratio(candidate: dict) -> float | None:
    """
    Share of the candidate's MDS fields that the source states explicitly.

    A field listed as both stated and inferred counts as inferred. Returns None
    when the candidate lists no fields at all (support cannot be assessed).
    """
    inferred = _field_names(candidate.get(INFERRED_FIELDS_FIELD))
    stated = _field_names(candidate.get(STATED_FIELDS_FIELD)) - inferred
    total = len(stated) + len(inferred)
    if total == 0:
        return None
    return len(stated) / total


def _normalize_quote(text: str) -> str:
    return _NON_ALNUM.sub(" ", (text or "").lower()).strip()


def build_source_index(source: ExtractedPrmsSource) -> SourceIndex:
    """Build a lowercase alphanumeric key with a map back to original offsets."""
    content = source.content or ""
    lowered = content.lower()
    skipped: set[int] = set()
    for match in _LINE_BREAK_HYPHEN.finditer(lowered):
        skipped.update(range(match.start(), match.end()))

    key_chars: list[str] = []
    key_to_content: list[int] = []
    previous_was_space = True
    for position, char in enumerate(lowered):
        if position in skipped:
            continue
        if char.isascii() and char.isalnum():
            key_chars.append(char)
            key_to_content.append(position)
            previous_was_space = False
        elif not previous_was_space:
            key_chars.append(" ")
            key_to_content.append(position)
            previous_was_space = True
    key = "".join(key_chars)

    words = [(match.group(), match.start(), match.end()) for match in _WORD.finditer(key)]
    ngram_spans: dict[tuple[str, ...], tuple[int, int]] = {}
    for start in range(len(words) - FUZZY_NGRAM_SIZE + 1):
        window = words[start : start + FUZZY_NGRAM_SIZE]
        gram = tuple(word for word, _, _ in window)
        ngram_spans.setdefault(gram, (window[0][1], window[-1][2]))

    return SourceIndex(
        source_id=source.source_id,
        content=content,
        key=key,
        key_to_content=key_to_content,
        ngram_spans=ngram_spans,
    )


def _locate_quote(index: SourceIndex, quote_key: str) -> tuple[int, int] | None:
    """Return (start, end) offsets in the key for the quote, or None."""
    start = index.key.find(quote_key)
    if start >= 0:
        return start, start + len(quote_key)

    # Tolerate small extraction artifacts (hyphenation, a changed or dropped
    # word) by requiring most consecutive word n-grams of the quote to exist.
    words = quote_key.split()
    if len(words) < FUZZY_NGRAM_SIZE:
        return None
    grams = [
        tuple(words[start : start + FUZZY_NGRAM_SIZE])
        for start in range(len(words) - FUZZY_NGRAM_SIZE + 1)
    ]
    spans = [index.ngram_spans[gram] for gram in grams if gram in index.ngram_spans]
    if len(spans) < FUZZY_MATCH_MIN_RATIO * len(grams):
        return None
    return spans[0][0], spans[-1][1]


def _context_window(index: SourceIndex, key_start: int, key_end: int, context_chars: int) -> str:
    content_start = index.key_to_content[key_start]
    content_end = index.key_to_content[max(key_start, key_end - 1)] + 1
    window_start = max(0, content_start - context_chars)
    window_end = min(len(index.content), content_end + context_chars)
    snippet = _WHITESPACE.sub(" ", index.content[window_start:window_end]).strip()
    prefix = "… " if window_start > 0 else ""
    suffix = " …" if window_end < len(index.content) else ""
    return f"{prefix}{snippet}{suffix}"


def evaluate_candidate(
    candidate: dict,
    index: SourceIndex,
    *,
    context_chars: int,
    min_mds_support: float = 0.0,
) -> GroundingDecision:
    """Decide whether one candidate is supported by its source."""
    confidence = str(candidate.get(CONFIDENCE_FIELD) or "").strip().lower()
    if confidence in REJECTED_CONFIDENCE:
        return GroundingDecision(kept=False, reason="low_confidence")

    quote = candidate.get(QUOTE_FIELD)
    if not isinstance(quote, str) or not quote.strip():
        return GroundingDecision(kept=False, reason="missing_quote")

    quote_key = _normalize_quote(quote)
    if len(quote_key) < MIN_QUOTE_KEY_CHARS:
        return GroundingDecision(kept=False, reason="quote_too_short")

    location = _locate_quote(index, quote_key)
    if location is None:
        return GroundingDecision(kept=False, reason="quote_not_in_source")

    if min_mds_support > 0:
        ratio = mds_support_ratio(candidate)
        if ratio is None:
            return GroundingDecision(kept=False, reason="missing_mds_support")
        if ratio < min_mds_support:
            return GroundingDecision(kept=False, reason="low_mds_support")

    return GroundingDecision(
        kept=True,
        reason="grounded",
        context=_context_window(index, location[0], location[1], context_chars),
    )


def ground_source_candidates(
    candidates: list[dict],
    source: ExtractedPrmsSource,
    *,
    context_chars: int,
    enforce: bool = True,
    min_mds_support: float = 0.0,
) -> tuple[list[dict], dict[str, str]]:
    """
    Verify candidates from one source against that source's text.

    Returns the kept candidates, tagged with ``source_id`` and a provisional
    ``candidate_id`` (``<source_id>#<position>``), plus the supporting context
    for each kept candidate keyed by that provisional id. When ``enforce`` is
    False, unsupported candidates are kept and only logged.
    """
    index = build_source_index(source)
    kept: list[dict] = []
    contexts: dict[str, str] = {}
    rejected: dict[str, int] = {}

    for position, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        decision = evaluate_candidate(
            candidate,
            index,
            context_chars=context_chars,
            min_mds_support=min_mds_support,
        )
        if not decision.kept:
            rejected[decision.reason] = rejected.get(decision.reason, 0) + 1
            logger.info(
                "🧹 PRMS grounding %s candidate source=%s position=%s indicator=%s reason=%s "
                "mds_support=%s",
                "dropped" if enforce else "flagged",
                source.source_id,
                position,
                candidate.get("indicator"),
                decision.reason,
                _format_ratio(mds_support_ratio(candidate)),
            )
            if enforce:
                continue
        tagged = dict(candidate)
        tagged[SOURCE_ID_FIELD] = source.source_id
        local_key = f"{source.source_id}#{position}"
        tagged[CANDIDATE_ID_FIELD] = local_key
        if decision.context:
            contexts[local_key] = decision.context
        kept.append(tagged)

    logger.info(
        "🧹 PRMS grounding complete source=%s candidates=%s kept=%s rejected=%s mode=%s",
        source.source_id,
        len(candidates),
        len(kept),
        rejected or "{}",
        "enforce" if enforce else "log_only",
    )
    return kept, contexts


def _format_ratio(ratio: float | None) -> str:
    return "n/a" if ratio is None else f"{ratio:.2f}"


def assign_candidate_ids(
    candidates: list[dict],
    contexts: dict[str, str],
) -> tuple[list[dict], list[tuple[str, str, str]]]:
    """
    Replace provisional per-source keys with short sequential ids (c1, c2, …).

    Returns the relabeled candidates and the list of (candidate_id, source_id,
    context) excerpts to show the final validator.
    """
    relabeled: list[dict] = []
    excerpts: list[tuple[str, str, str]] = []
    for number, candidate in enumerate(candidates, start=1):
        candidate_id = f"c{number}"
        local_key = candidate.get(CANDIDATE_ID_FIELD)
        updated = dict(candidate)
        updated[CANDIDATE_ID_FIELD] = candidate_id
        relabeled.append(updated)
        context = contexts.get(local_key) if local_key else None
        if context:
            excerpts.append((candidate_id, str(candidate.get(SOURCE_ID_FIELD) or ""), context))
    return relabeled, excerpts


def format_supporting_excerpts(excerpts: list[tuple[str, str, str]]) -> str:
    blocks = [
        f'<excerpt candidate_id="{candidate_id}" source_id="{source_id}">\n{context}\n</excerpt>'
        for candidate_id, source_id, context in excerpts
    ]
    return "\n\n".join(blocks)


def strip_internal_fields(results: list[dict]) -> list[dict]:
    """Remove pipeline-only provenance fields before mapping and schema validation."""
    cleaned: list[dict] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        cleaned.append({key: value for key, value in result.items() if key not in INTERNAL_FIELDS})
    return cleaned
