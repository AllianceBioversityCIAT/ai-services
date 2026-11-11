import httpx2 as httpx
import pytest
import anthropic

from app.llm.bedrock_mantle import BedrockMantleProvider
from app.llm.output_schema import SuggestionOutputV1, SuggestionOutputV2, normalize
from app.llm.provider import PdfEvidence, RetryableLlmError, SuggestionRequest, TextEvidence
from tests.fakes import fake_client, fake_message

V2_JSON = (
    '{"reasoning":"r","value":2,"component":"Principal","evidence_quote":"quote",'
    '"evidence_source_index":0,"explanation":"Because."}'
)


def request(model=SuggestionOutputV2):
    return SuggestionRequest(
        system_prefix="RUBRIC",
        task="TASK",
        evidence=[TextEvidence(0, 'a "b"', "text"), PdfEvidence(1, "scan.pdf", "JVBERi0=")],
        output_model=model,
        effort="medium",
        max_tokens=4000,
    )


def provider(client):
    return BedrockMantleProvider("anthropic.claude-haiku-5-5", "us-east-1", client=client)


def test_builds_cached_prefix_structured_output_and_no_temperature():
    client = fake_client(fake_message(V2_JSON))
    res = provider(client).suggest(request())
    call = client.messages.calls[0]
    assert "temperature" not in call and "top_p" not in call
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert call["output_config"]["effort"] == "medium"
    assert call["output_config"]["format"]["type"] == "json_schema"
    content = call["messages"][0]["content"]
    assert content[0]["text"].startswith('<evidence index="0" source="a &quot;b&quot;">')
    assert content[1]["type"] == "document" and content[-1]["text"] == "TASK"
    assert res.kind == "ok" and res.output.value == 2 and res.usage.cache_read_input_tokens == 900


@pytest.mark.parametrize(("stop", "kind"), [("refusal", "refusal"), ("max_tokens", "truncated")])
def test_refusal_and_truncation_keep_usage(stop, kind):
    res = provider(fake_client(fake_message("{", stop_reason=stop))).suggest(request())
    assert res.kind == kind and res.output is None and res.usage.input_tokens == 1200


def test_invalid_json_is_invalid_output():
    res = provider(fake_client(fake_message('{"value": "two"}'))).suggest(request())
    assert res.kind == "invalid_output"


def _status_error(cls, status):
    req = httpx.Request("POST", "https://example.invalid")
    return cls("boom", response=httpx.Response(status, request=req), body=None)


def test_throttling_and_5xx_are_retryable_but_400_is_not():
    with pytest.raises(RetryableLlmError):
        provider(fake_client(error=_status_error(anthropic.RateLimitError, 429))).suggest(request())
    with pytest.raises(RetryableLlmError):
        provider(fake_client(error=_status_error(anthropic.InternalServerError, 503))).suggest(request())
    with pytest.raises(anthropic.BadRequestError):
        provider(fake_client(error=_status_error(anthropic.BadRequestError, 400))).suggest(request())


def test_v1_and_v2_map_to_the_same_view():
    v1 = SuggestionOutputV1(reasoning="r", short_justification="Because.", score=2, component="Principal", evidence_quote="q")
    v2 = SuggestionOutputV2.model_validate_json(V2_JSON)
    a, b = normalize(v1), normalize(v2)
    assert (a.value, a.explanation, a.component) == (b.value, b.explanation, b.component)
