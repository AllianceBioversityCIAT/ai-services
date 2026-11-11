"""S0 smoke test: one Claude Haiku 5.5 call through Bedrock (Mantle) with the Lambda execution role.

Returns only model, stop_reason, usage and the reply text. Never logs credentials or headers.
Invoke: ``aws lambda invoke --function-name qa-ai-smoke-test out.json``. Remove after S2.
"""

import os
from typing import Any

import anthropic
from anthropic.lib.bedrock import AnthropicBedrockMantle

MODEL_ID = os.getenv("MODEL_ID", "anthropic.claude-haiku-5-5")


def handler(event: Any = None, context: Any = None, client: Any | None = None) -> dict[str, Any]:
    try:
        client = client or AnthropicBedrockMantle(aws_region=os.getenv("AWS_REGION", "us-east-1"))
        msg = client.messages.create(
            model=MODEL_ID,
            max_tokens=256,  # adaptive thinking counts toward max_tokens
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return {
            "ok": True,
            "model": msg.model,
            "stop_reason": msg.stop_reason,
            "usage": {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens},
            "text": text,
        }
    except anthropic.APIStatusError as err:
        return {"ok": False, "status": err.status_code, "type": type(err).__name__, "message": str(err)[:300]}
    except Exception as err:  # noqa: BLE001 - report any failure without a stack trace
        return {"ok": False, "type": type(err).__name__, "message": str(err)[:300]}
