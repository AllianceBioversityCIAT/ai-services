from app.handlers.smoke import handler
from tests.fakes import fake_client, fake_message


def test_smoke_returns_only_model_stop_usage_text():
    client = fake_client(fake_message("OK"))
    out = handler(client=client)
    assert out == {
        "ok": True,
        "api": "runtime",
        "model": "anthropic.claude-haiku-5-5",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 1200, "output_tokens": 300},
        "text": "OK",
    }
    call = client.messages.calls[0]
    assert "temperature" not in call
    assert call["model"] == "us.anthropic.claude-haiku-5-5"
    assert call["extra_body"] == {"anthropic_version": "bedrock-2023-05-31"}
