from app.text_mining.prms_mining.prompt_builder import build_final_validation_prompt


def _candidates() -> dict:
    return {
        "results": [
            {
                "candidate_id": "c1",
                "indicator": "Policy Change",
                "title": "Budget policy",
                "description": "National budget allocation.",
                "geo_focus": {"scope_code": 1, "scope_label": "Global"},
                "supporting_quote": "The ministry approved a national budget line.",
                "confidence": "high",
            }
        ]
    }


def test_final_validation_prompt_shape():
    prompt = build_final_validation_prompt(candidates=_candidates())
    assert "CANDIDATE RESULTS JSON" in prompt
    assert "SUPPORTING SOURCE EXCERPTS" in prompt
    assert "(no supporting excerpts available)" in prompt
    assert "You do NOT have the full source documents" in prompt
    assert "Decision order" in prompt
    assert "Duplication — merge or remove" in prompt
    assert "Never add a new result" in prompt
    assert "Do NOT remove a result because it seems thematically unrelated" in prompt
    assert "Never remove a candidate solely because it appears thematically unrelated" in prompt


def test_final_validation_prompt_includes_candidate_excerpts():
    excerpt = '<excerpt candidate_id="c1" source_id="source-1">\nThe ministry approved a national budget line.\n</excerpt>'
    prompt = build_final_validation_prompt(candidates=_candidates(), supporting_excerpts=excerpt)
    assert excerpt in prompt
    assert "(no supporting excerpts available)" not in prompt


def test_final_validation_rules_remove_unsupported_and_cross_indicator_duplicates():
    prompt = build_final_validation_prompt(candidates=_candidates())
    assert "Prefer keeping a valid result over removing it" not in prompt
    assert "0. Support — remove the result when its supporting excerpt" in prompt
    assert "MoU" in prompt
    assert "The same achievement reported under DIFFERENT indicators is also a duplicate" in prompt
    assert "Do not \"rescue\" an unsupported candidate by changing its indicator" in prompt
