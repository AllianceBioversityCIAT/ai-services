"""Bedrock adapter for the LlmProvider port, on either of the two Bedrock APIs for Claude.

- ``runtime`` (default): Amazon Bedrock Runtime InvokeModel, client ``anthropic.lib.bedrock.AnthropicBedrock``,
  endpoint ``https://bedrock-runtime.<region>.amazonaws.com/model/<id>/invoke``, model = inference profile
  ``us.anthropic.claude-haiku-5-5``. IAM: ``bedrock:InvokeModel`` on the profile and the model.
- ``mantle``: Claude in Amazon Bedrock, client ``AnthropicBedrockMantle``, endpoint
  ``https://bedrock-mantle.<region>.api.aws/anthropic``, model ``anthropic.claude-haiku-5-5``.
  IAM: ``bedrock-mantle:CreateInference``. In the TEST account it answers 404 for Haiku 5.5 (2026-11-11).

Both take the same Messages body; AWS documents ``output_config.format`` (structured outputs),
``output_config.effort`` and explicit ``cache_control`` for Haiku 5.5 on InvokeModel. The runtime body
carries ``anthropic_version = bedrock-2023-05-31`` as in the AWS examples (the SDK default would be the
newer ``2026-10-21``). Auth: the default AWS credential chain (SigV4).

Claude Haiku 5.5 constraints honoured here: no temperature/top_p/top_k, no assistant prefill,
adaptive thinking counts toward max_tokens, refusals handled client-side.

``messages.create`` with a JSON-schema output format is used instead of ``messages.parse``:
``parse`` raises on a truncated or invalid JSON body and the stop reason and token usage of that
call are lost. Here every outcome keeps its usage.
"""

from typing import Any, Literal

import anthropic
from anthropic.lib.bedrock import AnthropicBedrock, AnthropicBedrockMantle
from pydantic import ValidationError

from app.llm.provider import (
    LlmUsage,
    OutputT,
    PdfEvidence,
    RetryableLlmError,
    SuggestionRequest,
    SuggestionResult,
    TextPart,
)


BedrockApi = Literal["runtime", "mantle"]
RUNTIME_ANTHROPIC_VERSION = "bedrock-2023-05-31"
DEFAULT_MODEL_IDS: dict[str, str] = {
    "runtime": "us.anthropic.claude-haiku-5-5",
    "mantle": "anthropic.claude-haiku-5-5",
}


def make_client(
    api: BedrockApi, aws_region: str, aws_profile: str | None = None, max_retries: int = 3, timeout_s: float = 150.0
) -> Any:
    """``timeout_s``: AWS recommends at least 120 s, since a new output schema can take ~90 s to compile."""
    cls = AnthropicBedrock if api == "runtime" else AnthropicBedrockMantle
    return cls(aws_region=aws_region, aws_profile=aws_profile, max_retries=max_retries, timeout=timeout_s)


def extra_body(api: BedrockApi) -> dict[str, Any] | None:
    return {"anthropic_version": RUNTIME_ANTHROPIC_VERSION} if api == "runtime" else None


class BedrockProvider:
    def __init__(
        self,
        model_id: str,
        aws_region: str,
        api: BedrockApi = "runtime",
        client: Any | None = None,
        aws_profile: str | None = None,
    ):
        """``aws_profile`` is for local runs (the offline comparison); the Lambda uses its role."""
        if api not in DEFAULT_MODEL_IDS:
            raise ValueError(f"unknown Bedrock API {api!r}")
        self._model_id = model_id
        self._extra_body = extra_body(api)
        self._client = client or make_client(api, aws_region, aws_profile)

    def suggest(self, request: SuggestionRequest[OutputT]) -> SuggestionResult[OutputT]:
        content: list[dict[str, Any]] = []
        for part in request.content:
            if isinstance(part, TextPart):
                content.append({"type": "text", "text": part.text})
            elif isinstance(part, PdfEvidence):
                content.append(
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": part.data_base64},
                        "title": f"evidence {part.source_index}: {part.label}",
                    }
                )
        system: dict[str, Any] = {"type": "text", "text": request.system}
        if request.cache_system:
            system["cache_control"] = {"type": "ephemeral"}

        schema = anthropic.transform_schema(request.output_model.model_json_schema())
        try:
            message = self._client.messages.create(
                model=self._model_id,
                max_tokens=request.max_tokens,
                system=[system],
                messages=[{"role": "user", "content": content}],
                output_config={"effort": request.effort, "format": {"type": "json_schema", "schema": schema}},
                **({"extra_body": self._extra_body} if self._extra_body else {}),
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as err:
            raise RetryableLlmError(str(err), getattr(err, "status_code", None)) from err
        except anthropic.APIStatusError as err:
            if err.status_code >= 500:
                raise RetryableLlmError(str(err), err.status_code) from err
            raise

        usage = _usage(message.usage)
        model_id = message.model
        if message.stop_reason == "refusal":
            return SuggestionResult(kind="refusal", model_id=model_id, usage=usage)
        if message.stop_reason == "max_tokens":
            return SuggestionResult(kind="truncated", model_id=model_id, usage=usage)
        text = "".join(b.text for b in message.content if getattr(b, "type", None) == "text")
        try:
            output = request.output_model.model_validate_json(text)
        except ValidationError:
            return SuggestionResult(kind="invalid_output", model_id=model_id, usage=usage)
        return SuggestionResult(kind="ok", model_id=model_id, usage=usage, output=output)


def _usage(u: Any) -> LlmUsage:
    return LlmUsage(
        input_tokens=u.input_tokens or 0,
        output_tokens=u.output_tokens or 0,
        cache_read_input_tokens=getattr(u, "cache_read_input_tokens", None) or 0,
        cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", None) or 0,
    )

