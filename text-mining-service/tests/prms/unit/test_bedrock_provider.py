import pytest
from unittest.mock import MagicMock, patch
from app.text_mining.providers.bedrock_client import DEFAULT_MODEL_ID, invoke_model
from app.text_mining.shared.models import ModelInvocationError, ModelInvocationResult


def test_invoke_model_returns_usage_and_text():
    fake_body = MagicMock()
    fake_body.read.return_value = b"""{
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 11, "output_tokens": 22},
        "content": [{"text": "hello from bedrock"}]
    }"""
    fake_client = MagicMock()
    fake_client.invoke_model.return_value = {"body": fake_body}

    with patch("app.text_mining.providers.bedrock_client._bedrock_runtime", fake_client):
        result = invoke_model("prompt", max_tokens=100)

    assert isinstance(result, ModelInvocationResult)
    assert result.text == "hello from bedrock"
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 22
    assert result.model_id == DEFAULT_MODEL_ID
    assert result.stop_reason == "end_turn"
    fake_client.invoke_model.assert_called_once()


def test_invoke_model_wraps_errors():
    fake_client = MagicMock()
    fake_client.invoke_model.side_effect = RuntimeError("boom")

    with patch("app.text_mining.providers.bedrock_client._bedrock_runtime", fake_client):
        with pytest.raises(ModelInvocationError, match="boom"):
            invoke_model("prompt")
