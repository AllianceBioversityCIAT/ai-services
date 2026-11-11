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

LLM = {
    "model_id": os.getenv("MODEL_ID", "anthropic.claude-haiku-5-5"),
    "effort": os.getenv("LLM_EFFORT", "medium"),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4000")),
}

ENV_NAME = os.getenv("ENV_NAME", "local")
