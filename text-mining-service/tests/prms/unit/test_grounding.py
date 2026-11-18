from app.text_mining.prms_mining.grounding import (
    assign_candidate_ids,
    mds_support_ratio,
    build_source_index,
    evaluate_candidate,
    format_supporting_excerpts,
    ground_source_candidates,
    strip_internal_fields,
)
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType


SOURCE_TEXT = (
    "Section 3. Achievements\n"
    "In March 2025 the Ministry of Agriculture adopted the national seed\n"
    "certification guideline developed with Alliance researchers, making it\n"
    "mandatory for all registered seed companies.\n"
    "Section 4. Next steps\n"
    "The team plans to train extension agents next year."
)


def _source(content: str = SOURCE_TEXT, source_id: str = "source-1") -> ExtractedPrmsSource:
    return ExtractedPrmsSource(
        source_id=source_id,
        source_index=0,
        source_type=PrmsSourceType.DOCUMENT,
        content=content,
        segments=[content],
        character_count=len(content),
        extraction_seconds=0.01,
        file_name="report.pdf",
        eligible_as_formal_evidence=True,
    )


def _candidate(quote, confidence="high", title="Seed certification guideline adopted"):
    candidate = {"indicator": "Policy Change", "title": title, "description": "d"}
    if quote is not None:
        candidate["supporting_quote"] = quote
    if confidence is not None:
        candidate["confidence"] = confidence
    return candidate


def _evaluate(candidate, content=SOURCE_TEXT, min_mds_support=0.0):
    return evaluate_candidate(
        candidate,
        build_source_index(_source(content)),
        context_chars=80,
        min_mds_support=min_mds_support,
    )


GROUNDED_QUOTE = "the Ministry of Agriculture adopted the national seed certification guideline"


def test_exact_quote_is_grounded_with_surrounding_context():
    decision = _evaluate(
        _candidate("the Ministry of Agriculture adopted the national seed certification guideline")
    )
    assert decision.kept
    assert decision.reason == "grounded"
    assert "Ministry of Agriculture adopted" in decision.context
    assert "Achievements" in decision.context


def test_quote_matching_ignores_case_punctuation_and_line_breaks():
    decision = _evaluate(
        _candidate("THE MINISTRY OF AGRICULTURE ADOPTED THE NATIONAL SEED — certification guideline, developed with Alliance researchers")
    )
    assert decision.kept


def test_long_quote_with_one_changed_word_is_still_grounded():
    decision = _evaluate(
        _candidate(
            "In March 2025 the Ministry of Agriculture adopted the national seed certification "
            "guideline developed with Alliance scientists, making it mandatory for all "
            "registered seed companies"
        )
    )
    assert decision.kept


def test_short_quote_with_a_changed_figure_is_rejected():
    decision = _evaluate(
        _candidate("In March 2023 the Ministry of Agriculture adopted the national seed certification guideline")
    )
    assert not decision.kept


def test_pdf_line_break_hyphenation_is_tolerated():
    content = "The ministry adopted the seed certifi-\ncation guideline for all registered companies."
    decision = _evaluate(
        _candidate("The ministry adopted the seed certification guideline for all registered companies."),
        content=content,
    )
    assert decision.kept
    assert "certifi-" in decision.context


def test_fabricated_quote_is_rejected():
    decision = _evaluate(
        _candidate("The government allocated USD 5 million to scale the seed guideline nationwide.")
    )
    assert not decision.kept
    assert decision.reason == "quote_not_in_source"


def test_missing_short_and_low_confidence_quotes_are_rejected():
    assert _evaluate(_candidate(None)).reason == "missing_quote"
    assert _evaluate(_candidate("   ")).reason == "missing_quote"
    assert _evaluate(_candidate("seed companies")).reason == "quote_too_short"
    low = _evaluate(_candidate("The team plans to train extension agents next year.", confidence="low"))
    assert low.reason == "low_confidence"


def test_missing_confidence_does_not_reject_a_grounded_quote():
    decision = _evaluate(
        _candidate("making it mandatory for all registered seed companies", confidence=None)
    )
    assert decision.kept


def test_ground_source_candidates_enforce_drops_and_tags_kept_results():
    candidates = [
        _candidate("the Ministry of Agriculture adopted the national seed certification guideline"),
        _candidate("A regional seed law was enacted across five countries in 2024.", title="Fake"),
    ]
    kept, contexts = ground_source_candidates(candidates, _source(), context_chars=50, enforce=True)

    assert [item["title"] for item in kept] == ["Seed certification guideline adopted"]
    assert kept[0]["source_id"] == "source-1"
    assert kept[0]["candidate_id"] == "source-1#0"
    assert set(contexts) == {"source-1#0"}
    assert "candidate_id" not in candidates[0]


def test_ground_source_candidates_log_only_keeps_unsupported_results():
    candidates = [_candidate("A regional seed law was enacted across five countries in 2024.")]
    kept, contexts = ground_source_candidates(candidates, _source(), context_chars=50, enforce=False)
    assert len(kept) == 1
    assert contexts == {}


def test_assign_candidate_ids_and_format_excerpts():
    candidates = [
        {"title": "a", "candidate_id": "source-1#0", "source_id": "source-1"},
        {"title": "b", "candidate_id": "source-2#3", "source_id": "source-2"},
    ]
    relabeled, excerpts = assign_candidate_ids(
        candidates, {"source-2#3": "context for b"}
    )
    assert [item["candidate_id"] for item in relabeled] == ["c1", "c2"]
    assert excerpts == [("c2", "source-2", "context for b")]
    assert format_supporting_excerpts(excerpts) == (
        '<excerpt candidate_id="c2" source_id="source-2">\ncontext for b\n</excerpt>'
    )


def test_strip_internal_fields_removes_only_provenance():
    cleaned = strip_internal_fields(
        [
            {
                "indicator": "Other Output",
                "title": "t",
                "supporting_quote": "q",
                "confidence": "high",
                "candidate_id": "c1",
                "source_id": "source-1",
                "stated_fields": ["geo_focus"],
                "inferred_fields": [],
            },
            "not-a-dict",
        ]
    )
    assert cleaned == [{"indicator": "Other Output", "title": "t"}]


def test_mds_support_ratio_counts_fields_listed_in_both_arrays_as_inferred():
    candidate = {
        "stated_fields": ["geo_focus", "lead_center", "policy_change.policy_stage"],
        "inferred_fields": ["policy_change.policy_stage", "policy_change.policy_type"],
    }
    # stated: geo_focus, lead_center; inferred: policy_stage, policy_type.
    assert mds_support_ratio(candidate) == 0.5
    assert mds_support_ratio({"stated_fields": [], "inferred_fields": []}) is None
    assert mds_support_ratio({"stated_fields": "geo_focus"}) is None


def test_mds_support_gate_drops_mostly_inferred_and_unassessed_candidates():
    supported = {
        **_candidate(GROUNDED_QUOTE),
        "stated_fields": ["geo_focus", "lead_center", "policy_change.policy_type"],
        "inferred_fields": ["policy_change.policy_stage"],
    }
    mostly_inferred = {
        **_candidate(GROUNDED_QUOTE),
        "stated_fields": ["geo_focus"],
        "inferred_fields": ["policy_change.policy_type", "policy_change.policy_stage"],
    }
    unassessed = _candidate(GROUNDED_QUOTE)

    assert _evaluate(supported, min_mds_support=0.75).kept
    decision = _evaluate(mostly_inferred, min_mds_support=0.75)
    assert (decision.kept, decision.reason) == (False, "low_mds_support")
    decision = _evaluate(unassessed, min_mds_support=0.75)
    assert (decision.kept, decision.reason) == (False, "missing_mds_support")
    # A disabled gate keeps the grounded candidate without field lists.
    assert _evaluate(unassessed, min_mds_support=0.0).kept


def test_mds_support_gate_runs_after_the_quote_check():
    fabricated = {
        **_candidate("The minister announced a new fertilizer subsidy for all districts in 2025."),
        "stated_fields": ["geo_focus"],
        "inferred_fields": [],
    }
    assert _evaluate(fabricated, min_mds_support=0.75).reason == "quote_not_in_source"
