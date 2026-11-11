"""Logger with the same interface as qa-service (``get_logger()``).

Differences from qa-service, on purpose:
  - console only: in Lambda, stdout goes to CloudWatch; a /tmp file would be lost with the sandbox;
  - INFO by default (``LOG_LEVEL`` overrides): log ids, hashes, token counts and reasons only,
    never evidence text, prompts or model output.
"""

import logging
import os
import sys

logger = logging.getLogger("ai-qa-helper")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    )
    logger.addHandler(_handler)
logger.propagate = False


def get_logger() -> logging.Logger:
    return logger
