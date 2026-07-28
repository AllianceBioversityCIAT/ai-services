import os
from dotenv import load_dotenv

load_dotenv()


def is_lambda_runtime() -> bool:
    """True when running inside AWS Lambda (use IAM execution role for boto3)."""
    return bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("AWS_EXECUTION_ENV"))


def _resolve_static_aws_credentials() -> tuple[str | None, str | None]:
    """Static keys are for local development only — never used in Lambda."""
    if is_lambda_runtime():
        return None, None
    access_key = os.getenv("INSIGHTS_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("INSIGHTS_AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    return access_key, secret_key


_access_key, _secret_key = _resolve_static_aws_credentials()

AWS = {
    "aws_access_key": _access_key,
    "aws_secret_key": _secret_key,
    "aws_region": os.getenv("AWS_REGION", "us-east-1"),
}

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"

CLARISA_VALIDATE_URL = os.getenv("CLARISA_VALIDATE_URL")

INTERACTION_SERVICE_URL = os.getenv("INTERACTION_SERVICE_URL")

STAR_API_BASE_URL = os.getenv("STAR_API_BASE_URL")

STAR_API_TOKEN = os.getenv("STAR_API_TOKEN")


def get_boto3_client_kwargs() -> dict:
    """Extra kwargs for boto3.client(). Empty in Lambda → IAM execution role."""
    kwargs = {"region_name": AWS["aws_region"]}
    if is_lambda_runtime():
        return kwargs
    if AWS.get("aws_access_key") and AWS.get("aws_secret_key"):
        kwargs["aws_access_key_id"] = AWS["aws_access_key"]
        kwargs["aws_secret_access_key"] = AWS["aws_secret_key"]
    return kwargs


def clear_static_aws_credentials_from_environ() -> None:
    """Remove app-specific static keys only — do not touch AWS_* vars Lambda injects for the IAM role."""
    if not is_lambda_runtime():
        return
    for key in (
        "INSIGHTS_AWS_ACCESS_KEY_ID",
        "INSIGHTS_AWS_SECRET_ACCESS_KEY",
    ):
        os.environ.pop(key, None)


clear_static_aws_credentials_from_environ()
