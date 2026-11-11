import httpx2 as httpx
import pytest
import anthropic

from app.llm.bedrock_mantle import BedrockMantleProvider
from app.llm.output_schema import SuggestionOutputV2, V1ImpactAreaOutput, normalize
from app.llm.provider import PdfEvidence, RetryableLlmError, SuggestionRequest, TextPart
from tests.fakes import fake_client, fake_message

V2_JSON = (
    '{"reasoning":"r","value":2,"component":"Principal","evidence_quote":"quote",'
    '"evidence_source_index":0,"explanation":"Because."}'
)


def request(model=SuggestionOutputV2, cache_system=True):
    return SuggestionRequest(
        system="RUBRIC",
        content=[TextPart("EVIDENCE"), PdfEvidence(1, "scan.pdf", "JVBERi0="), TextPart("TASK")],
        output_model=model,
        effort="medium",
        max_tokens=4000,
        cache_system=cache_system,
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
    assert [c["type"] for c in content] == ["text", "document", "text"]
    assert content[0]["text"] == "EVIDENCE" and content[-1]["text"] == "TASK"
    assert res.kind == "ok" and res.output.value == 2 and res.usage.cache_read_input_tokens == 900


def test_system_without_cache_breakpoint_when_not_requested():
    client = fake_client(fake_message(V2_JSON))
    provider(client).suggest(request(cache_system=False))
    assert client.messages.calls[0]["system"] == [{"type": "text", "text": "RUBRIC"}]


def test_v1_schema_uses_the_previous_helper_keys():
    client = fake_client(fake_message(
        '{"Reasoning":"r","Short Justification":"Because.","Score":1,"Component (if Score = 2)":"N/A",'
        '"Evidence Quote":"q"}'
    ))
    res = provider(client).suggest(request(model=V1ImpactAreaOutput))
    props = client.messages.calls[0]["output_config"]["format"]["schema"]["properties"]
    assert list(props) == ["Reasoning", "Short Justification", "Score", "Component (if Score = 2)", "Evidence Quote"]
    assert res.kind == "ok" and normalize(res.output).component is None


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
    v1 = V1ImpactAreaOutput(reasoning="r", short_justification="Because.", score=2, component="Principal", evidence_quote="q")
    v2 = SuggestionOutputV2.model_validate_json(V2_JSON)
    a, b = normalize(v1), normalize(v2)
    assert (a.value, a.explanation, a.component) == (b.value, b.explanation, b.component)
