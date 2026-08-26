"""Shared AWS Bedrock runtime client for all mining products."""

from __future__ import annotations

import json
import time
import boto3
from botocore.config import Config
from app.utils.config.config_util import AWS
from app.utils.logger.logger_util import get_logger
from app.text_mining.shared.models import ModelInvocationError, ModelInvocationResult, ModelUsage


logger = get_logger()

DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

_bedrock_config = Config(
    connect_timeout=60,
    read_timeout=300,
    retries={"max_attempts": 3, "mode": "adaptive"},
)

_bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    aws_access_key_id=AWS["aws_access_key"],
    aws_secret_access_key=AWS["aws_secret_key"],
    region_name=AWS.get("aws_region", "us-east-1"),
    config=_bedrock_config,
)


def invoke_model(
    prompt: str,
    max_tokens: int = 15000,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    temperature: float = 0.1,
) -> ModelInvocationResult:
    """
    Invoke Claude (or another Anthropic Messages model on Bedrock).

    Returns text plus usage metadata. Product pipelines are responsible for
    parsing/validating the response schema after this call.
    """
    start = time.time()
    try:
        logger.info("🚀 Invoking Bedrock model %s...", model_id)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        }

        response = _bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
        response_body = json.loads(response["body"].read())
        stop_reason = response_body.get("stop_reason", "unknown")
        usage_raw = response_body.get("usage", {})
        usage = ModelUsage(
            input_tokens=usage_raw.get("input_tokens", 0),
            output_tokens=usage_raw.get("output_tokens", 0),
        )
        text = response_body["content"][0]["text"]
        duration = time.time() - start

        logger.info(
            "✅ Model invoked - stop=%s input=%s output=%s duration=%.2fs",
            stop_reason,
            usage.input_tokens,
            usage.output_tokens,
            duration,
        )
        logger.info("📄 Model response (first 500 chars): %s...", text[:500])

        if stop_reason != "end_turn":
            logger.warning(
                "⚠️ Model stopped with reason: %s (may indicate truncation or max_tokens reached)",
                stop_reason,
            )

        return ModelInvocationResult(
            text=text,
            usage=usage,
            stop_reason=stop_reason,
            model_id=model_id,
            duration_seconds=duration,
        )
    except ModelInvocationError:
        raise
    except Exception as exc:
        logger.error("❌ Error invoking the model: %s", str(exc))
        raise ModelInvocationError(str(exc)) from exc
