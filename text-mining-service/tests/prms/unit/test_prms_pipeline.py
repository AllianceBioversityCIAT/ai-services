from unittest.mock import patch

from app.text_mining.prms_mining.corpus import ContextBuildResult
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType
from app.text_mining.shared.models import ModelInvocationResult, ModelUsage


KENYA_TEXT = "The project trained 20 women farmers in Kenya on seed storage."
UGANDA_TEXT = "Fifteen district officers in Uganda completed a policy training course."


def _free_text_source(content: str, source_index: int = 0) -> ExtractedPrmsSource:
    return ExtractedPrmsSource(
        source_id=f"source-{source_index + 1}",
        source_index=source_index,
        source_type=PrmsSourceType.FREE_TEXT,
        content=content,
        segments=[content],
        character_count=len(content),
        extraction_seconds=0.01,
        eligible_as_formal_evidence=False,
    )


def _capacity_result(title: str, women: int, quote: str | None = None) -> dict:
    result = {
        "indicator": "Capacity Sharing for Development",
        "title": title,
        "description": "Short-term group training",
        "geo_focus": {
            "scope_code": 4,
            "scope_label": "National",
            "countries": [{"iso_alpha_2": "KE"}],
        },
        "capacity_sharing": {
            "number_people_trained": {"women": women},
            "length_training": "Short-term",
            "delivery_method": "In person",
        },
    }
    if quote is not None:
        result["supporting_quote"] = quote
        result["confidence"] = "high"
    return result


def _model_invocation(results: list[dict]) -> ModelInvocationResult:
    import json

    return ModelInvocationResult(
        text=json.dumps({"results": results}),
        usage=ModelUsage(input_tokens=10, output_tokens=20),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )


def test_process_document_prms_text_only_happy_path():
    extracted = [_free_text_source("Group training for 20 female extension agents in Kenya.")]
    per_source_context = ContextBuildResult(
        excerpts="chunk text",
        retrieval_version="prms-retrieval-v1",
        chunks_processed=0,
        estimated_tokens=4,
        trimmed=False,
    )
    validation_invocation = _model_invocation(
        [_capacity_result("Extension agent training", 20)]
    )

    with (
        patch(
            "app.text_mining.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.text_mining.prms_mining.mining.build_single_source_excerpts",
            return_value=per_source_context,
        ),
        patch(
            "app.text_mining.prms_mining.mining.invoke_model",
            side_effect=[
                _model_invocation([_capacity_result("Extension agent training", 20, quote="Group training for 20 female extension agents in Kenya.")]),
                validation_invocation,
            ],
        ),
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(text="Group training for 20 female extension agents in Kenya.")

    assert result["project"] == "PRMS"
    assert result["extraction_mode"] == "per_source_parallel"
    assert result["sources_processed"] == 1
    assert result["json_content"]["results"]
    assert result["json_content"]["results"][0]["capacity_sharing"]["number_people_trained"]["women"] == 20
    assert result["source_counts"]["free_text"] == 1


def test_process_document_prms_parallel_per_source_extraction_merges_results():
    extracted = [
        _free_text_source(KENYA_TEXT, source_index=0),
        _free_text_source(UGANDA_TEXT, source_index=1),
    ]
    def per_source_context(source, **_kwargs):
        return ContextBuildResult(
            excerpts=source.content,
            retrieval_version="prms-retrieval-v1",
            chunks_processed=0,
            estimated_tokens=4,
            trimmed=False,
        )

    validation_invocation = _model_invocation(
        [
            _capacity_result("Kenya training", 20),
            _capacity_result("Uganda policy training", 15),
        ]
    )

    def fake_invoke(prompt, **_kwargs):
        # Parallel workers call the model in any order; answer by prompt content.
        if "CANDIDATE RESULTS JSON" in prompt:
            return validation_invocation
        if KENYA_TEXT in prompt:
            return _model_invocation([_capacity_result("Kenya training", 20, quote=KENYA_TEXT)])
        return _model_invocation(
            [_capacity_result("Uganda policy training", 15, quote=UGANDA_TEXT)]
        )

    with (
        patch(
            "app.text_mining.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.text_mining.prms_mining.mining.build_single_source_excerpts",
            side_effect=per_source_context,
        ),
        patch(
            "app.text_mining.prms_mining.mining.invoke_model",
            side_effect=fake_invoke,
        ) as mock_invoke,
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(
            text=KENYA_TEXT,
            keys=["ignored-for-this-test"],
        )

    assert result["sources_processed"] == 2
    assert mock_invoke.call_count == 3
    titles = {item["title"] for item in result["json_content"]["results"]}
    assert titles == {"Kenya training", "Uganda policy training"}


def test_process_document_prms_drops_ungrounded_candidates_and_strips_provenance():
    source_text = (
        "Background on the region. "
        + KENYA_TEXT
        + " The team also held an inception meeting with partners."
    )
    extracted = [_free_text_source(source_text)]
    per_source_context = ContextBuildResult(
        excerpts=source_text,
        retrieval_version="prms-retrieval-v1",
        chunks_processed=0,
        estimated_tokens=10,
        trimmed=False,
    )
    grounded = _capacity_result("Kenya seed storage training", 20, quote=KENYA_TEXT)
    hallucinated = _capacity_result(
        "Regional training of 500 agents",
        500,
        quote="The project trained 500 extension agents across East Africa in 2025.",
    )
    low_confidence = {
        **_capacity_result("Inception meeting", 5, quote="The team also held an inception meeting with partners."),
        "confidence": "low",
    }
    # The validator echoes the provenance fields back; they must not reach the response.
    validation_invocation = _model_invocation(
        [{**grounded, "candidate_id": "c1", "source_id": "source-1"}]
    )

    with (
        patch(
            "app.text_mining.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.text_mining.prms_mining.mining.build_single_source_excerpts",
            return_value=per_source_context,
        ),
        patch(
            "app.text_mining.prms_mining.mining.invoke_model",
            side_effect=[
                _model_invocation([grounded, hallucinated, low_confidence]),
                validation_invocation,
            ],
        ) as mock_invoke,
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(text=source_text)

    validation_prompt = mock_invoke.call_args_list[1].args[0]
    assert "Kenya seed storage training" in validation_prompt
    assert "Regional training of 500 agents" not in validation_prompt
    assert "Inception meeting" not in validation_prompt
    assert '<excerpt candidate_id="c1" source_id="source-1">' in validation_prompt
    assert "Background on the region." in validation_prompt

    results = result["json_content"]["results"]
    assert [item["title"] for item in results] == ["Kenya seed storage training"]
    for field in ("supporting_quote", "confidence", "candidate_id", "source_id"):
        assert field not in results[0]


def test_process_document_prms_skips_validation_when_nothing_is_grounded():
    extracted = [_free_text_source(KENYA_TEXT)]
    per_source_context = ContextBuildResult(
        excerpts=KENYA_TEXT,
        retrieval_version="prms-retrieval-v1",
        chunks_processed=0,
        estimated_tokens=10,
        trimmed=False,
    )

    with (
        patch(
            "app.text_mining.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.text_mining.prms_mining.mining.build_single_source_excerpts",
            return_value=per_source_context,
        ),
        patch(
            "app.text_mining.prms_mining.mining.invoke_model",
            side_effect=[_model_invocation([_capacity_result("No quote", 3)])],
        ) as mock_invoke,
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(text=KENYA_TEXT)

    assert mock_invoke.call_count == 1
    assert result["json_content"]["results"] == []
