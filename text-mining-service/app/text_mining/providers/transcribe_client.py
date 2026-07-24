"""Shared Amazon Transcribe client provider."""

from __future__ import annotations

import boto3
from app.utils.config.config_util import AWS


def get_transcribe_client():
    """Create a Transcribe client using shared AWS config."""
    return boto3.client(
        "transcribe",
        aws_access_key_id=AWS["aws_access_key"],
        aws_secret_access_key=AWS["aws_secret_key"],
        region_name=AWS.get("aws_region", "us-east-1"),
    )