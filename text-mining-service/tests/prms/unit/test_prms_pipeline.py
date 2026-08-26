from unittest.mock import patch

from app.text_mining.prms_mining.corpus import ContextBuildResult
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType
from app.text_mining.shared.models import ModelInvocationResult, ModelUsage


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


def _capacity_result(title: str, women: int) -> dict:
    return {
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
                _model_invocation([_capacity_result("Extension agent training", 20)]),
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
        _free_text_source("Training in Kenya", source_index=0),
        _free_text_source("Policy adoption in Uganda", source_index=1),
    ]
    per_source_context = ContextBuildResult(
        excerpts="source excerpt",
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
                _model_invocation([_capacity_result("Kenya training", 20)]),
                _model_invocation([_capacity_result("Uganda policy training", 15)]),
                validation_invocation,
            ],
        ) as mock_invoke,
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(
            text="Training in Kenya",
            keys=["ignored-for-this-test"],
        )

    assert result["sources_processed"] == 2
    assert mock_invoke.call_count == 3
    titles = {item["title"] for item in result["json_content"]["results"]}
    assert titles == {"Kenya training", "Uganda policy training"}
