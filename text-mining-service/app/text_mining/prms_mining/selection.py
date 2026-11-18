"""Cap the number of PRMS draft results by the length of the sources.

Users review every returned result as a draft. A short document (2-3 pages)
rarely supports more than a few reportable results, so the pipeline keeps only
the strongest candidates, with a limit that grows with the total length of the
sources.

Ranking uses signals recorded before final validation (keyed by candidate_id):
confidence first ("high" before "medium"), then the share of MDS fields the
source states explicitly, then the original order. Kept results stay in their
original order so drafts read in document order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.text_mining.prms_mining.grounding import (
    CANDIDATE_ID_FIELD,
    CONFIDENCE_FIELD,
    mds_support_ratio,
)
from app.text_mining.prms_mining.models import ExtractedPrmsSource

# Characters per page used when a source has no page count (DOCX, free text,
# audio transcripts). About 500 words of English prose.
CHARS_PER_PAGE = 3000

_CONFIDENCE_RANK = {"high": 2, "medium": 1}


@dataclass(frozen=True)
class CandidateScore:
    confidence_rank: int
    mds_support: float
    position: int


def parse_cap_tiers(raw: str) -> list[tuple[int, int]]:
    """
    Parse "max_pages:max_results" pairs, e.g. "3:3,10:5,25:8".

    Returns the tiers sorted by page limit. Raises ValueError on malformed input.
    """
    tiers: list[tuple[int, int]] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        pages_text, _, results_text = part.partition(":")
        try:
            pages, results = int(pages_text), int(results_text)
        except ValueError as exc:
            raise ValueError(f"Invalid result cap tier {part!r}; expected 'pages:results'") from exc
        if pages <= 0 or results <= 0:
            raise ValueError(f"Result cap tier values must be > 0, got {part!r}")
        tiers.append((pages, results))
    return sorted(tiers)


def estimate_pages(sources: list[ExtractedPrmsSource]) -> int:
    """Total pages across sources; uses character count when pages are unknown."""
    total = 0
    for source in sources:
        if source.page_count:
            total += source.page_count
        else:
            total += max(1, math.ceil((source.character_count or 0) / CHARS_PER_PAGE))
    return total


def max_results_for_pages(pages: int, tiers: list[tuple[int, int]], ceiling: int) -> int:
    for max_pages, max_results in tiers:
        if pages <= max_pages:
            return min(max_results, ceiling)
    return ceiling


def score_candidates(candidates: list[dict]) -> dict[str, CandidateScore]:
    """Record ranking signals by candidate_id before final validation drops them."""
    scores: dict[str, CandidateScore] = {}
    for position, candidate in enumerate(candidates):
        candidate_id = candidate.get(CANDIDATE_ID_FIELD)
        if not candidate_id:
            continue
        confidence = str(candidate.get(CONFIDENCE_FIELD) or "").strip().lower()
        scores[str(candidate_id)] = CandidateScore(
            confidence_rank=_CONFIDENCE_RANK.get(confidence, 0),
            mds_support=mds_support_ratio(candidate) or 0.0,
            position=position,
        )
    return scores


def cap_results(
    results: list[dict],
    scores: dict[str, CandidateScore],
    limit: int,
) -> list[dict]:
    """Keep the `limit` strongest results, in their original order."""
    if len(results) <= limit:
        return results

    def sort_key(item: tuple[int, dict]):
        index, result = item
        score = scores.get(str(result.get(CANDIDATE_ID_FIELD) or ""))
        if score is None:
            # Unknown provenance (validator dropped the id): rank after known ones.
            return (1, 0, 0.0, index)
        return (0, -score.confidence_rank, -score.mds_support, index)

    ranked = sorted(enumerate(results), key=sort_key)
    kept_indexes = sorted(index for index, _ in ranked[:limit])
    return [results[index] for index in kept_indexes]
