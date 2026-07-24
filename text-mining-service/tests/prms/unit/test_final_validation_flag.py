from app.text_mining.prms_mining.prompt_builder import build_final_validation_prompt


def test_final_validation_prompt_shape():
    prompt = build_final_validation_prompt(
        candidates={
            "results": [
                {
                    "indicator": "Policy Change",
                    "title": "Budget policy",
                    "description": "National budget allocation.",
                    "geo_focus": {"scope_code": 1, "scope_label": "Global"},
                }
            ]
        },
    )
    assert "CANDIDATE RESULTS JSON" in prompt
    assert "SUPPORTING SOURCE EXCERPTS" not in prompt
    assert "You do NOT have access to source documents" in prompt
    assert "Decision order" in prompt
    assert "Duplication — merge or remove" in prompt
    assert "Never add a new result" in prompt
    assert "Do NOT remove a result because it seems thematically unrelated" in prompt
    assert "Never remove a candidate solely because it appears thematically unrelated" in prompt
