"""
Bedrock invocation with a forced tool call, for the quality assessment flow.

Separate from app/llm/mining.py on purpose:
  - its own semaphore, so the assessment endpoint's parallel calls are not
    throttled by (or throttling) the existing /api/prms-qa flow;
  - forced tool use instead of "reply with raw JSON", so the response shape is
    guaranteed by the API rather than by prompt instructions.

A cache breakpoint sits on the system block, which holds the role and criteria and
is identical for every result of the same type. Bedrock supports explicit
cache_control but not top-level automatic caching, so the breakpoint is placed by
hand and the volatile result data is kept in the user message, after it.
"""

import json
import asyncio
from typing import Optional

import boto3

from app.utils.logger.logger_util import get_logger

logger = get_logger()

MODEL_ID = "us.anthropic.claude-sonnet-4-6"
ASSESSMENT_SEMAPHORE = asyncio.Semaphore(4)

_bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")


class ToolCallFailed(Exception):
    pass


async def invoke_with_tool(
    system: str,
    user: str,
    tool: dict,
    max_tokens: int = 4000,
    call_name: str = "assessment",
    timeout: Optional[float] = None,
    max_retries: int = 3,
) -> dict:
    """Invoke the model and return the forced tool call's input as a dict."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
        "messages": [{"role": "user", "content": [{"type": "text", "text": user}]}],
    }

    async with ASSESSMENT_SEMAPHORE:
        delay = 0.5
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                coro = loop.run_in_executor(
                    None,
                    lambda: _bedrock.invoke_model(
                        modelId=MODEL_ID,
                        body=json.dumps(body),
                        contentType="application/json",
                        accept="application/json",
                    ),
                )
                response = await (
                    asyncio.wait_for(coro, timeout) if timeout else coro
                )
                payload = json.loads(response["body"].read())

                usage = payload.get("usage", {})
                logger.info(
                    f"✅ {call_name}: in={usage.get('input_tokens')} "
                    f"out={usage.get('output_tokens')} "
                    f"cache_read={usage.get('cache_read_input_tokens', 0)} "
                    f"cache_write={usage.get('cache_creation_input_tokens', 0)}"
                )

                for block in payload.get("content", []):
                    if block.get("type") == "tool_use" and block.get("name") == tool["name"]:
                        return block["input"]

                raise ToolCallFailed(
                    f"{call_name}: model did not call {tool['name']} "
                    f"(stop_reason={payload.get('stop_reason')})"
                )

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ {call_name} exceeded its {timeout}s budget")
                raise

            except Exception as e:
                throttled = "ThrottlingException" in str(e) or "Too many tokens" in str(e)
                if throttled and attempt < max_retries - 1:
                    logger.warning(
                        f"⏱️ {call_name} throttled, retrying in {delay}s "
                        f"({attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                logger.error(f"❌ {call_name} failed: {e}")
                raise
