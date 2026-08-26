from unittest.mock import patch

from app.text_mining.prms_mining.mining import _run_final_validation
from app.text_mining.shared.models import ModelInvocationResult, ModelUsage


def test_run_final_validation_parses_strict_json():
    candidates = {
        "results": [
            {
                "indicator": "Other Output",
                "title": "Keep me",
                "description": "desc",
                "geo_focus": {"scope_label": "Global"},
            }
        ]
    }
    invocation = ModelInvocationResult(
        text='{"results": [{"indicator": "Other Output", "title": "Keep me", "description": "desc", "geo_focus": {"scope_label": "Global"}}]}',
        usage=ModelUsage(input_tokens=100, output_tokens=50),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )

    with patch(
        "app.text_mining.prms_mining.mining.invoke_model",
        return_value=invocation,
    ) as mock_invoke:
        payload, usage, raw = _run_final_validation(candidates)

    assert len(payload["results"]) == 1
    assert usage.input_tokens == 100
    assert raw.startswith("{")
    mock_invoke.assert_called_once()
    assert mock_invoke.call_args.kwargs["temperature"] == 0


def test_run_final_validation_repair_pass_on_prose_response():
    candidates = {"results": []}
    prose_only = ModelInvocationResult(
        text="I'll work through each result systematically. Result 1 looks valid.",
        usage=ModelUsage(input_tokens=100, output_tokens=80),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )
    repaired = ModelInvocationResult(
        text='{"results": [{"indicator": "Other Outcome", "title": "Outcome", "description": "desc", "geo_focus": {"scope_label": "Global"}}]}',
        usage=ModelUsage(input_tokens=50, output_tokens=40),
        stop_reason="end_turn",
        model_id="test-model",
        duration_seconds=0.1,
    )

    with patch(
        "app.text_mining.prms_mining.mining.invoke_model",
        side_effect=[prose_only, repaired],
    ) as mock_invoke:
        payload, usage, raw = _run_final_validation(candidates)

    assert len(payload["results"]) == 1
    assert usage.input_tokens == 150
    assert usage.output_tokens == 120
    assert mock_invoke.call_count == 2
