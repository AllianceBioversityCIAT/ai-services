from unittest.mock import patch

from app.llm.prms_mining.corpus import ContextBuildResult
from app.llm.prms_mining.models import ExtractedPrmsSource, PrmsSourceType
from app.llm.shared.models import ModelInvocationResult, ModelUsage


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
        text='{"results":[{"indicator":"Capacity Sharing for Development","title":"Extension agent training","description":"Short-term group training","keywords":["training","extension"],"geoscope_level":"National","training_type":"Group training","female_participants":20}]}',
        usage=ModelUsage(input_tokens=10, output_tokens=20),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )

    with (
        patch(
            "app.llm.prms_mining.mining.extract_sources",
            return_value=extracted,
        ),
        patch(
            "app.llm.prms_mining.mining.build_context_excerpts",
            return_value=ContextBuildResult(
                excerpts="chunk text",
                retrieval_version="prms-retrieval-v1",
                chunks_processed=0,
                estimated_tokens=4,
                trimmed=False,
            ),
        ),
        patch(
            "app.llm.prms_mining.mining.invoke_model",
            return_value=invocation,
        ),
        patch(
            "app.llm.prms_mining.mining.map_fields_with_opensearch",
            side_effect=lambda result, *_args, **_kwargs: result,
        ),
        patch("app.llm.prms_mining.mining.PRMS_FINAL_VALIDATION_ENABLED", False),
    ):
        from app.llm.prms_mining.mining import process_document_prms

        result = process_document_prms(text="Group training for 20 female extension agents in Kenya.")

    assert result["project"] == "PRMS"
    assert result["json_content"]["results"]
    assert result["json_content"]["results"][0]["indicator"] == "Capacity Sharing for Development"
    assert result["source_counts"]["free_text"] == 1
