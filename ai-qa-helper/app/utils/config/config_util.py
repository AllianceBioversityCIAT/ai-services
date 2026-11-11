"""Runtime configuration, read once from the environment (same pattern as qa-service).

Only names are documented here; values come from the Lambda environment (Terraform) or a local
``.env`` that is never committed.
"""

import os

from dotenv import load_dotenv

load_dotenv()

AWS = {
    "aws_region": os.getenv("AWS_REGION", "us-east-1"),
}

_BEDROCK_API = os.getenv("BEDROCK_API", "runtime")
"""``runtime`` (Bedrock Runtime InvokeModel) or ``mantle`` (Claude in Amazon Bedrock). See app/llm/bedrock.py."""

LLM = {
    "bedrock_api": _BEDROCK_API,
    "model_id": os.getenv(
        "MODEL_ID", "us.anthropic.claude-haiku-5-5" if _BEDROCK_API == "runtime" else "anthropic.claude-haiku-5-5"
    ),
    "effort": os.getenv("LLM_EFFORT", "medium"),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4000")),
}

ENV_NAME = os.getenv("ENV_NAME", "local")
