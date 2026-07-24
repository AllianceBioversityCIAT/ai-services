from unittest.mock import patch

from app.text_mining.prms_mining.corpus import ContextBuildResult
from app.text_mining.prms_mining.models import ExtractedPrmsSource, PrmsSourceType
from app.text_mining.shared.models import ModelInvocationResult, ModelUsage


def test_process_document_prms_text_only_happy_path():
    extracted = [
        ExtractedPrmsSource(
            source_id="source-1",
            source_index=0,
            source_type=PrmsSourceType.FREE_TEXT,
            content="Group training for 20 female extension agents in Kenya.",
            segments=["Group training for 20 female extension agents in Kenya."],
            character_count=55,
            extraction_seconds=0.01,
            eligible_as_formal_evidence=False,
        )
    ]
    invocation = ModelInvocationResult(
        text=(
            '{"results":[{"indicator":"Capacity Sharing for Development",'
            '"title":"Extension agent training","description":"Short-term group training",'
            '"geo_focus":{"scope_code":4,"scope_label":"National","countries":[{"iso_alpha_2":"KE"}]},'
            '"capacity_sharing":{"number_people_trained":{"women":20},'
            '"length_training":"Short-term","delivery_method":"In person"}}]}'
        ),
        usage=ModelUsage(input_tokens=10, output_tokens=20),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )

    with (
        patch(
            "app.text_mining.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.text_mining.prms_mining.mining.build_context_excerpts",
            return_value=ContextBuildResult(
                excerpts="chunk text",
                retrieval_version="prms-retrieval-v1",
                chunks_processed=0,
                estimated_tokens=4,
                trimmed=False,
            ),
        ),
        patch(
            "app.text_mining.prms_mining.mining.invoke_model",
            side_effect=[invocation, invocation],
        ),
        patch(
            "app.text_mining.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
    ):
        from app.text_mining.prms_mining.mining import process_document_prms

        result = process_document_prms(text="Group training for 20 female extension agents in Kenya.")

    assert result["project"] == "PRMS"
    assert result["json_content"]["results"]
    assert result["json_content"]["results"][0]["capacity_sharing"]["number_people_trained"]["women"] == 20
    assert result["source_counts"]["free_text"] == 1
