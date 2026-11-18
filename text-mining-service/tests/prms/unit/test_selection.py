import pytest

from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType
from app.text_mining.prms_mining.selection import (
    CHARS_PER_PAGE,
    cap_results,
    estimate_pages,
    max_results_for_pages,
    parse_cap_tiers,
    score_candidates,
)


def _source(page_count=None, characters=1000, source_type=PrmsSourceType.DOCUMENT):
    return ExtractedPrmsSource(
        source_id="source-1",
        source_index=0,
        source_type=source_type,
        content="x",
        segments=["x"],
        page_count=page_count,
        character_count=characters,
        extraction_seconds=0.01,
    )


def test_parse_cap_tiers_sorts_and_rejects_malformed_values():
    assert parse_cap_tiers("10:5, 3:3,25:8") == [(3, 3), (10, 5), (25, 8)]
    assert parse_cap_tiers("") == []
    with pytest.raises(ValueError):
        parse_cap_tiers("3-3")
    with pytest.raises(ValueError):
        parse_cap_tiers("3:0")


def test_estimate_pages_uses_page_count_or_characters():
    sources = [
        _source(page_count=3),
        _source(characters=CHARS_PER_PAGE * 4 + 1),  # DOCX without page count -> 5
        _source(characters=10, source_type=PrmsSourceType.FREE_TEXT),  # at least 1
    ]
    assert estimate_pages(sources) == 9


def test_max_results_for_pages_follows_tiers_and_ceiling():
    tiers = [(3, 3), (10, 5), (25, 8)]
    assert max_results_for_pages(2, tiers, 10) == 3
    assert max_results_for_pages(3, tiers, 10) == 3
    assert max_results_for_pages(9, tiers, 10) == 5
    assert max_results_for_pages(79, tiers, 10) == 10
    assert max_results_for_pages(2, tiers, 2) == 2


def test_cap_results_keeps_strongest_in_original_order():
    candidates = [
        {"candidate_id": "c1", "confidence": "medium", "stated_fields": ["a"], "inferred_fields": []},
        {"candidate_id": "c2", "confidence": "high", "stated_fields": ["a"], "inferred_fields": ["b"]},
        {"candidate_id": "c3", "confidence": "high", "stated_fields": ["a", "b"], "inferred_fields": []},
        {"candidate_id": "c4", "confidence": "medium", "stated_fields": ["a", "b"], "inferred_fields": []},
    ]
    scores = score_candidates(candidates)
    validated = [{"candidate_id": cid} for cid in ("c1", "c2", "c3", "c4")]

    kept = cap_results(validated, scores, 3)
    # Ranked c3 (high, 1.0), c2 (high, 0.5), c1/c4 (medium, 1.0) -> c1 wins the tie by order.
    assert [item["candidate_id"] for item in kept] == ["c1", "c2", "c3"]


def test_cap_results_ranks_results_without_known_id_last_and_skips_when_under_limit():
    scores = score_candidates([{"candidate_id": "c1", "confidence": "medium"}])
    validated = [{"title": "no id"}, {"candidate_id": "c1"}]
    assert cap_results(validated, scores, 1) == [{"candidate_id": "c1"}]
    assert cap_results(validated, scores, 5) == validated
