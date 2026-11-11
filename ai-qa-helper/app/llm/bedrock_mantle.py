"""Claude in Amazon Bedrock (Mantle) adapter for the LlmProvider port.

Client: ``anthropic.lib.bedrock.AnthropicBedrockMantle`` (package ``anthropic[bedrock]``), endpoint
``https://bedrock-mantle.<region>.api.aws/anthropic``. Auth: the Lambda execution role through the
default AWS credential chain (SigV4). IAM action: ``bedrock-mantle:CreateInference``.

Claude Haiku 5.5 constraints honoured here: no temperature/top_p/top_k, no assistant prefill,
adaptive thinking counts toward max_tokens, refusals handled client-side.

``messages.create`` with a JSON-schema output format is used instead of ``messages.parse``:
``parse`` raises on a truncated or invalid JSON body and the stop reason and token usage of that
call are lost. Here every outcome keeps its usage.
"""

from typing import Any

import anthropic
from anthropic.lib.bedrock import AnthropicBedrockMantle
from pydantic import ValidationError

from app.llm.provider import (
    LlmUsage,
    OutputT,
    PdfEvidence,
    RetryableLlmError,
    SuggestionRequest,
    SuggestionResult,
    TextEvidence,
)


class BedrockMantleProvider:
    def __init__(
        self,
        model_id: str,
        aws_region: str,
        max_retries: int = 3,
        timeout_s: float = 90.0,
        client: Any | None = None,
    ):
        self._model_id = model_id
        self._client = client or AnthropicBedrockMantle(
            aws_region=aws_region, max_retries=max_retries, timeout=timeout_s
        )

    def suggest(self, request: SuggestionRequest[OutputT]) -> SuggestionResult[OutputT]:
        content: list[dict[str, Any]] = []
        for part in request.evidence:
            if isinstance(part, TextEvidence):
                content.append(
                    {
                        "type": "text",
                        "text": f'<evidence index="{part.source_index}" source="{_attr(part.label)}">\n'
                        f"{part.text}\n</evidence>",
                    }
                )
            elif isinstance(part, PdfEvidence):
                content.append(
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": part.data_base64},
                        "title": f"evidence {part.source_index}: {part.label}",
                    }
                )
        content.append({"type": "text", "text": request.task})

        schema = anthropic.transform_schema(request.output_model.model_json_schema())
        try:
            message = self._client.messages.create(
                model=self._model_id,
                max_tokens=request.max_tokens,
                system=[{"type": "text", "text": request.system_prefix, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": content}],
                output_config={"effort": request.effort, "format": {"type": "json_schema", "schema": schema}},
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


def _attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
